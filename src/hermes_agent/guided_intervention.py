# ruff: noqa: E501 -- Research prompts are kept as readable, exact text.

"""
GuidedInterventionAgent — 基于「过程引导」而非「答案泄漏」的干预 Agent。

继承自 IntervenedTerminusAgent，在保留其干预框架的基础上，
将干预策略从「注入 oracle solution 命令」改为「基于轨迹分析的过程引导」。

核心改进（对应三篇论文）：
  1. 过程引导（替代答案泄漏）：使用 ProcessGuidanceEngine 生成诊断性提示
  2. 认知错误检测：在前 1/4 阶段重点监控任务理解偏差
  3. 分层诊断：定位错误到具体的运行时层面
  4. 三元反馈：CORRECT / RECOVERABLE / IRRECOVERABLE
  5. 自适应 Episode 管理：根据进程质量动态调整限制
"""

from __future__ import annotations

import itertools
import json
import re
import shlex
from pathlib import Path
from typing import Any

from terminal_bench.llms.chat import Chat
from terminal_bench.terminal.tmux_session import TmuxSession

from hermes_agent.ablation import AblationConfig
from hermes_agent.intervened_terminus import IntervenedTerminusAgent
from hermes_agent.process_guidance import (
    ProcessGuidanceEngine,
    TernaryFeedback,
)
from hermes_agent.replay_support import default_artifact_path
from hermes_agent.task_contract import TaskContract


