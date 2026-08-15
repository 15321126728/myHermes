# ruff: noqa: E501 -- Research prompts are kept as readable, exact text.

"""
IntervenedTerminusAgent — 实验干预专用的 Agent 子类。

继承自 ReplayableHermesAgent，在保留其「轨迹回放→干预→自由采样」骨架的基础上，
增加了更丰富的干预机制。

新增功能：
  1. intervention_schedule（干预时刻表）：在多个指定 episode 执行不同的注入/覆盖操作
  2. intervention_triggers（条件触发器）：当终端输出匹配特定错误模式时自动触发干预
  3. inject_before_episode（前置注入）：在 LLM 调用之前注入消息，而非之后
  4. 干预日志记录：每次干预触发时记录到 _trajectory_records
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

from terminal_bench.agents.base_agent import AgentResult
from terminal_bench.agents.failure_mode import FailureMode
from terminal_bench.llms.chat import Chat
from terminal_bench.terminal.tmux_session import TmuxSession

from hermes_agent.replay_support import (
    apply_message_intervention,
    default_artifact_path,
)
from hermes_agent.replayable_hermes import ReplayableHermesAgent
from hermes_agent.terminus import Command


class IntervenedTerminusAgent(ReplayableHermesAgent):
    """具有增强干预能力的 Agent 子类。

    在 ReplayableHermesAgent 的基础上，支持：

    - **干预时刻表 (intervention_schedule)**:
      ``[{"episode": 3, "mode": "inject", "payload": "..."}, ...]``
      在指定的 episode 执行干预，支持 inject / overwrite 模式。

    - **条件触发器 (intervention_triggers)**:
      ``[{"pattern": "ModuleNotFoundError", "mode": "inject", "payload": "..."}, ...]``
      当 terminal_output 匹配正则模式时自动触发干预（仅生效一次）。

    - **前置注入 (inject_before_episode)**:
      若 ``inject_before_episode >= 0``，在对应 episode 的 LLM query 之前
      注入干预消息，而非 query 之后。
    """

    def __init__(
        self,
        model_name: str,
        max_episodes: int | None = None,
        parser_name: str = "json",
        api_base: str | None = None,
        temperature: float = 0.7,
        replay_path: str | None = None,
        replay_until_episode: int = 0,
        intervention_mode: str = "none",
        intervention_payload: str | None = None,
        trajectory_output_path: str | None = None,
        # --- 新增参数 ---
        intervention_schedule: Any = None,
        intervention_triggers: Any = None,
        inject_before_episode: int = -1,
        # --- Oracle 轨迹对比干预 ---
        oracle_trajectory_path: str | None = None,  # oracle_trajectory.json 路径
        enable_episode_snapshots: bool = False,  # 是否在每 episode 后捕获文件快照
        # --- Oracle 距离 + Dockerless 验证 ---
        enable_oracle_distance: bool = False,  # 注入稠密距离信号
        enable_dockerless: bool = False,  # 启用 Dockerless 静态验证
        **kwargs: Any,
    ):
        super().__init__(
            model_name=model_name,
            max_episodes=max_episodes,
            parser_name=parser_name,
            api_base=api_base,
            temperature=temperature,
            replay_path=replay_path,
            replay_until_episode=replay_until_episode,
            intervention_mode=intervention_mode,
            intervention_payload=intervention_payload,
            trajectory_output_path=trajectory_output_path,
            **kwargs,
        )
        # 解析 JSON 字符串参数 → Python 对象
        # CLI 的 _infer_type 会通过 ast.literal_eval 自动将 JSON 转为 Python 列表，
        # 因此需要兼容 str 与 list 两种输入
        self._intervention_schedule: list[dict[str, Any]] = (
            json.loads(intervention_schedule)
            if isinstance(intervention_schedule, str)
            else intervention_schedule
            if isinstance(intervention_schedule, list)
            else []
        )
        self._intervention_triggers: list[dict[str, Any]] = (
            json.loads(intervention_triggers)
            if isinstance(intervention_triggers, str)
            else intervention_triggers
            if isinstance(intervention_triggers, list)
            else []
        )
        self._inject_before_episode = inject_before_episode

        # 已触发过的条件干预索引集合（每个 trigger 只触发一次）
        self._triggered_indices: set[int] = set()

        # --- 运行时命令监控 ---
        self._command_history: list[str] = []  # 最近执行的命令列表
        self._command_repetition_count: int = 0  # 连续重复计数
        self._last_command: str | None = None  # 上一条命令
        self._repetition_intervention_triggered: bool = False  # 是否已触发过重复干预
        self._pending_force_commands: list[str] | None = None  # 等待执行的强制命令
        self._last_analysis_episode: int = -1  # 上一个执行分析命令的 episode
        self._analysis_command_count: int = 0  # 连续分析命令计数

        # --- 轨迹自动保存 ---
        self._trajectory_output_path: Path | None = (
            Path(trajectory_output_path) if trajectory_output_path else None
        )

        # --- Oracle 轨迹对比干预 ---
        self._oracle_trajectory_path: str | None = oracle_trajectory_path
        self._enable_episode_snapshots: bool = enable_episode_snapshots
        self._episode_snapshots: list[dict[str, Any]] = []  # 每 episode 的文件快照

        # --- Oracle 距离 + Dockerless 验证 ---
        self._enable_oracle_distance: bool = enable_oracle_distance
        self._enable_dockerless: bool = enable_dockerless
        self._previous_distance_score: float | None = None
        self._oracle_state = None  # 延迟初始化
        self._distance_history: list[float] = []  # 距离历史（用于停滞检测）
        self._distance_stagnation_episodes: int = 0  # 连续无进步次数

        # 如果启用了 oracle_distance，预先加载 oracle 规格
        if enable_oracle_distance:
            from hermes_agent.oracle_distance import OracleState

            self._oracle_state = OracleState()

        self._logger.info(
            f"IntervenedTerminusAgent initialized: "
            f"schedule={len(self._intervention_schedule)} items, "
            f"triggers={len(self._intervention_triggers)} patterns, "
            f"inject_before_episode={inject_before_episode}, "
            f"snapshots={enable_episode_snapshots}, "
            f"oracle_distance={enable_oracle_distance}, "
            f"dockerless={enable_dockerless}"
        )

    # ──────────────────────────────────────────────
    # 三阶段定向干预策略（默认配置）
    # ──────────────────────────────────────────────

    # ──────────────────────────────────────────────
    # 激进四阶段干预策略（默认配置—v6 使用）
    # ──────────────────────────────────────────────

    AGGRESSIVE_STRATEGY = {
        "schedule": [
            {
                "episode": 2,
                "mode": "overwrite",
                "payload": (
                    "【系统指令】你正处于 Terminal-Bench 的 dna-assembly 任务环境中。\n"
                    "任务：设计 8 条 Golden Gate 组装引物（input/egfp/flag/snap 各一正一反）。\n"
                    "序列文件 sequences.fasta 已包含所有序列，请勿重复查看。\n"
                    "正确的工作流：\n"
                    "  1. 用 Python 解析 FASTA 获取 4 个片段的序列\n"
                    "  2. 确定各片段的 4bp 拼接点 overhang\n"
                    "  3. 计算每条引物的退火序列\n"
                    "  4. 格式：5'-GGTCTC-[4bp overhang]-[退火区]-3'\n"
                    "  5. 用 oligotm 检查 Tm（目标 58-72°C）\n"
                    "  6. 写入 /app/primers.fasta\n"
                    "立即开始，禁止执行 ls/cat 等文件查看命令。"
                ),
            },
            {
                "episode": 5,
                "mode": "overwrite",
                "payload": (
                    "【中间检查】当前 episode 5。\n"
                    "请确认已执行以下步骤：\n"
                    "  1. ✅ 用 Python 解析了 FASTA 序列\n"
                    "  2. ✅ 识别了 4bp overhang\n"
                    "  3. ✅ 设计了引物序列\n"
                    "如果尚未完成，请立即执行。使用 Python subprocess 或直接编写 primer 脚本。\n"
                    "最终文件必须是 /app/primers.fasta。"
                ),
            },
            {
                "episode": 8,
                "mode": "overwrite",
                "payload": (
                    "【进度警告】Episode 8：时间已过半。\n"
                    "如果你还没有输出 /app/primers.fasta，请立即执行以下操作：\n"
                    "```python\n"
                    'primers = {"input_fwd": "...", ...}\n'
                    "with open('/app/primers.fasta', 'w') as f:\n"
                    "    for name, seq in primers.items():\n"
                    "        f.write(f'>{name}\\n{seq}\\n')\n"
                    "```\n"
                    "不要继续 cat 或 ls。立刻输出文件。"
                ),
            },
            {
                "episode": 12,
                "mode": "overwrite",
                "payload": (
                    "【严重警告】Episode 12：任务即将超时！\n"
                    "立即输出 /app/primers.fasta！格式要求：\n"
                    "  >input_fwd\n"
                    "  GGTCTC[4bp overhang][15-45bp annealing sequence]\n"
                    "  >input_rev\n"
                    "  ...\n"
                    "共需 8 条引物（4 个片段×正反向）。立刻写入文件！"
                ),
            },
        ],
        "triggers": [
            {
                "pattern": r"ModuleNotFoundError|ImportError.*requests",
                "mode": "inject",
                "payload": (
                    "系统提示：当前环境中未安装 requests 库。"
                    "请使用 Python 标准库 urllib.request 进行 HTTP 请求。"
                ),
            },
            {
                "pattern": r"cat sequences\.fasta|cat -n sequences|head.*sequences|tail.*sequences",
                "mode": "inject",
                "payload": (
                    "【系统警告】禁止重复查看 sequences.fasta。"
                    "你已经在之前的回合中读取过该文件。请基于已有的信息直接设计引物。"
                ),
            },
            {
                "pattern": r"ls -la|ls /app",
                "mode": "inject",
                "payload": ("【系统警告】不需要继续查看目录结构。请直接进行引物设计。"),
            },
        ],
    }

    @classmethod
    def with_aggressive_strategy(
        cls,
        model_name: str,
        max_episodes: int | None = None,
        **kwargs: Any,
    ) -> IntervenedTerminusAgent:
        """使用激进四阶段干预策略创建 Agent 实例。

        相比 THREE_STEP_STRATEGY 的改进：
        - 使用 overwrite 模式替代 inject（直接替换对话历史，效果更强）
        - 从 Ep2 开始干预（更早介入）
        - 干预频率更高（Ep2/5/8/12）
        - 触发器更针对 dna-assembly 的具体命令模式
        """
        strategy = cls.AGGRESSIVE_STRATEGY
        schedule = kwargs.pop("intervention_schedule", strategy["schedule"])
        triggers = kwargs.pop("intervention_triggers", strategy["triggers"])
        return cls(
            model_name=model_name,
            max_episodes=max_episodes,
            intervention_schedule=schedule,
            intervention_triggers=triggers,
            **kwargs,
        )

    THREE_STEP_STRATEGY = {
        "schedule": [
            {
                "episode": 6,
                "mode": "inject",
                "payload": (
                    "系统警告：禁止重复执行 ls 或 cat sequences.fasta。"
                    "你已经在之前的回合中完整解析过所有序列。"
                    "input, egfp, flag, snap 的序列数据已在你的上下文内存中。"
                    "请直接根据这些序列设计引物。"
                    "如果你继续执行文件查看命令，将被视为任务执行失败。"
                ),
            },
            {
                "episode": 12,
                "mode": "inject",
                "payload": (
                    "当前任务进度：已读取序列。目标：生成 primers.fasta。\n"
                    "请执行以下 Python 步骤：\n"
                    "1. 用 Python 解析 FASTA。\n"
                    "2. 定位拼接点 overhangs (4bp)。\n"
                    "3. 计算引物序列。\n"
                    "4. 使用 oligotm 或内置 Tm 公式检查 Tm。\n"
                    "5. 写入 primers.fasta。\n"
                    "请停止 cat 操作，立刻开始设计引物。"
                ),
            },
            {
                "episode": 18,
                "mode": "inject",
                "payload": (
                    "严重警告：你已接近任务时限。请立即输出最终的 primers.fasta 文件。\n"
                    "不再需要更多分析。请按照以下简化步骤操作：\n"
                    "1. 识别 4 个片段的 4bp 拼接点。\n"
                    "2. 为每个片段生成 1 条正向和 1 条反向引物。\n"
                    "3. 引物格式：5'-[4bp overhang]-GGTCTC-[15-45bp annealing]-3'\n"
                    "4. 写入 /app/primers.fasta。\n"
                    "立刻执行，无需更多确认。"
                ),
            },
        ],
        "triggers": [
            {
                "pattern": r"ModuleNotFoundError|ImportError.*requests",
                "mode": "inject",
                "payload": (
                    "系统提示：当前环境中未安装 requests 库，且禁止安装新包。"
                    "请使用 Python 标准库 urllib.request 进行 HTTP 请求。"
                    "修改你的代码逻辑，禁止使用 import requests。"
                ),
            },
            {
                "pattern": r"ImportError.*no module named",
                "mode": "inject",
                "payload": (
                    "系统提示：无法安装第三方包。请仅使用 Python 3 标准库中的模块。"
                    "检查你的 import 语句并删除所有第三方依赖。"
                ),
            },
            {
                "pattern": r"apt-get|pip install|conda install",
                "mode": "inject",
                "payload": (
                    "系统警告：禁止安装新包。当前环境已提供所有必要的工具。"
                    "请使用环境中已有的工具完成任务。"
                ),
            },
        ],
    }

    @classmethod
    def with_three_step_strategy(
        cls,
        model_name: str,
        max_episodes: int | None = None,
        **kwargs: Any,
    ) -> IntervenedTerminusAgent:
        """使用三阶段定向干预策略创建 Agent 实例。

        此工厂方法自动注入默认的 3 步干预配置，适合 dna-assembly 类任务。
        用户可通过 ``schedule_overrides`` 和 ``triggers_overrides`` 覆盖默认设置。
        """
        strategy = cls.THREE_STEP_STRATEGY
        schedule = kwargs.pop("intervention_schedule", strategy["schedule"])
        triggers = kwargs.pop("intervention_triggers", strategy["triggers"])
        return cls(
            model_name=model_name,
            max_episodes=max_episodes,
            intervention_schedule=schedule,
            intervention_triggers=triggers,
            **kwargs,
        )

    # ──────────────────────────────────────────────
    # 静态标识
    # ──────────────────────────────────────────────

    @staticmethod
    def name() -> str:
        return "intervened-terminus"

    # ──────────────────────────────────────────────
    # 干预辅助方法
    # ──────────────────────────────────────────────

    # ──────────────────────────────────────────────
    # 运行时命令重复监控
    # ──────────────────────────────────────────────

    def _is_analysis_command(self, cmd_text: str) -> bool:
        """判断命令是否属于分析类命令（非实质性操作）。

        扩展检测：不仅检测 ls/cat 等简单命令，也检测：
        - 只读的 Python 脚本（读取文件但不写入目标文件）
        - 重复的工具检查
        - 无输出的探索性命令
        """
        cmd = cmd_text.strip().lower()
        analysis_patterns = [
            r"^ls[ \n]",
            r"^cat[ \n]",
            r"^which[ \n]",
            r"^head[ \n]",
            r"^tail[ \n]",
            r"^find[ \n]",
            r"^echo.*(which|ls|cat)",
            r"^pwd[ \n]",
            r"^env$",
            r"^print",
            r"^clear",
        ]
        for pat in analysis_patterns:
            if re.search(pat, cmd_text):
                return True

        # Python 脚本分析检测：读取文件但不写入目标文件
        if cmd.startswith("python3") or cmd.startswith("python "):
            has_read = any(
                kw in cmd
                for kw in [
                    "open(",
                    ".read()",
                    ".read_text",
                    "open(",
                    "sequences.fasta",
                    "for line in",
                ]
            )
            # 如果读取目标文件但没写引物文件 → 分析命令
            if has_read and "primers.fasta" not in cmd:
                return True

        return False

    def _check_analysis_loop(
        self,
        commands: list[Command],
        episode: int,
        session: TmuxSession,
        chat: Chat | None = None,
    ) -> bool:
        """检测分析循环：连续过多的分析类命令，强制截断历史并注入执行指令。
        Returns True if forced action was taken.
        """
        cmd_texts = [c.keystrokes.strip() for c in commands if c.keystrokes.strip()]
        if not cmd_texts:
            return False

        # 统计本轮中的分析类命令
        analysis_count = sum(1 for t in cmd_texts if self._is_analysis_command(t))
        all_analysis = analysis_count == len(cmd_texts) and analysis_count > 0

        if episode == self._last_analysis_episode + 1:
            if all_analysis:
                self._analysis_command_count += 1
            else:
                # 有实质性命令，重置计数器
                self._analysis_command_count = 0
        else:
            if all_analysis:
                self._analysis_command_count = 1
            else:
                self._analysis_command_count = 0

        self._last_analysis_episode = episode

        # 连续 3+ 个 episode 全为分析命令 → 强制截断 + 注入紧急指令
        if self._analysis_command_count >= 3:
            self._logger.info(
                f"[分析循环检测] Episode {episode}: "
                f"连续 {self._analysis_command_count} 个 episode 仅执行分析命令 → "
                f"强制截断历史并注入紧急指令"
            )
            if chat is None:
                self._logger.warning("chat is None, cannot truncate history")
                self._analysis_command_count = 0
                return False
            # 截断历史：只保留第一条系统消息 + 紧急指令
            current_screen = session.capture_pane(capture_entire=False)
            force_prompt = (
                "【强制指令】你已连续多个回合仅执行分析命令而未取得实质进展。\n"
                "立即终止所有分析。直接执行任务所需的关键命令。\n"
                "如果你不知道该做什么，请直接运行: python3 << 'EOF'\n"
                "# 在这里写你需要的 Python 代码\n"
                "EOF\n"
                f"当前终端状态: {current_screen[:2000]}"
            )
            chat._messages = [
                chat._messages[0],
                {"role": "user", "content": force_prompt},
            ]
            self._analysis_command_count = 0
            self._trajectory_records.append(
                {
                    "episode": episode,
                    "intervention_type": "analysis_loop_break",
                    "intervention_mode": "history_truncate",
                    "analysis_count": self._analysis_command_count,
                }
            )
            return True
        return False

    def _check_command_repetition(
        self, commands: list[Command], episode: int, chat: Chat
    ) -> None:
        """检测命令重复模式，触发实时干预。"""
        if self._repetition_intervention_triggered:
            return  # 已触发过，不再重复

        # 提取命令文本
        cmd_texts = []
        for cmd in commands:
            text = cmd.keystrokes.strip()
            # 只检查非空命令
            if text:
                cmd_texts.append(text)

        if not cmd_texts:
            return

        # 检查是否与上一条命令重复
        current_cmd = "; ".join(cmd_texts)
        if current_cmd == self._last_command:
            self._command_repetition_count += 1
        else:
            self._command_repetition_count = 0
            self._last_command = current_cmd

        # 如果连续 3 次执行相同命令 → 触发干预
        if self._command_repetition_count >= 2:  # 连续 3 次相同
            self._logger.info(
                f"[命令重复检测] Episode {episode}: 检测到连续重复命令 "
                f"'{current_cmd[:80]}...' → 触发实时干预"
            )
            payload = (
                f"【实时干预】检测到连续重复执行相同命令（{current_cmd[:80]}），"
                f"此行为已在第 {episode - self._command_repetition_count} 至 "
                f"{episode} episode 中重复 {self._command_repetition_count + 1} 次。"
                f"请立即停止重复操作，换用不同的方法推进任务。"
            )
            apply_message_intervention(chat._messages, "overwrite", payload)
            self._repetition_intervention_triggered = True
            self._trajectory_records.append(
                {
                    "episode": episode,
                    "intervention_type": "repetition_detection",
                    "intervention_mode": "overwrite",
                    "intervention_payload": payload,
                    "repeated_command": current_cmd[:100],
                    "repetition_count": self._command_repetition_count + 1,
                }
            )

    # ──────────────────────────────────────────────
    # Oracle 距离 + Dockerless 验证
    # ──────────────────────────────────────────────

    def _compute_oracle_distance(
        self, terminal_output: str, episode: int = 0
    ) -> str | None:
        """计算当前状态与 oracle 的距离，返回可注入 prompt 的文本。"""
        if not self._enable_oracle_distance or self._oracle_state is None:
            return None

        # 从 terminal_output 中提取 primers.fasta 内容（如果有）
        primer_content = self._extract_primer_content(terminal_output)

        from hermes_agent.oracle_distance import (
            compute_distance,
            format_distance_for_prompt,
        )

        result = compute_distance(
            terminal_output=terminal_output,
            oracle=self._oracle_state,
            primer_content=primer_content,
        )

        # 跟踪距离历史，检测停滞
        current_score = result["score"]
        if self._previous_distance_score is not None:
            improvement = self._previous_distance_score - current_score
            if improvement < 0.02:  # 进步小于 2%
                self._distance_stagnation_episodes += 1
            else:
                self._distance_stagnation_episodes = 0
        self._distance_history.append(current_score)

        formatted = format_distance_for_prompt(
            result, previous_score=self._previous_distance_score
        )

        # 如果连续 5+ 轮无进步，添加强制推进指令
        if self._distance_stagnation_episodes >= 5:
            # 基于各分量生成针对性指导
            components = result.get("components", {})
            stagnation_guide = "\n\n⚠️ 【距离停滞警告】你的距离分数连续多轮未改善。"

            # 找出最差的 2 个分量
            sorted_components = sorted(
                components.items(), key=lambda x: x[1], reverse=True
            )
            worst = [k for k, v in sorted_components if v >= 0.6][:2]

            for comp in worst:
                if comp == "tools_installed":
                    stagnation_guide += "\n📦 工具未安装: apt-get update && apt-get install -y emboss primer3"
                elif comp == "sequences_read":
                    stagnation_guide += "\n📄 序列未读取: cat /app/sequences.fasta"
                elif comp == "needle_run":
                    stagnation_guide += (
                        "\n🔬 Needle 比对未执行: "
                        "needle sequences.fasta:egfp sequences.fasta:output "
                        "-gapopen 10 -gapextend 0.5 -aformat pair -outfile stdout | head -50"
                    )
                elif comp == "attempted_write":
                    stagnation_guide += "\n✏️  未写入 primers.fasta: 使用 python3 计算后写入 /app/primers.fasta"
                elif comp == "missing_primers":
                    stagnation_guide += "\n🧬 引物缺失: 需要 output_fwd, output_rev, egfp_fwd, egfp_rev, flag_fwd, flag_rev, snap_fwd, snap_rev"
                elif comp == "bsai_missing":
                    stagnation_guide += "\n✂️  缺少 BsaI 位点: 每条引物需包含 GGTCTC"
                elif comp == "clamp_missing":
                    stagnation_guide += (
                        "\n🛡️  缺少 clamp 碱基: GGTCTC 前需 ≥1bp 保护碱基 (如 ggctac)"
                    )
                elif comp == "overhang_errors":
                    stagnation_guide += (
                        "\n🔗 Overhang 不匹配: 检查 4bp overhang 是否与相邻片段互补"
                    )
                elif comp == "tm_deviation":
                    stagnation_guide += (
                        "\n🌡️  Tm 偏离: 使用 oligotm 验证退火温度 (目标 58-72°C)"
                    )

            stagnation_guide += (
                "\n\n立即执行上述命令，然后运行: bash /tests/run-tests.sh"
            )
            formatted += stagnation_guide
            self._distance_stagnation_episodes = 0  # 重置

        self._previous_distance_score = current_score
        return formatted

    def _run_dockerless_validation(self, terminal_output: str) -> str | None:
        """运行 Dockerless 静态验证，返回反馈文本。"""
        if not self._enable_dockerless:
            return None

        primer_content = self._extract_primer_content(terminal_output)
        if not primer_content:
            return None

        from hermes_agent.dockerless_validator import validate_primers

        vr = validate_primers(primer_content)
        return vr.to_prompt()

    def _extract_primer_content(self, terminal_output: str) -> str | None:
        """从 terminal_output 中提取 primers.fasta 的内容。"""
        # 尝试从 cat 输出中提取
        fasta_pattern = re.compile(r"(>[a-zA-Z_0-9]+\s*[atcgATCG\n]+)", re.MULTILINE)
        matches = fasta_pattern.findall(terminal_output)
        if matches:
            combined = "\n".join(m.strip() for m in matches)
            if ">" in combined and any(c in combined.lower() for c in "atcg"):
                return combined

        # 如果 snapshots 中有记录，也检查
        if self._episode_snapshots:
            latest = self._episode_snapshots[-1]
            for k, v in latest.items():
                if k.endswith("primers.fasta:content"):
                    return v

        return None

    # ──────────────────────────────────────────────
    # Episode 文件快照（用于与 oracle 轨迹对比 + Fork 重放）
    # ──────────────────────────────────────────────

    def _capture_episode_snapshot(
        self,
        episode: int,
        commands: list[Command],
        terminal_output: str,
        session: TmuxSession,
    ) -> dict[str, Any]:
        """捕获当前 episode 执行后的文件系统快照。"""
        snapshot: dict[str, Any] = {
            "episode": episode,
            "timestamp": time.time(),
        }

        # 捕获关键文件的内容
        key_paths = [
            "/app/primers.fasta",
            "/app/sequences.fasta",
            "/app/answer.txt",
        ]
        for path in key_paths:
            try:
                result = session.container.exec_run(
                    ["bash", "-c", f"cat {path} 2>/dev/null || true"]
                )
                content = result.output.decode(errors="replace")
                if content.strip():
                    snapshot[f"file:{path}:content"] = content[:5000]  # 限制大小
                    # 也记 md5
                    md5_result = session.container.exec_run(
                        [
                            "bash",
                            "-c",
                            f"md5sum {path} 2>/dev/null | cut -d' ' -f1 || true",
                        ]
                    )
                    md5 = md5_result.output.decode(errors="replace").strip()
                    if md5:
                        snapshot[f"file:{path}:md5"] = md5
            except Exception:
                pass

        # 捕获命令执行的摘要（用于快速定位）
        cmd_texts = [
            c.keystrokes.strip() for c in (commands or []) if c.keystrokes.strip()
        ]
        snapshot["commands_executed"] = cmd_texts[:20]  # 最多 20 条
        snapshot["terminal_output_preview"] = terminal_output[:1000]

        self._episode_snapshots.append(snapshot)
        return snapshot

    def _save_checkpoint_tarball(
        self,
        episode: int,
        session: TmuxSession,
    ) -> str | None:
        """保存当前 /app/ 目录的 checkpoint tarball 到宿主机。

        用于 Fork 重放：在后续运行时恢复这个 checkpoint，从而
        保留之前的文件状态，无需从头开始。

        Returns:
            str | None: tarball 路径，失败返回 None
        """
        if not self._trajectory_output_path:
            return None

        checkpoint_dir = self._trajectory_output_path.parent / "checkpoints"
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        tarball_path = checkpoint_dir / f"episode-{episode}.tar.gz"

        try:
            # 在容器内创建 tarball
            result = session.container.exec_run(
                [
                    "bash",
                    "-c",
                    f"tar czf /tmp/checkpoint-ep-{episode}.tar.gz "
                    f"-C / app/ 2>/dev/null; "
                    f"base64 /tmp/checkpoint-ep-{episode}.tar.gz",
                ],
                user=self._user if hasattr(self, "_user") else "",
            )
            output = result.output.decode(errors="replace").strip()
            if output:
                import base64

                tarball_path.write_bytes(base64.b64decode(output))
                self._logger.info(
                    f"Checkpoint saved: {tarball_path} "
                    f"({tarball_path.stat().st_size} bytes)"
                )
                return str(tarball_path)
        except Exception as e:
            self._logger.warning(f"Failed to save checkpoint tarball: {e}")

        return None

    def _save_episode_snapshots(self) -> None:
        """将 episode 快照保存到文件。"""
        if not self._episode_snapshots:
            return
        # 保存在 trajectory 的同级目录
        if self._trajectory_output_path:
            snapshots_path = self._trajectory_output_path.with_suffix(".snapshots.json")
        else:
            snapshots_path = default_artifact_path(
                "intervened-terminus-trajectory.snapshots.json"
            )
        try:
            snapshots_path.parent.mkdir(parents=True, exist_ok=True)
            snapshots_path.write_text(
                json.dumps(self._episode_snapshots, indent=2, ensure_ascii=False)
            )
            self._logger.info(f"Episode snapshots saved to {snapshots_path}")
        except Exception as e:
            self._logger.warning(f"Failed to save episode snapshots: {e}")

    # ──────────────────────────────────────────────
    # 轨迹自动保存
    # ──────────────────────────────────────────────

    def _save_trajectory_snapshot(self) -> None:
        """定时保存 trajectory 快照，防止进程挂起丢失数据。"""
        if not self._trajectory_output_path:
            return
        try:
            path = Path(self._trajectory_output_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            snapshot = {
                "trajectory": self._trajectory_records,
                "saved_at": time.time(),
            }
            path.write_text(json.dumps(snapshot, indent=2, ensure_ascii=False))
        except Exception as e:
            self._logger.warning(f"Failed to save trajectory snapshot: {e}")

    def _apply_schedule_interventions(self, episode: int, chat: Chat) -> None:
        """根据 intervention_schedule 检查当前 episode 是否需要干预。"""
        for item in self._intervention_schedule:
            if item.get("episode") == episode:
                mode = item.get("mode", "inject")
                payload = item.get("payload", "")
                if payload:
                    self._logger.info(
                        f"[干预时刻表] Episode {episode}: 触发干预 (mode={mode})"
                    )
                    apply_message_intervention(chat._messages, mode, payload)
                    self._trajectory_records.append(
                        {
                            "episode": episode,
                            "intervention_type": "schedule",
                            "intervention_mode": mode,
                            "intervention_payload": payload,
                        }
                    )
                # 检查是否有强制命令需要执行
                force_commands = item.get("force_commands")
                if force_commands and isinstance(force_commands, list):
                    self._logger.info(
                        f"[强制命令] Episode {episode}: 设置 {len(force_commands)} 条强制命令"
                    )
                    self._pending_force_commands = force_commands

    def _check_trigger_interventions(
        self, episode: int, terminal_output: str, chat: Chat
    ) -> None:
        """检查 terminal_output 是否匹配 intervention_triggers 中的模式。"""
        for idx, item in enumerate(self._intervention_triggers):
            if idx in self._triggered_indices:
                continue  # 已触发过，跳过
            pattern = item.get("pattern", "")
            if not pattern:
                continue
            if re.search(pattern, terminal_output, re.IGNORECASE):
                mode = item.get("mode", "inject")
                payload = item.get("payload", "")
                self._logger.info(
                    f"[条件触发器] Episode {episode}: 匹配到模式 '{pattern}' → "
                    f"触发干预 (mode={mode})"
                )
                apply_message_intervention(chat._messages, mode, payload)
                self._triggered_indices.add(idx)
                self._trajectory_records.append(
                    {
                        "episode": episode,
                        "intervention_type": "trigger",
                        "intervention_mode": mode,
                        "intervention_payload": payload,
                        "matched_pattern": pattern,
                    }
                )

    # ──────────────────────────────────────────────
    # 重写主循环
    # ──────────────────────────────────────────────

    def _run_agent_loop(
        self,
        initial_prompt: str,
        session: TmuxSession,
        chat: Chat,
        logging_dir: Path | None = None,
        original_instruction: str = "",
    ) -> None:
        prompt = initial_prompt
        replay_cutoff = self._replay_until_episode

        try:
            for episode in range(self._max_episodes):
                if not session.is_session_alive():
                    self._logger.info("Session has ended, breaking out of agent loop")
                    break

                if original_instruction:
                    proactive_summary = self._check_proactive_summarization(
                        chat, original_instruction, session
                    )
                    if proactive_summary:
                        prompt = proactive_summary

                logging_paths = self._setup_episode_logging(logging_dir, episode)

                replay_mode = episode < min(replay_cutoff, len(self._replay_turns))

                if replay_mode:
                    # ── Phase 1: 回放模式 ──
                    commands, is_task_complete, feedback, response = (
                        self._handle_replay_interaction(
                            chat=chat,
                            prompt=prompt,
                            logging_paths=logging_paths,
                            episode=episode,
                            session=session,
                        )
                    )
                else:
                    # ── Phase 2: LLM 采样模式（含干预） ──

                    # 2a. 前置注入：在 LLM query 之前注入消息
                    if (
                        self._inject_before_episode >= 0
                        and episode == self._inject_before_episode
                        and self._intervention_mode != "none"
                        and self._intervention_payload
                    ):
                        self._logger.info(
                            f"[前置注入] Episode {episode}: 在 LLM query 之前注入干预"
                        )
                        apply_message_intervention(
                            chat._messages,
                            self._intervention_mode,
                            self._intervention_payload,
                        )

                    # 2b. 时刻表干预（在 LLM 调用前检查）
                    self._apply_schedule_interventions(episode, chat)

                    # 2c. 原始干预点（从父类保留的向后兼容）
                    if (
                        self._intervention_mode != "none"
                        and episode == replay_cutoff
                        and self._intervention_payload
                        and self._inject_before_episode < 0  # 前置注入已处理过则跳过
                    ):
                        apply_message_intervention(
                            chat._messages,
                            self._intervention_mode,
                            self._intervention_payload,
                        )

                    commands, is_task_complete, feedback, response = (
                        self._handle_llm_interaction(
                            chat,
                            prompt,
                            logging_paths,
                            original_instruction,
                            session,
                            episode=episode,
                            max_episodes=self._max_episodes,
                        )
                    )

                    # 2c. 强制命令：如果干预设置了 force_commands，替换 LLM 输出的命令
                    if self._pending_force_commands:
                        self._logger.info(
                            f"[强制命令] Episode {episode}: 执行 {len(self._pending_force_commands)} 条强制命令"
                        )
                        commands = [
                            Command(
                                keystrokes=cmd + "\n"
                                if not cmd.endswith("\n")
                                else cmd,
                                duration_sec=5.0,
                            )
                            for cmd in self._pending_force_commands
                        ]
                        self._pending_force_commands = None
                    self._record_asciinema_marker(
                        f"Episode {episode}: {len(commands)} commands", session
                    )

                if feedback and "ERROR:" in feedback:
                    # 在 parser 错误反馈中检查触发条件
                    if not replay_mode:
                        self._check_trigger_interventions(episode, feedback, chat)
                    prompt = (
                        f"Previous response had parsing errors:\n{feedback}\n\n"
                        f"Please fix these issues and provide a proper "
                        f"{self._get_error_response_type()}."
                    )
                    self._trajectory_records.append(
                        {
                            "episode": episode,
                            "replayed": replay_mode,
                            "prompt": prompt,
                            "response": response,
                            "commands": self._serialize_commands(commands),
                            "feedback": feedback,
                        }
                    )
                    continue

                _, terminal_output = self._execute_commands(commands, session)

                # 2c2. Episode 文件快照（用于与 oracle 轨迹对比 + Fork 重放）
                if self._enable_episode_snapshots and not replay_mode:
                    self._capture_episode_snapshot(
                        episode, commands, terminal_output, session
                    )
                    # 每 5 个 episode 保存一次 checkpoint tarball
                    # （用于 Fork 重放时恢复文件系统状态）
                    if episode > 0 and episode % 5 == 0:
                        self._save_checkpoint_tarball(episode, session)

                # 2d. 分析循环检测（连续分析命令 → 截断历史）
                if not replay_mode:
                    forced = self._check_analysis_loop(commands, episode, session, chat)
                    if forced:
                        # 截断历史后重新开始循环
                        prompt = self._limit_output_length(
                            session.get_incremental_output()
                        )
                        self._trajectory_records.append(
                            {
                                "episode": episode,
                                "replayed": replay_mode,
                                "prompt": prompt,
                                "response": response,
                                "commands": self._serialize_commands(commands),
                                "terminal_output": terminal_output,
                                "task_complete": False,
                            }
                        )
                        continue

                # 2e. 命令重复检测（实时监控）
                if not replay_mode:
                    self._check_command_repetition(commands, episode, chat)

                # 2f. 条件触发器：检查终端输出中的错误模式
                if not replay_mode:
                    self._check_trigger_interventions(episode, terminal_output, chat)

                # 2g. 定时保存轨迹快照（每 3 episodes）
                if not replay_mode and episode % 3 == 0:
                    self._save_trajectory_snapshot()

                if is_task_complete:
                    if self._pending_completion:
                        self._trajectory_records.append(
                            {
                                "episode": episode,
                                "replayed": replay_mode,
                                "prompt": prompt,
                                "response": response,
                                "commands": self._serialize_commands(commands),
                                "terminal_output": terminal_output,
                                "task_complete": True,
                            }
                        )
                        break

                    self._pending_completion = True
                    prompt = self._get_completion_confirmation_message(terminal_output)
                    self._trajectory_records.append(
                        {
                            "episode": episode,
                            "replayed": replay_mode,
                            "prompt": prompt,
                            "response": response,
                            "commands": self._serialize_commands(commands),
                            "terminal_output": terminal_output,
                            "task_complete": False,
                        }
                    )
                    continue

                self._pending_completion = False

                # 注入 Oracle 距离信号 + Dockerless 验证反馈
                extra_feedback = ""
                if not replay_mode:
                    dist_text = self._compute_oracle_distance(terminal_output, episode)
                    if dist_text:
                        extra_feedback += f"\n\n{dist_text}"
                    dock_text = self._run_dockerless_validation(terminal_output)
                    if dock_text:
                        extra_feedback += f"\n\n{dock_text}"

                if feedback and "WARNINGS:" in feedback:
                    prompt = (
                        f"Previous response had warnings:\n{feedback}\n\n"
                        f"{self._limit_output_length(terminal_output)}"
                        f"{extra_feedback}"
                    )
                else:
                    prompt = (
                        f"{self._limit_output_length(terminal_output)}{extra_feedback}"
                    )

                self._trajectory_records.append(
                    {
                        "episode": episode,
                        "replayed": replay_mode,
                        "prompt": prompt,
                        "response": response,
                        "commands": self._serialize_commands(commands),
                        "terminal_output": terminal_output,
                        "task_complete": False,
                    }
                )

        finally:
            # ── Episode 快照落盘 ──
            if self._enable_episode_snapshots:
                self._save_episode_snapshots()

            # ── 终极保险：轨迹落盘（与父类逻辑一致） ──
            if not self._trajectory_records:
                print("\n⚠️ [IntervenedTerminus] 轨迹记录为空，无内容可落盘。")
            else:
                output_path = self._trajectory_output_path or default_artifact_path(
                    "intervened-terminus-trajectory.json"
                )
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(
                        json.dumps(
                            self._trajectory_records, indent=2, ensure_ascii=False
                        ),
                        encoding="utf-8",
                    )
                    print(f"[IntervenedTerminus] 轨迹已保存至: {output_path}")
                except Exception as e:
                    self._logger.warning("Failed to save trajectory: %s", e)

    # ──────────────────────────────────────────────
    # perform_task （复用父类逻辑）
    # ──────────────────────────────────────────────

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
        time_limit_seconds: float | None = None,
    ) -> AgentResult:
        chat = Chat(self._llm)

        initial_prompt = self._prompt_template.format(
            instruction=instruction,
            terminal_state=self._limit_output_length(session.get_incremental_output()),
        )

        self._run_agent_loop(initial_prompt, session, chat, logging_dir, instruction)

        return AgentResult(
            total_input_tokens=chat.total_input_tokens,
            total_output_tokens=chat.total_output_tokens,
            failure_mode=FailureMode.NONE,
            timestamped_markers=self._timestamped_markers,
        )
