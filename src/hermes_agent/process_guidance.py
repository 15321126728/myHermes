# ruff: noqa: E501 -- Research guidance strings retain their exact text.

"""
ProcessGuidanceEngine — 基于论文思想的「过程引导」干预引擎。

核心思想（来自三篇论文的综合）：
  论文 1 (Failure as a Process):
    - 认知错误 > 执行错误；决定性错误发生在前 1/4 阶段
    - 恢复能力是区分成败的关键；存在修复窗口 (t_err → t_lock)
  论文 2 (HarnessFix):
    - 故障应定位到 7 个运行时层面
    - 结构化轨迹诊断 (HTIR-like) 优于原始 trace
  论文 3 (DataPRM):
    - 三元奖励：正确/可修复/不可修复
    - 环境交互验证 > 纯文本推理

本引擎代替「注入 oracle solution 命令」，改为：
  1. 分析 agent 的轨迹和行为模式
  2. 识别认知错误类型和运行时层面
  3. 生成诊断性引导提示（不给答案）
  4. 使用三元反馈评估当前状态
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

# ──────────────────────────────────────────────
# 错误类型定义
# ──────────────────────────────────────────────


@dataclass
class CognitiveError:
    """认知错误 — 信息已存在但被忽视/误解。"""

    type: str  # 错误类型标识
    description: str  # 人类可读描述
    evidence: list[str]  # 轨迹中的证据
    layer: str  # 所属运行时层面
    suggested_hint: str  # 引导提示（不给答案）


@dataclass
class ErrorDiagnosis:
    """完整的错误诊断结果。"""

    error_type: str  # cognitive / capability / environmental
    error_layer: str  # execution / tool / context / lifecycle / observability / validation / governance
    severity: float  # 0.0~1.0
    is_recoverable: bool  # 是否可修复
    diagnosis_text: str  # 诊断描述
    guidance: str  # 引导提示
    confidence: float  # 诊断置信度


# ──────────────────────────────────────────────
# 三元反馈级别
# ──────────────────────────────────────────────


class TernaryFeedback:
    """三元反馈 — 替代 binary pass/fail。"""

    CORRECT = "✓ CORRECT"
    RECOVERABLE = "⚠️ RECOVERABLE"
    IRRECOVERABLE = "✗ IRRECOVERABLE"

    @classmethod
    def format(cls, level: str, message: str, guidance: str = "") -> str:
        return f"{level}\n{message}\n{guidance}"


# ──────────────────────────────────────────────
# 认知错误检测器
# ──────────────────────────────────────────────


class CognitiveErrorDetector:
    """检测 agent 是否形成了对任务的错误理解。

    在轨迹的前 1/4 阶段重点监控以下信号：
    - 任务目标误解（agent 描述的任务与实际不符）
    - 工具选择错误（使用了与领域不符的工具）
    - 格式理解偏差（agent 对输出格式的理解有误）
    - 过早成功声明（agent 声称完成但明显遗漏关键步骤）
    - 分析瘫痪（重复分析但不执行）
    """

    # 各类任务的典型工作流关键词
    TASK_WORKFLOW_SIGNALS: dict[str, dict[str, list[str]]] = {
        "constraints-scheduling": {
            "required_tools": ["python3", "cat"],
            "required_actions": ["parse_ics", "check_constraints", "write_ics"],
            "output_files": ["meeting_scheduled.ics"],
            "forbidden_patterns": ["apt-get", "pip install", "icalendar"],
        },
        "feal-differential-cryptanalysis": {
            "required_tools": ["python3"],
            "required_actions": ["implement_attack", "differential_cryptanalysis"],
            "output_files": ["attack.py"],
            "forbidden_patterns": [],
        },
        "protein-assembly": {
            "required_tools": ["python3", "curl"],
            "required_actions": ["fetch_pdb", "fetch_fpbase", "design_gblock"],
            "output_files": ["gblock.txt"],
            "forbidden_patterns": [],
        },
        "torch-tensor-parallelism": {
            "required_tools": ["python3"],
            "required_actions": ["implement_linear", "test_sharding"],
            "output_files": ["parallel_linear.py"],
            "forbidden_patterns": [],
        },
    }

    # 通用的认知错误模式
    COGNITIVE_PATTERNS: list[dict[str, Any]] = [
        {
            "name": "task_misunderstanding",
            "signals": [
                r"i think the task is.*(wrong|different)",
                r"this seems (easy|trivial|simple)",
                r"i'll just (cat|ls|echo)",
            ],
            "layer": "context",
            "description": "Agent 对任务目标的理解有偏差",
            "hint_template": "你的任务理解似乎有偏差。请重新阅读任务描述，重点关注：输出文件的格式要求和需要完成的具体步骤。",
        },
        {
            "name": "premature_success",
            "signals": [
                r"task (complete|done|finished)",
                r"(done|finished|complete)!",
                r"i have (completed|finished) the task",
            ],
            "layer": "validation",
            "description": "Agent 过早声称任务完成但未验证",
            "hint_template": "你声称任务已经完成，但输出文件似乎不完整或格式有误。请先通过 `cat` 确认输出文件的内容和格式是否符合要求，然后运行测试验证。",
        },
        {
            "name": "analysis_paralysis",
            "signals": [
                r"let me (check|verify|analyze|look at|examine)",
                r"first, (let|i need|we need) to (understand|check|examine)",
                r"i should (check|verify|examine|analyze) (if|whether)",
            ],
            "layer": "lifecycle",
            "description": "Agent 陷入分析瘫痪 — 重复分析不执行",
            "hint_template": "你已经分析了足够的上下文。现在需要执行具体的操作来推进任务。请直接输出所需的文件内容。",
        },
        {
            "name": "wrong_tool_choice",
            "signals": [
                r"apt-get install|pip install|conda install",
                r"npm install|gem install",
            ],
            "layer": "execution",
            "description": "Agent 试图安装外部依赖",
            "hint_template": "当前环境可能没有网络连接，无法安装新包。请使用环境中已预装的工具，或者仅使用 Python 标准库完成任务。",
        },
        {
            "name": "endless_reading",
            "signals": [
                r"cat.*\.(fasta|ics|py|txt|yaml|json|csv)",
                r"head.*\.(fasta|ics|py)",
                r"tail.*\.(fasta|ics|py)",
                r"less|more|vim|nano",
            ],
            "layer": "tool",
            "description": "Agent 反复读取已有文件内容",
            "hint_template": "你已经多次读取了输入文件。请基于已有信息直接推进任务，而不是继续查看文件内容。",
        },
    ]

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.task_signals = self.TASK_WORKFLOW_SIGNALS.get(task_id, {})
        self._command_history: list[str] = []
        self._analysis_count: int = 0
        self._read_count: int = 0

    def analyze_episode(
        self,
        episode: int,
        commands: list[str],
        terminal_output: str,
        total_episodes: int,
        has_output_file: bool = False,
    ) -> list[CognitiveError]:
        """分析单 episode，返回检测到的认知错误列表。"""
        errors: list[CognitiveError] = []
        cmd_text = " ".join(commands).lower()
        output_lower = terminal_output.lower()

        self._command_history.extend(commands)

        # 合并命令文本用于模式匹配
        combined_text = cmd_text + "\n" + output_lower

        # 已生成输出文件 → 抑制"无尽读取"等过时警告
        if has_output_file:
            # 只检测关键错误（过早成功、分析瘫痪），跳过读取警告
            allowed_patterns = ["premature_success", "analysis_paralysis"]
            for pattern in self.COGNITIVE_PATTERNS:
                if pattern["name"] not in allowed_patterns:
                    continue
                for signal in pattern["signals"]:
                    if re.search(signal, combined_text, re.IGNORECASE):
                        errors.append(
                            CognitiveError(
                                type=pattern["name"],
                                description=pattern["description"],
                                evidence=[f"matched pattern: {signal}"],
                                layer=pattern["layer"],
                                suggested_hint=pattern["hint_template"],
                            )
                        )
                        break
        else:
            # 检查通用认知错误模式（全量检查）
            for pattern in self.COGNITIVE_PATTERNS:
                for signal in pattern["signals"]:
                    if re.search(signal, combined_text, re.IGNORECASE):
                        errors.append(
                            CognitiveError(
                                type=pattern["name"],
                                description=pattern["description"],
                                evidence=[f"matched pattern: {signal}"],
                                layer=pattern["layer"],
                                suggested_hint=pattern["hint_template"],
                            )
                        )
                        break

        # 检查领域特定的缺失行为
        if self.task_signals:
            for forbidden in self.task_signals.get("forbidden_patterns", []):
                if (
                    forbidden in combined_text
                    and forbidden not in self._command_history[-3:]
                ):
                    errors.append(
                        CognitiveError(
                            type="forbidden_action",
                            description=f"Agent 试图执行禁止的操作: {forbidden}",
                            evidence=[f"found forbidden pattern: {forbidden}"],
                            layer="execution",
                            suggested_hint=f"操作 '{forbidden}' 在当前环境中不可用或不允许。请使用环境中已有的工具。",
                        )
                    )

        return errors

    def get_progress_summary(self) -> dict[str, Any]:
        """返回当前进度摘要。"""
        return {
            "total_commands": len(self._command_history),
            "analysis_count": self._analysis_count,
            "read_count": self._read_count,
        }


# ──────────────────────────────────────────────
# 运行时层面诊断
# ──────────────────────────────────────────────


class LayerDiagnoser:
    """诊断错误发生在哪个运行时层面。

    参考 HarnessFix 的 7 层模型：
    - execution: 执行层（命令找不到、依赖缺失）
    - tool: 工具层（只用读工具不用写工具）
    - context: 上下文层（对任务理解错误）
    - lifecycle: 生命周期层（卡在循环中）
    - observability: 可观测性层（agent 无法感知自身状态）
    - validation: 验证层（输出格式错误）
    - governance: 治理层（违反约束规则）
    """

    LAYER_SIGNALS: dict[str, list[dict[str, Any]]] = {
        "execution": [
            {
                "pattern": r"command not found",
                "hint": "命令不存在。请检查命令名称是否正确，或使用 `which <command>` 查找可用工具。",
            },
            {
                "pattern": r"permission denied",
                "hint": "权限不足。请检查文件权限或使用 sudo（如可用）。",
            },
            {
                "pattern": r"no such file or directory",
                "hint": "文件或目录不存在。请检查路径是否正确。",
            },
            {
                "pattern": r"ModuleNotFoundError",
                "hint": "Python 模块未安装。请使用 Python 标准库或检查模块名称。",
            },
        ],
        "tool": [
            {
                "pattern": r"(cat|head|tail|less|more).*(cat|head|tail|less|more)",
                "hint": "你一直在使用读取工具，但没有使用任何写入工具来生成输出文件。",
            },
            {
                "pattern": r"(ls|find).*(ls|find)",
                "hint": "重复的文件列表操作不会推进任务。请直接操作文件内容。",
            },
        ],
        "context": [
            {
                "pattern": r"i don't know what (to do|the task)",
                "hint": "回顾任务描述中的关键约束和输出要求。",
            },
            {
                "pattern": r"what (should|do) i (do|need)",
                "hint": "重新阅读任务描述，重点关注需要生成什么文件以及它的格式要求。",
            },
        ],
        "lifecycle": [
            {
                "pattern": r"(let me|i need to|i should) (first|start by|begin by)",
                "hint": "不要继续分析。直接执行具体的文件操作命令。",
            },
            {
                "pattern": r"(check|verify|analyze|understand).*(check|verify|analyze|understand)",
                "hint": "分析循环检测：连续的分析操作没有产生实质性进展。请执行一个具体的写文件操作。",
            },
        ],
        "validation": [
            {
                "pattern": r"(error|wrong|incorrect).*format",
                "hint": "输出文件格式可能有误。请检查格式规范是否符合任务要求。",
            },
            {
                "pattern": r"test.*fail",
                "hint": "测试失败。请检查输出文件的内容和格式，并与任务描述中的要求进行比对。",
            },
        ],
    }

    def diagnose(
        self, episode: int, commands: list[str], terminal_output: str
    ) -> list[dict[str, Any]]:
        """诊断当前 episode 中的错误层面。"""
        findings: list[dict[str, Any]] = []
        combined = terminal_output.lower() + "\n" + " ".join(commands).lower()

        for layer, signals in self.LAYER_SIGNALS.items():
            for signal in signals:
                if re.search(signal["pattern"], combined, re.IGNORECASE):
                    findings.append(
                        {
                            "layer": layer,
                            "hint": signal["hint"],
                            "matched": signal["pattern"],
                        }
                    )
                    break  # 每层只报告第一个匹配

        return findings


# ──────────────────────────────────────────────
# 三元反馈评估器
# ──────────────────────────────────────────────


class TernaryEvaluator:
    """评估当前 episode 的状态为三元反馈之一。

    CORRECT: 当前步骤正确，继续
    RECOVERABLE: 当前步骤有误但可修复，提供诊断
    IRRECOVERABLE: 当前轨迹无法挽回，建议重启
    """

    @staticmethod
    def _has_success_signal(text: str) -> bool:
        success_patterns = [
            r"\b\d+\s+tests?\s+passed\b",
            r"\b\d+\s+passed\b",
            r"\ball\s+tests?\s+passed\b",
            r"\btests?\s+passed\b",
            r"\bpassed\b",
            r"\bsuccess(?:ful)?\b",
        ]
        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in success_patterns
        )

    @staticmethod
    def _has_failure_signal(text: str) -> bool:
        failure_patterns = [
            r"\berror\b",
            r"\bfail(?:ed|ure)?\b",
            r"traceback",
            r"exception",
        ]
        return any(
            re.search(pattern, text, re.IGNORECASE) for pattern in failure_patterns
        )

    def evaluate(
        self,
        episode: int,
        commands: list[str],
        terminal_output: str,
        distance_score: float | None = None,
        is_analysis_loop: bool = False,
        has_output_file: bool = False,
    ) -> tuple[str, str, str]:
        """返回 (level, message, guidance)。"""

        combined = (terminal_output or "") + " " + " ".join(commands)
        combined_l = combined.lower()

        # 不可修复的条件
        if is_analysis_loop and episode > 10:
            return (
                TernaryFeedback.IRRECOVERABLE,
                "检测到分析瘫痪且已超过 10 个 episode，当前路径难以挽回。",
                "建议：回到任务描述重新理解需求，或者考虑换个完全不同的方法。",
            )

        if distance_score is not None and distance_score > 0.9 and episode > 15:
            return (
                TernaryFeedback.IRRECOVERABLE,
                f"距离分数持续很高 ({distance_score:.2f}) 且已消耗大量 episode。",
                "建议：重新评估任务理解是否有根本性偏差，考虑重启。",
            )

        # 可修复的条件
        if self._has_failure_signal(combined_l):
            return (
                TernaryFeedback.RECOVERABLE,
                "检测到错误信息。",
                "请仔细阅读错误信息，定位问题所在。常见原因：文件路径不正确、格式不符合要求、缺少必要步骤。",
            )

        if is_analysis_loop:
            return (
                TernaryFeedback.RECOVERABLE,
                "检测到分析循环 — 你一直在重复分析而没有执行。",
                "停止所有分析命令。直接执行生成输出文件的操作。思考：你现在离目标只差一个写文件的操作。",
            )

        if distance_score is not None and distance_score > 0.5:
            return (
                TernaryFeedback.RECOVERABLE,
                f"距目标还有一定距离 (分数={distance_score:.2f})。",
                "检查各维度中最差的指标，优先解决那个问题。",
            )

        # 正确的条件
        if has_output_file and self._has_success_signal(combined_l):
            return (
                TernaryFeedback.CORRECT,
                "输出文件已生成且测试通过。",
                "继续验证其他约束是否满足。",
            )

        if distance_score is not None and distance_score < 0.2:
            return (
                TernaryFeedback.CORRECT,
                f"距离分数很低 ({distance_score:.2f})，接近目标。",
                "继续推进，确保输出文件完全符合要求。",
            )

        # 默认：中性，提供一般性引导
        return (
            TernaryFeedback.RECOVERABLE,
            "需要确认当前进度。",
            "请检查你是否已经生成了所需的输出文件。如果没有，请直接执行写文件操作。",
        )


# ──────────────────────────────────────────────
# 自适应 Episode 管理器
# ──────────────────────────────────────────────


class AdaptiveEpisodeManager:
    """动态管理 episode 限制。

    核心原则：
    - 仅在 agent 仍在积极工作时延长
    - 分析瘫痪时不延长
    - 恢复尝试时延长
    """

    def __init__(self, base_max_episodes: int = 25):
        self.base_max = base_max_episodes
        self._progress_history: list[float] = []
        self._episode_type_history: list[str] = []  # "active", "analysis", "recovery"

    def record_episode(self, episode_type: str, progress: float = 0.0):
        """记录 episode 类型和进度。"""
        self._episode_type_history.append(episode_type)
        self._progress_history.append(progress)

    def should_extend(self, current_episode: int) -> bool:
        """判断是否需要延长 episode 限制。"""
        if current_episode < self.base_max:
            return False  # 未到基础限制

        recent = (
            self._episode_type_history[-5:]
            if len(self._episode_type_history) >= 5
            else self._episode_type_history
        )

        # 分析瘫痪 → 不延长
        if recent.count("analysis") >= 3:
            return False

        # 正在恢复 → 延长
        if "recovery" in recent:
            return True

        # 积极工作但慢 → 延长
        if recent.count("active") >= 3:
            # 检查是否有进展
            recent_progress = (
                self._progress_history[-5:]
                if len(self._progress_history) >= 5
                else self._progress_history
            )
            if len(recent_progress) >= 2 and recent_progress[-1] > recent_progress[0]:
                return True

        return False

    def get_max_episodes(self, current_episode: int) -> int:
        """返回当前建议的最大 episode 数。"""
        if self.should_extend(current_episode):
            return current_episode + 10  # 每次延长 10 轮
        return self.base_max


# ──────────────────────────────────────────────
# 主引导引擎
# ──────────────────────────────────────────────


class ProcessGuidanceEngine:
    """过程引导引擎 — 综合分析轨迹并生成引导。"""

    def __init__(self, task_id: str, base_max_episodes: int = 25):
        self.task_id = task_id
        self.cognitive_detector = CognitiveErrorDetector(task_id)
        self.layer_diagnoser = LayerDiagnoser()
        self.ternary_evaluator = TernaryEvaluator()
        self.episode_manager = AdaptiveEpisodeManager(base_max_episodes)

        self._episodes_processed: int = 0
        self._last_guidance: str = ""

    def process_episode(
        self,
        episode: int,
        commands: list[str],
        terminal_output: str,
        total_episodes: int,
        distance_score: float | None = None,
        is_analysis_loop: bool = False,
        has_output_file: bool = False,
    ) -> str:
        """处理单个 episode，返回引导提示文本。

        Args:
            episode: 当前 episode 编号
            commands: 执行的命令列表
            terminal_output: 终端输出
            total_episodes: 总 episode 数
            distance_score: Oracle 距离分数（可选）
            is_analysis_loop: 是否检测到分析循环
            has_output_file: 是否已生成输出文件

        Returns:
            str: 注入到 prompt 的引导文本
        """
        self._episodes_processed += 1

        # 1. 检测认知错误
        cognitive_errors = self.cognitive_detector.analyze_episode(
            episode,
            commands,
            terminal_output,
            total_episodes,
            has_output_file=has_output_file,
        )

        # 2. 层面诊断
        layer_findings = self.layer_diagnoser.diagnose(
            episode, commands, terminal_output
        )

        # 3. 三元反馈评估
        fb_level, fb_message, fb_guidance = self.ternary_evaluator.evaluate(
            episode,
            commands,
            terminal_output,
            distance_score,
            is_analysis_loop,
            has_output_file,
        )

        # 4. 确定 episode 类型
        if is_analysis_loop:
            episode_type = "analysis"
        elif cognitive_errors and any(
            e.type == "premature_success" for e in cognitive_errors
        ):
            episode_type = "recovery"
        elif has_output_file or ("write" in " ".join(commands).lower()):
            episode_type = "active"
        else:
            episode_type = "active"

        # 估算进度（如果有距离分数）
        progress = 1.0 - (distance_score or 1.0)
        self.episode_manager.record_episode(episode_type, progress)

        # 5. 检查是否需要自适应延长
        extension_note = ""
        if self.episode_manager.should_extend(episode):
            new_max = self.episode_manager.get_max_episodes(episode)
            extension_note = (
                f"\n（系统：检测到你在积极工作，已将 episode 上限延长至 {new_max}。）"
            )

        # 6. 组合引导文本
        guidance_parts = [f"【过程引导 - Episode {episode}】"]

        # 三元反馈
        guidance_parts.append(f"\n{fb_level}")
        guidance_parts.append(f"状态：{fb_message}")
        if fb_guidance:
            guidance_parts.append(f"建议：{fb_guidance}")

        # 认知错误
        if cognitive_errors and fb_level != TernaryFeedback.CORRECT:
            # 只取第一个最严重的认知错误
            ce = cognitive_errors[0]
            guidance_parts.append(f"\n⚠️ 认知提示：{ce.suggested_hint}")

        # 层面诊断
        if layer_findings and fb_level != TernaryFeedback.CORRECT:
            lf = layer_findings[0]  # 最高优先级的发现
            guidance_parts.append(f"\n🔍 {lf['hint']}")

        # 自适应延长
        if extension_note:
            guidance_parts.append(extension_note)

        # 框架信息（如果距离分数可用）
        if distance_score is not None:
            guidance_parts.append(f"\n📊 进度指标：距离目标 {distance_score:.1%}")

        guidance = "\n".join(guidance_parts)
        self._last_guidance = guidance
        return guidance