class GuidedInterventionAgent(IntervenedTerminusAgent):
    """基于过程引导的干预 Agent。

    相比 IntervenedTerminusAgent 的改进：
    - 时刻表 payload 不允许包含 oracle solution 命令​​
    - 自动通过 ProcessGuidanceEngine 生成诊断引导
    - 三元反馈替代 binary 距离分数
    - 自适应 episode 管理
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
        # --- 干预参数 ---
        intervention_schedule: Any = None,
        intervention_triggers: Any = None,
        inject_before_episode: int = -1,
        # --- 快照 ---
        enable_episode_snapshots: bool = False,
        # --- 过程引导参数 ---
        enable_process_guidance: bool = True,  # 启用过程引导（默认开）
        guidance_task_id: str = "",  # 任务 ID（用于领域特定引导）
        guidance_base_max: int | None = None,  # 默认与实际运行上限一致
        # --- 知识提示参数 ---
        knowledge_file: str | None = None,  # 容器内路径；未设置时按任务自动发现
        ablation_config: dict[str, bool] | None = None,
        **kwargs: Any,
    ):
        knowledge_max_hints = int(kwargs.pop("knowledge_max_hints", 3))
        enable_comprehension_check = bool(
            kwargs.pop("enable_comprehension_check", True)
        )
        max_trajectory_resets = int(kwargs.pop("max_trajectory_resets", 1))
        config = AblationConfig.from_mapping(ablation_config)
        if not enable_process_guidance:
            config = config.with_disabled(
                "cognitive_detection",
                "layer_diagnosis",
                "ternary_feedback",
                "adaptive_episodes",
            )
        if not enable_comprehension_check:
            config = config.with_disabled("comprehension_check")
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
            intervention_schedule=intervention_schedule,
            intervention_triggers=intervention_triggers,
            inject_before_episode=inject_before_episode,
            enable_episode_snapshots=enable_episode_snapshots,
            enable_oracle_distance=False,  # 由过程引导替代
            enable_dockerless=False,
            **kwargs,
        )

        # 过程引导引擎
        self._ablation_config = config
        self._enable_process_guidance = config.process_guidance_enabled()
        self._guidance_engine: ProcessGuidanceEngine | None = None
        if self._enable_process_guidance:
            self._guidance_engine = ProcessGuidanceEngine(
                task_id=guidance_task_id,
                base_max_episodes=guidance_base_max or self._max_episodes,
                ablation_config=config,
            )

        self._guidance_task_id = guidance_task_id

        # 知识提示状态
        task_knowledge_files = {
            "dna-assembly": "/app/KNOWLEDGE_GOLDEN_GATE.md",
            "feal-differential-cryptanalysis": "/app/KNOWLEDGE_FEAL.md",
            "protein-assembly": "/app/KNOWLEDGE_FUSION.md",
        }
        self._knowledge_file = None
        if config.knowledge_hints:
            self._knowledge_file = knowledge_file or task_knowledge_files.get(
                guidance_task_id
            )
        self._knowledge_available: bool | None = None
        self._knowledge_hint_sent: bool = False
        self._knowledge_hint_count: int = 0
        self._knowledge_max_hints = max(0, knowledge_max_hints)

        # 任务理解校验状态
        self._comprehension_enabled = config.comprehension_check
        self._comprehension_sent: bool = False  # 是否已向 agent 提问
        self._comprehension_checked: bool = False  # 是否已检查 agent 的回答
        self._comprehension_episode: int = 0  # 提问所在的 episode
        self._active_comprehension_questions: list[dict[str, Any]] = []
        self._trajectory_reset_count = 0
        self._max_trajectory_resets = max(0, max_trajectory_resets)

        # 运行验证器收集状态（轻量级，不依赖 Docker）
        self._has_output_file: bool = False
        self._output_file_path: str = ""
        self._artifact_requirement_detected = False

        self._trajectory_records.append(
            {
                "record_type": "run_config",
                "ablation": config.as_dict(),
                "guidance_task_id": guidance_task_id,
                "base_episode_limit": guidance_base_max or self._max_episodes,
                "initial_episode_limit": self._max_episodes,
            }
        )

        self._logger.info(
            f"GuidedInterventionAgent initialized: "
            f"task={guidance_task_id}, "
            f"process_guidance={self._enable_process_guidance}, "
            f"base_max={guidance_base_max}"
        )

    # ──────────────────────────────────────────────
    # 领域特定的输出文件检测
    # ──────────────────────────────────────────────

    @staticmethod
    def _container_file_nonempty(session: TmuxSession, path: str) -> bool:
        try:
            result = session.container.exec_run(
                ["bash", "-lc", f"test -s {shlex.quote(path)}"]
            )
            return result.exit_code == 0
        except Exception:
            return False

    def _check_output_file(
        self,
        terminal_output: str,
        session: TmuxSession,
        instruction: str = "",
    ) -> bool:
        """在容器内验证任务声明的输出产物存在且非空。"""
        contract = TaskContract.from_instruction(instruction) if instruction else None
        if contract and (contract.output_paths or contract.optional_output_groups):
            self._artifact_requirement_detected = True
            required_ready = all(
                self._container_file_nonempty(session, path)
                for path in contract.output_paths
            )
            optional_ready = all(
                any(self._container_file_nonempty(session, path) for path in group)
                for group in contract.optional_output_groups
            )
            if required_ready and optional_ready:
                paths = list(contract.output_paths)
                paths.extend(group[0] for group in contract.optional_output_groups)
                self._output_file_path = ", ".join(paths)
                return True
            return False

        output_triggers = {
            "constraints-scheduling": [
                "meeting_scheduled.ics",
                "/app/meeting_scheduled.ics",
            ],
            "feal-differential-cryptanalysis": ["attack.py", "/app/attack.py"],
            "protein-assembly": ["gblock.txt", "/app/gblock.txt"],
            "torch-tensor-parallelism": [
                "parallel_linear.py",
                "/app/parallel_linear.py",
            ],
        }

        triggers = output_triggers.get(self._guidance_task_id, [])
        absolute_triggers = [
            trigger if trigger.startswith("/app/") else f"/app/{trigger}"
            for trigger in triggers
        ]
        if absolute_triggers:
            self._artifact_requirement_detected = True
            for trigger in dict.fromkeys(absolute_triggers):
                if self._container_file_nonempty(session, trigger):
                    self._output_file_path = trigger
                    return True
            return False

        # 无任务契约时，只把终端文本用于发现候选路径，最终仍以容器为准。
        file_candidates = re.findall(
            r"(?<!/)\b[A-Za-z0-9_.-]+\.(?:py|txt|json|csv|ics|parquet|fasta|fa|fna)\b",
            terminal_output,
        )
        for candidate in file_candidates:
            possible_path = f"/app/{candidate}"
            if self._container_file_nonempty(session, possible_path):
                self._output_file_path = possible_path
                return True

        return False

    def _knowledge_file_exists(self, session: TmuxSession) -> bool:
        if not self._knowledge_file:
            return False
        if self._knowledge_available is None:
            self._knowledge_available = self._container_file_nonempty(
                session, self._knowledge_file
            )
        return self._knowledge_available

    # ──────────────────────────────────────────────
    # 知识提示：AI 缺少领域知识时提示阅读知识文档
    # ──────────────────────────────────────────────

    def _maybe_inject_knowledge_hint(
        self, episode: int, response: str, terminal_output: str
    ) -> str:
        """检测 AI 是否因缺少领域知识而卡住，若是则提示其阅读知识文档。

        设计原则：
        - 知识文档只提供「领域概念 + 方法」，不包含答案（避免答案泄漏）
        - 第一个实时 episode 主动告知知识文档的存在
        - 后续 episode 仅在检测到「知识缺失信号」（疑惑、不确定、请求解释等）时提醒
        - 最多注入 knowledge_max_hints 次，避免过度干扰

        返回注入的提示文本（空串表示不注入）。
        """
        if not self._knowledge_file:
            return ""

        # ── 首个实时 episode：主动告知知识文档存在 ──
        if not self._knowledge_hint_sent:
            self._knowledge_hint_sent = True
            self._knowledge_hint_count += 1
            self._trajectory_records.append(
                {
                    "episode": episode,
                    "intervention_type": "knowledge_hint",
                    "kind": "intro",
                    "knowledge_hint": self._knowledge_intro_hint(),
                }
            )
            return self._knowledge_intro_hint()

        # ── 后续：检测知识缺失信号 ──
        if self._knowledge_hint_count >= self._knowledge_max_hints:
            return ""

        combined = (response or "") + "\n" + (terminal_output or "")
        combined_lower = combined.lower()

        # 知识缺失信号：agent 表达疑惑、请求解释、或表现出不知道怎么做
        knowledge_gap_patterns = [
            r"i (don't|do not) (know|understand|know how)",
            r"i'm not (sure|familiar)",
            r"i am not (sure|familiar|clear)",
            r"what (is|are|does) (this|a|the|an)",
            r"how (do|does|to) i",
            r"(not familiar|unfamiliar|never (seen|heard|used))",
            r"explain (to me|how|what)",
            r"no idea",
            r"(help me|can you tell me|please tell me).*(what|how)",
            r"i don't know (what|how|which|where)",
            r"what does (golden gate|bsai|overhang|fret|smiles|dhfr|snap|flag) mean",
        ]

        for pattern in knowledge_gap_patterns:
            if re.search(pattern, combined_lower):
                self._knowledge_hint_count += 1
                hint = (
                    "\n\n[Knowledge Hint] It looks like you might be missing some "
                    "domain knowledge needed for this task. A knowledge reference "
                    f"document is available at {self._knowledge_file} (in the container). "
                    "Read it to understand the domain concepts and methodology: "
                    f"`cat {self._knowledge_file}`. It contains background knowledge, "
                    "not the answer, so use it to guide your own solution."
                )
                self._trajectory_records.append(
                    {
                        "episode": episode,
                        "intervention_type": "knowledge_hint",
                        "kind": "gap_detected",
                        "matched_pattern": pattern,
                        "knowledge_hint": hint,
                    }
                )
                return hint

        return ""

    def _knowledge_intro_hint(self) -> str:
        """首次知识文档介绍提示（不含答案，只告知存在与方法提示）。"""
        return (
            "\n\n[Knowledge Hint] This task may require specialized domain knowledge "
            "that is not obvious from the task description alone. A knowledge reference "
            f"document is available in the container at {self._knowledge_file}. "
            "It explains the domain concepts and methodology (it does NOT contain the "
            "answer). If you are not already an expert in this domain, it is strongly "
            "recommended that you read it first: `cat {self._knowledge_file}`."
        )

    # ──────────────────────────────────────────────
    # 任务理解校验（Comprehension Check）
    # 通过向 agent 提问关键约束，从回答中检测是否误解任务
    # ──────────────────────────────────────────────

    # 每个任务的理解校验问题集：
    #   question: 向 agent 提出的问题（只问"你要做什么/约束是什么"，不问答案）
    #   expect:   预期回答中应出现的关键词（任一命中即通过，大小写不敏感）
    #   hint:     未通过时注入的纠正提示（只指出约束，不给答案）
    COMPREHENSION_QUESTIONS: dict[str, list[dict[str, Any]]] = {
        "feal-differential-cryptanalysis": [
            {
                "question": "你的攻击要恢复哪个密钥？（索引/位置）",
                "expect": [
                    "key[5]",
                    "key 5",
                    "key index 5",
                    "第5",
                    "5th",
                    "最后一轮",
                    "last round",
                ],
                "hint": "注意：目标是 key[5]（最后一轮的轮密钥），不是 key[0] 或全部密钥。",
            },
            {
                "question": "你的攻击要写在哪？函数名和参数是什么？",
                "expect": [
                    "attack.py",
                    "attack(",
                    "def attack",
                    "encrypt_fn",
                    "encrypt function",
                ],
                "hint": "攻击应实现为 /app/attack.py 中的 attack(encrypt_fn) 函数。",
            },
            {
                "question": "攻击的运行时限制是多少秒？",
                "expect": ["30", "thirty", "less than 30", "30 秒", "30秒"],
                "hint": "攻击必须在 30 秒内运行完成。",
            },
            {
                "question": "提示说每个轮密钥由什么推导？这有什么含义？",
                "expect": [
                    "16 bit",
                    "16-bit",
                    "16位",
                    "seed",
                    "65536",
                    "2^16",
                    "2**16",
                ],
                "hint": "每个轮密钥由 16 位 seed 推导（key[i] = seed*1234567 & 0xFFFFFFFF），所以 key[5] 只有 65536 个可能值。",
            },
            {
                "question": "你打算用什么类型的密码分析？（差分/线性/暴力）",
                "expect": [
                    "differential",
                    "差分",
                    "chosen plaintext",
                    "特征",
                    "characteristic",
                ],
                "hint": "任务要求差分密码分析（differential cryptanalysis），利用概率-1 差分特征。",
            },
        ],
        "dna-assembly": [
            {
                "question": "你的输出文件叫什么名字？",
                "expect": ["primers.fasta"],
                "hint": "输出文件应为 /app/primers.fasta。",
            },
            {
                "question": "你使用哪个酶做 Golden Gate 组装？",
                "expect": ["BsaI", "bsai", "BsaI-HF", "bsai-hf"],
                "hint": "使用 BsaI-HF v2 酶，识别位点 GGTCTC。",
            },
            {
                "question": "退火区的长度范围是多少？（多少到多少核苷酸）",
                "expect": ["15", "45", "15 到 45", "15-45"],
                "hint": "退火区长度必须在 15 到 45 个核苷酸之间。",
            },
            {
                "question": "熔解温度的约束是什么？（范围，以及配对差）",
                "expect": ["58", "72", "5", "58-72"],
                "hint": "Tm 在 58-72°C，每对 fwd/rev 的 Tm 差 ≤ 5°C。",
            },
            {
                "question": "引物头（header）的格式是什么？",
                "expect": ["TEMPLATENAME_DIR", ">input", "fwd", "rev", "_fwd", "_rev"],
                "hint": "头格式为 >TEMPLATENAME_DIR，如 >input_fwd。",
            },
        ],
        "protein-assembly": [
            {
                "question": "你的输出文件叫什么？",
                "expect": ["gblock.txt", "gblock"],
                "hint": "输出应为 /app/gblock.txt，只含 DNA 序列。",
            },
            {
                "question": "子蛋白的连接顺序是什么？（N→C 端）",
                "expect": [
                    "antibody",
                    "donor",
                    "dhfr",
                    "acceptor",
                    "binder",
                    "抗体",
                    "供体",
                    "受体",
                ],
                "hint": "顺序：antibody binder - donor - DHFR - acceptor - molecule binder。",
            },
            {
                "question": "GC 含量约束是什么？（窗口和范围）",
                "expect": ["30", "70", "50 nt", "50nt", "50 碱基", "30-70"],
                "hint": "任意 50 nt 窗口 GC 含量 30-70%。",
            },
            {
                "question": "总长度上限是多少？",
                "expect": ["3000", "≤3000", "3000 nt"],
                "hint": "gBlock 总长度 ≤ 3000 核苷酸。",
            },
            {
                "question": "序列是 DNA 还是蛋白？（gBlock 是什么）",
                "expect": ["DNA", "dna", "核苷酸", "nucleotide"],
                "hint": "gBlock 是 DNA 序列（不是氨基酸序列），需要反向翻译。",
            },
        ],
        "torch-tensor-parallelism": [
            {
                "question": "你的输出文件叫什么？",
                "expect": ["parallel_linear.py"],
                "hint": "输出应为 /app/parallel_linear.py。",
            },
            {
                "question": "需要实现哪两个类？",
                "expect": ["ColumnParallelLinear", "RowParallelLinear"],
                "hint": "需要实现 ColumnParallelLinear 和 RowParallelLinear 两个类。",
            },
            {
                "question": "张量并行中列分割和行分割分别如何划分权重？",
                "expect": [
                    "列",
                    "column",
                    "行",
                    "row",
                    "dim",
                    "维",
                    "out_features",
                    "in_features",
                ],
                "hint": "ColumnParallel 沿输出维分割权重，RowParallel 沿输入维分割权重。",
            },
        ],
        "constraints-scheduling": [
            {
                "question": "你的输出文件叫什么？格式是什么？",
                "expect": ["meeting_scheduled.ics", ".ics", "ics"],
                "hint": "输出应为 /app/meeting_scheduled.ics（ICS 格式）。",
            },
            {
                "question": "这个调度任务要满足的约束有哪些？（提到至少一个）",
                "expect": [
                    "meeting",
                    "会议",
                    "time",
                    "时间",
                    "conflict",
                    "冲突",
                    "person",
                    "人",
                ],
                "hint": "需要为所有参会人安排一个无冲突的会议时间。",
            },
        ],
        "analyze-access-logs": [
            {
                "question": "你的输出文件叫什么？",
                "expect": ["analysis.txt", ".txt", "result"],
                "hint": "输出应为分析结果文件（文本格式）。",
            },
        ],
        "heterogeneous-dates": [
            {
                "question": "你的输出文件叫什么？",
                "expect": ["avg_temp.txt", ".txt"],
                "hint": "输出应为 /app/avg_temp.txt。",
            },
        ],
        "csv-to-parquet": [
            {
                "question": "你的输出文件是什么格式？",
                "expect": ["parquet", ".parquet"],
                "hint": "输出应为 Parquet 格式。",
            },
        ],
    }

    def _build_comprehension_prompt(self, instruction: str = "") -> str:
        """构造 Ep0 的理解校验问题文本。"""
        questions = list(self.COMPREHENSION_QUESTIONS.get(self._guidance_task_id, []))
        if not questions and instruction:
            contract = TaskContract.from_instruction(instruction)
            if contract.output_paths:
                questions.append(
                    {
                        "question": "任务要求生成哪些最终输出文件？",
                        "expect": list(contract.output_paths),
                        "min_matches": len(contract.output_paths),
                        "hint": "请重新核对任务中明确声明的最终输出路径。",
                    }
                )
            requirement_text = " ".join(contract.requirements[:3]).lower()
            stopwords = {
                "about",
                "after",
                "before",
                "create",
                "file",
                "from",
                "into",
                "output",
                "should",
                "task",
                "that",
                "then",
                "this",
                "using",
                "with",
            }
            keywords = list(
                dict.fromkeys(
                    word
                    for word in re.findall(r"[a-z0-9_.-]{4,}", requirement_text)
                    if word not in stopwords and not word.startswith("/app/")
                )
            )[:6]
            if keywords:
                questions.append(
                    {
                        "question": "请概括核心目标和至少两个关键约束。",
                        "expect": keywords,
                        "min_matches": min(2, len(keywords)),
                        "hint": "请重新阅读目标、输入、输出及限制条件后再开始。",
                    }
                )
        self._active_comprehension_questions = questions
        if not questions:
            return ""
        lines = [
            "在开始执行任务之前，请先用你自己的话回答以下几个问题，"
            "以确认你对任务的理解。然后才开始执行。",
            "你仍然必须使用系统要求的结构化 JSON 响应格式。请把编号回答写入 "
            "JSON 的 `analysis` 字段；不要返回 JSON 之外的自然语言。",
            "你可以在同一个 JSON 响应中给出合法的 `commands`，也可以暂时使用空列表。",
            "",
        ]
        for i, q in enumerate(questions, 1):
            lines.append(f"Q{i}. {q['question']}")
        lines.append("")
        lines.append("（这只用于确认理解，不会影响最终评分。）")
        return "\n".join(lines)

    def _check_comprehension(
        self, response: str, terminal_output: str
    ) -> tuple[list[dict[str, Any]], str]:
        """检查 agent 的回答是否符合预期的任务理解。

        对每个问题，检查 agent 的回答（response 全文 + 终端输出）中
        是否出现任一预期关键词。未通过的问题即为被误解/遗漏的约束。

        Returns:
            (failed_items, feedback_text)
            failed_items: 未通过的问题列表（含 question/hint）
            feedback_text: 若存在误解，注入的纠正提示文本（空串表示理解正确）
        """
        questions = self._active_comprehension_questions
        if not questions:
            return [], ""

        combined = (response or "") + "\n" + (terminal_output or "")
        combined_lower = combined.lower()

        failed: list[dict[str, Any]] = []
        for q in questions:
            expect = q.get("expect", [])
            match_count = sum(
                bool(re.search(re.escape(str(exp).lower()), combined_lower))
                for exp in expect
            )
            passed = match_count >= int(q.get("min_matches", 1))
            if not passed:
                failed.append(q)

        if not failed:
            return [], ""

        # 构造纠正提示：只指出被误解的约束，不给答案
        lines = [
            "\n\n[Task Understanding Check] 根据你的回答，你似乎对任务的"
            "以下关键约束理解有误或遗漏。请重新阅读任务描述并修正你的理解："
        ]
        for q in failed:
            lines.append(f"- {q['hint']}")
        lines.append("请重新审视任务，然后再继续。")
        feedback_text = "\n".join(lines)

        self._trajectory_records.append(
            {
                "episode": self._comprehension_episode,
                "intervention_type": "comprehension_check",
                "kind": "misunderstanding_detected",
                "failed_questions": [q["question"] for q in failed],
                "feedback": feedback_text,
            }
        )
        return failed, feedback_text

    # ──────────────────────────────────────────────
    # 重写 _run_agent_loop — 注入过程引导
    # ──────────────────────────────────────────────

    def _run_agent_loop(
        self,
        initial_prompt: str,
        session: TmuxSession,
        chat: Chat,
        logging_dir: Path | None = None,
        original_instruction: str = "",
    ) -> None:
        """重写主循环，在关键点注入过程引导。"""
        prompt = initial_prompt
        replay_cutoff = self._replay_until_episode

        try:
            for episode in itertools.count():
                if episode >= self._max_episodes:
                    break
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
                    # ── 前置注入 ──
                    if (
                        self._inject_before_episode >= 0
                        and episode == self._inject_before_episode
                        and self._intervention_mode != "none"
                        and self._intervention_payload
                    ):
                        self._logger.info(
                            f"[前置注入] Episode {episode}: 在 LLM query 之前注入干预"
                        )
                        from hermes_agent.replay_support import (
                            apply_message_intervention,
                        )

                        apply_message_intervention(
                            chat._messages,
                            self._intervention_mode,
                            self._intervention_payload,
                        )

                    # ── 时刻表干预 ──
                    self._apply_schedule_interventions(episode, chat)

                    # ── 首个实时 episode：仅在文档真实存在时提示 ──
                    if (
                        self._knowledge_file_exists(session)
                        and not self._knowledge_hint_sent
                    ):
                        prompt = (
                            f"{self._maybe_inject_knowledge_hint(episode, '', '')}"
                            f"\n\n{prompt}"
                        )

                    # ── ★ 任务理解校验：Ep0 向 agent 提问关键约束 ──
                    if (
                        not replay_mode
                        and self._comprehension_enabled
                        and not self._comprehension_sent
                    ):
                        comp_prompt = self._build_comprehension_prompt(
                            original_instruction
                        )
                        if comp_prompt:
                            # 把问题放在当前 prompt 最前面，要求先回答再执行
                            prompt = f"{comp_prompt}\n\n{prompt}"
                            self._comprehension_sent = True
                            self._comprehension_episode = episode
                            self._logger.info(
                                f"[理解校验] Episode {episode}: 注入 "
                                f"{len(self._active_comprehension_questions)} 个理解问题"
                            )
                            self._trajectory_records.append(
                                {
                                    "episode": episode,
                                    "intervention_type": "comprehension_check",
                                    "kind": "questions_sent",
                                    "questions": comp_prompt,
                                }
                            )

                    # ── LLM 交互 ──
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

                    # ── 强制命令 ──
                    if self._pending_force_commands:
                        self._logger.info(
                            f"[强制命令] Episode {episode}: 执行 {len(self._pending_force_commands)} 条强制命令"
                        )
                        from hermes_agent.terminus import Command

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

                # ── 解析错误处理 ──
                if feedback and "ERROR:" in feedback:
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

                # ── 执行命令 ──
                _, terminal_output = self._execute_commands(commands, session)

                # 每轮都从容器验证声明的输出产物，而不是等待最终测试。
                if not replay_mode and self._ablation_config.runtime_verification:
                    self._has_output_file = self._check_output_file(
                        terminal_output, session, original_instruction
                    )

                # 理解回答必须在接受完成声明之前通过机器检查。
                comprehension_feedback = ""
                if (
                    not replay_mode
                    and self._comprehension_enabled
                    and self._comprehension_sent
                    and not self._comprehension_checked
                ):
                    _, comprehension_feedback = self._check_comprehension(
                        response, terminal_output
                    )
                    self._comprehension_checked = True
                    if comprehension_feedback:
                        self._logger.info(
                            f"[理解校验] Episode {episode}: 检测到任务误解"
                        )

                # ── Episode 快照 ──
                if self._enable_episode_snapshots and not replay_mode:
                    self._capture_episode_snapshot(
                        episode, commands, terminal_output, session
                    )

                # ── 分析循环检测（覆盖：修复 cat > heredoc 误判为分析命令） ──
                if not replay_mode:
                    # 使用 GuidedInterventionAgent 的改进版检测
                    forced = self._guided_check_analysis_loop(
                        commands, episode, session, chat
                    )
                    if forced:
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

                # ── 命令重复检测 ──
                if not replay_mode:
                    self._check_command_repetition(commands, episode, chat)

                # ── 条件触发器 ──
                if not replay_mode:
                    self._check_trigger_interventions(episode, terminal_output, chat)

                # ── 定时保存快照 ──
                if not replay_mode and episode % 3 == 0:
                    self._save_trajectory_snapshot()

                # ── 任务完成检查 ──
                if is_task_complete:
                    if comprehension_feedback:
                        self._pending_completion = False
                        prompt = comprehension_feedback
                        self._trajectory_records.append(
                            {
                                "episode": episode,
                                "task_complete": False,
                                "completion_rejected": True,
                                "reason": "comprehension_check_failed",
                            }
                        )
                        continue
                    if (
                        self._artifact_requirement_detected
                        and not self._has_output_file
                    ):
                        self._pending_completion = False
                        prompt = (
                            "Completion was rejected by the runtime verifier: one or "
                            "more declared output artifacts are missing or empty. "
                            "Create and validate every required artifact before trying "
                            "again.\n\n"
                            f"{self._limit_output_length(terminal_output)}"
                        )
                        self._trajectory_records.append(
                            {
                                "episode": episode,
                                "task_complete": False,
                                "completion_rejected": True,
                            }
                        )
                        continue
                    if self._pending_completion:
                        self._trajectory_records.append(
                            {"episode": episode, "task_complete": True}
                        )
                        break
                    self._pending_completion = True
                    prompt = self._get_completion_confirmation_message(terminal_output)
                    self._trajectory_records.append(
                        {
                            "episode": episode,
                            "task_complete": False,
                            "pending_completion": True,
                        }
                    )
                    continue

                self._pending_completion = False

                # ── ★ 核心改进：过程引导 ──
                extra_feedback = ""
                if (
                    not replay_mode
                    and self._enable_process_guidance
                    and self._guidance_engine
                ):
                    # 分析命令文本
                    cmd_texts = [
                        c.keystrokes.strip()
                        for c in (commands or [])
                        if c.keystrokes.strip()
                    ]

                    # 检查是否在分析循环中
                    is_loop = self._analysis_command_count >= 2

                    # 调用过程引导引擎
                    guidance = self._guidance_engine.process_episode(
                        episode=episode,
                        commands=cmd_texts,
                        terminal_output=terminal_output,
                        total_episodes=self._max_episodes,
                        is_analysis_loop=is_loop,
                        has_output_file=self._has_output_file,
                        is_productive=any(
                            self._is_productive_command(text) for text in cmd_texts
                        ),
                        agent_response=response,
                    )
                    extra_feedback = f"\n\n{guidance}"

                    # 记录引导到轨迹
                    self._trajectory_records.append(
                        {
                            "episode": episode,
                            "intervention_type": "process_guidance",
                            "guidance": guidance,
                            "diagnostics": self._guidance_engine.last_diagnostics,
                        }
                    )

                    # 检查是否需要自适应延长
                    manager = self._guidance_engine.episode_manager
                    if (
                        self._ablation_config.adaptive_episodes
                        and manager.should_extend(episode, self._max_episodes)
                    ):
                        new_max = manager.extend_limit(episode, self._max_episodes)
                        self._logger.info(
                            f"[自适应延长] Episode {episode}: 上限从 {self._max_episodes} 延长至 {new_max}"
                        )
                        self._max_episodes = new_max
                        extra_feedback += (
                            f"\n\n[Adaptive Budget] Productive progress was detected; "
                            f"the episode limit is now {new_max}."
                        )

                    if (
                        TernaryFeedback.is_irrecoverable(
                            self._guidance_engine.last_feedback_level
                        )
                        and self._trajectory_reset_count < self._max_trajectory_resets
                    ):
                        self._trajectory_reset_count += 1
                        chat._messages = [
                            message
                            for message in chat._messages
                            if message.get("role") == "system"
                        ]
                        extra_feedback = (
                            "\n\n[Trajectory Reset] The previous approach became "
                            "irrecoverable. Re-ground on the original task and choose a "
                            "different method. Existing files remain available.\n\n"
                            f"{initial_prompt}\n\n{guidance}"
                        )
                        self._trajectory_records.append(
                            {
                                "episode": episode,
                                "intervention_type": "trajectory_reset",
                                "feedback_level": self._guidance_engine.last_feedback_level,
                            }
                        )

                # ── ★ 知识提示：AI 缺少领域知识时提示阅读知识文档 ──
                knowledge_hint = ""
                if (
                    not replay_mode
                    and self._knowledge_file_exists(session)
                    and self._knowledge_hint_sent
                ):
                    knowledge_hint = self._maybe_inject_knowledge_hint(
                        episode, response, terminal_output
                    )
                    if knowledge_hint:
                        self._logger.info(
                            f"[知识提示] Episode {episode}: 注入知识提示（共 {self._knowledge_hint_count} 次）"
                        )

                # ── 构建下一轮 prompt ──
                if feedback and "WARNINGS:" in feedback:
                    prompt = (
                        f"Previous response had warnings:\n{feedback}\n\n"
                        f"{self._limit_output_length(terminal_output)}"
                        f"{extra_feedback}"
                        f"{knowledge_hint}"
                        f"{comprehension_feedback}"
                    )
                else:
                    prompt = (
                        f"{self._limit_output_length(terminal_output)}"
                        f"{extra_feedback}"
                        f"{knowledge_hint}"
                        f"{comprehension_feedback}"
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
            if self._trajectory_records:
                first_record = self._trajectory_records[0]
                if first_record.get("record_type") == "run_config":
                    first_record["effective_episode_limit"] = self._max_episodes
                    if self._guidance_engine:
                        manager = self._guidance_engine.episode_manager
                        first_record["extensions_granted"] = manager.extensions_granted

            # ── 快照落盘 ──
            if self._enable_episode_snapshots:
                self._save_episode_snapshots()

            # ── 轨迹落盘 ──
            if not self._trajectory_records:
                print("\n⚠️ [GuidedIntervention] 轨迹记录为空。")
            else:
                output_path = self._trajectory_output_path or default_artifact_path(
                    "guided-intervention-trajectory.json"
                )
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(
                        json.dumps(
                            self._trajectory_records, indent=2, ensure_ascii=False
                        ),
                        encoding="utf-8",
                    )
                    print(f"[GuidedIntervention] 轨迹已保存至: {output_path}")
                except Exception as e:
                    self._logger.warning("Failed to save trajectory: %s", e)

    # ──────────────────────────────────────────────
    # 改进的分析循环检测
    # ──────────────────────────────────────────────

    def _is_productive_command(self, cmd_text: str) -> bool:
        """判断命令是否属于生产性操作（写文件、编译、运行脚本等）。"""
        cmd = cmd_text.strip().lower()

        # 通用写入和编辑操作。
        if re.search(r"(^|[^2])>{1,2}\s*[^&]", cmd):
            return True
        if cmd.startswith(
            (
                "tee ",
                "touch ",
                "sed -i",
                "perl -pi",
                "patch ",
                "git apply ",
                "chmod ",
                "chown ",
            )
        ):
            return True

        # Python 写入或脚本执行；纯读取的一次性探针不算生产性进展。
        if cmd.startswith("python3") or cmd.startswith("python "):
            write_signals = (
                ".write(",
                ".write_text(",
                ".write_bytes(",
                ".to_csv(",
                ".to_parquet(",
                "json.dump(",
                "pickle.dump(",
            )
            opens_for_write = re.search(r"open\s*\([^)]*,\s*['\"][wax+]", cmd)
            if opens_for_write or any(signal in cmd for signal in write_signals):
                return True
            read_signals = ("open(", ".read()", ".read_text(", "for line in")
            is_inline = " -c " in cmd or "<<" in cmd
            if is_inline and any(signal in cmd for signal in read_signals):
                return False
            return True

        # 测试执行
        if "run-tests" in cmd or "pytest" in cmd:
            return True

        # 文件复制/移动
        if cmd.startswith(("cp ", "mv ", "install ", "make ", "cmake ", "docker ")):
            return True

        return False

    def _is_analysis_command_fixed(self, cmd_text: str) -> bool:
        """改进版的分析命令检测 — 避免将 cat > heredoc 误判为分析。"""
        cmd = cmd_text.strip().lower()

        # 先检查是否是生产性命令
        if self._is_productive_command(cmd_text):
            return False

        # 再检查分析命令模式
        analysis_patterns = [
            r"^ls[ \n]",
            r"^cat[ \n]",
            r"^which[ \n]",
            r"^head[ \n]",
            r"^tail[ \n]",
            r"^find[ \n]",
            r"^pwd[ \n]",
            r"^env$",
            r"^print",
            r"^clear",
        ]
        for pat in analysis_patterns:
            if re.search(pat, cmd_text):
                return True

        # Python 只读脚本
        if cmd.startswith("python3") or cmd.startswith("python "):
            has_read = any(
                kw in cmd
                for kw in [
                    "open(",
                    ".read()",
                    ".read_text",
                    "for line in",
                ]
            )
            has_write = bool(re.search(r"open\s*\([^)]*,\s*['\"][wax+]", cmd)) or any(
                kw in cmd
                for kw in (
                    ".write(",
                    ".write_text(",
                    ".write_bytes(",
                    ".to_csv(",
                    ".to_parquet(",
                )
            )
            if has_read and not has_write:
                return True

        return False

    def _guided_check_analysis_loop(
        self,
        commands,
        episode: int,
        session,
        chat,
    ) -> bool:
        """改进版分析循环检测 — 修复 cat > heredoc 误报。"""
        cmd_texts = [
            c.keystrokes.strip() for c in (commands or []) if c.keystrokes.strip()
        ]
        if not cmd_texts:
            return False

        # 统计本轮中的分析类命令（使用修复版）
        analysis_count = sum(1 for t in cmd_texts if self._is_analysis_command_fixed(t))
        all_analysis = analysis_count == len(cmd_texts) and analysis_count > 0

        if episode == self._last_analysis_episode + 1:
            if all_analysis:
                self._analysis_command_count += 1
            else:
                self._analysis_command_count = 0
        else:
            self._analysis_command_count = 1 if all_analysis else 0

        self._last_analysis_episode = episode

        # 连续 4+ 个 episode 全为分析命令 → 截断（比父类更宽松，给更多空间）
        if self._analysis_command_count >= 4:
            self._logger.info(
                f"[改进分析循环检测] Episode {episode}: "
                f"连续 {self._analysis_command_count} 个 episode 仅执行分析命令 → "
                f"强制截断历史并注入紧急指令"
            )
            if chat is None:
                self._logger.warning("chat is None, cannot truncate history")
                self._analysis_command_count = 0
                return False

            current_screen = session.capture_pane(capture_entire=False)
            force_prompt = (
                "【强制指令】你已连续多个回合仅执行分析命令而未取得实质进展。\n"
                "立即终止所有分析。直接执行任务所需的关键命令。\n"
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

    # ──────────────────────────────────────────────
    # 名称
    # ──────────────────────────────────────────────

    @staticmethod
    def name() -> str:
        return "guided-intervention"
