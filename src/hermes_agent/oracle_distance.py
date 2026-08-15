# ruff: noqa: E501 -- Formulae and research diagnostics retain their exact text.

"""
OracleDistance — 稠密奖励信号：计算当前状态与 oracle 终态的距离。

核心思想：
  Agent 每走一步，计算 D = distance(current_state, oracle_final_state)
  注入 D 到 prompt 中，让 agent 感知自己离目标有多远。

距离公式（dna-assembly）：
  D = w1 * missing_primers + w2 * tm_deviation + w3 * overhang_errors + w4 * bsai_missing

  其中 w1..w4 是权重，归一化后 D ∈ [0, 1]
  0 = 完美匹配 oracle，1 = 完全偏离
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# ──────────────────────────────────────────────
# Tm 估算（不需要 oligotm）
# ──────────────────────────────────────────────


def estimate_tm(seq: str) -> float:
    """用 Nearest-Neighbor 简化公式估算引物 Tm。

    对于 15-45nt 的 DNA 引物，使用修正的 Wallace 规则：
      Tm ≈ 4*(G+C) + 2*(A+T)

    这比 oligotm 的 NN 算法粗糙，但足够做趋势判断。
    """
    seq = seq.upper().strip()
    if not seq:
        return 0.0
    gc = seq.count("G") + seq.count("C")
    at = seq.count("A") + seq.count("T")
    if gc + at == 0:
        return 0.0
    return 4.0 * gc + 2.0 * at


# ──────────────────────────────────────────────
# Oracle 状态定义
# ──────────────────────────────────────────────


@dataclass
class PrimerSpec:
    """单条引物的 oracle 规格。"""

    name: str  # 如 input_fwd
    annealing_region: str  # 退火段序列
    overhang: str  # 4bp overhang
    has_bsai_site: bool = True  # 是否包含 ggtctc
    clamp_bp: int = 6  # clamp 碱基数
    expected_tm_min: float = 58.0
    expected_tm_max: float = 72.0


@dataclass
class OverhangPair:
    """相邻片段的 overhang 互补对。"""

    left_fragment: str  # 左侧片段名
    right_fragment: str  # 右侧片段名
    left_overhang: str  # 左侧的右 overhang
    right_overhang: str  # 右侧的左 overhang
    # 要求: left_overhang == rc(right_overhang)


@dataclass
class OracleState:
    """Oracle 理想终态——从 solution.sh 预计算。"""

    # ── 文件规格 ──
    expected_files: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "/app/primers.fasta": {
                "lines": 16,  # 8 条引物 × 2 行（header + 序列）
                "min_lines": 2,
                "must_contain": ["ggtctc", "GGTCTC"],
                "format": ">name\n[acgt]+",
            },
        }
    )

    # ── 引物规格 ──
    primer_names: list[str] = field(
        default_factory=lambda: [
            "input_fwd",
            "input_rev",
            "egfp_fwd",
            "egfp_rev",
            "flag_fwd",
            "flag_rev",
            "snap_fwd",
            "snap_rev",
        ]
    )

    # ── 质量要求 ──
    tm_min: float = 58.0
    tm_max: float = 72.0
    tm_pair_diff_max: float = 5.0
    annealing_min_len: int = 15
    annealing_max_len: int = 45
    overhang_len: int = 4
    bsai_site: str = "ggtctc"
    clamp_min: int = 1

    # ── Overhang 互补关系（从 solution.sh 预计算） ──
    # 片段顺序: input → egfp → flag → snap → input(闭环)
    # overhang[左] == rc(overhang[右相邻])
    expected_overhang_pairs: list[OverhangPair] = field(
        default_factory=lambda: [
            OverhangPair("egfp", "input", "", ""),  # egfp.right == rc(input.left)
            OverhangPair("flag", "egfp", "", ""),  # flag.right == rc(egfp.left)
            OverhangPair("snap", "flag", "", ""),  # snap.right == rc(flag.left)
            OverhangPair(
                "input", "snap", "", ""
            ),  # input.right == rc(snap.left) - 闭环
        ]
    )

    # ── 权重（距离公式用） ──
    # 包含中间进度信号（不依赖 primers.fasta）
    weights: dict[str, float] = field(
        default_factory=lambda: {
            "tools_installed": 0.08,  # 工具安装进度
            "sequences_read": 0.05,  # 序列文件已读取
            "needle_run": 0.07,  # needle 比对已执行
            "attempted_write": 0.05,  # 尝试写 primers.fasta
            "missing_primers": 0.25,  # 引物数量
            "bsai_missing": 0.20,  # BsaI 位点
            "overhang_errors": 0.15,  # Overhang 格式
            "clamp_missing": 0.10,  # Clamp 碱基
            "tm_deviation": 0.05,  # Tm 估算
        }
    )

    def __post_init__(self):
        self._primers_fasta_content: str | None = None


# ──────────────────────────────────────────────
# 距离计算
# ──────────────────────────────────────────────


def rc(seq: str) -> str:
    """反向互补。"""
    return seq.translate(str.maketrans("acgtACGT", "tgcaTGCA"))[::-1]


def parse_primers_fasta(content: str) -> dict[str, str]:
    """解析 FASTA 格式的引物文件。

    Args:
        content: FASTA 文件内容

    Returns:
        dict[str, str]: primer_name -> sequence
    """
    primers: dict[str, str] = {}
    current_name = ""
    current_seq = ""

    for line in content.strip().split("\n"):
        line = line.strip()
        if line.startswith(">"):
            if current_name and current_seq:
                primers[current_name] = current_seq
            current_name = line[1:].strip()
            current_seq = ""
        elif line:
            current_seq += line

    if current_name and current_seq:
        primers[current_name] = current_seq

    return primers


def compute_distance(
    terminal_output: str,
    oracle: OracleState,
    primer_content: str | None = None,
) -> dict[str, Any]:
    """计算当前状态与 oracle 终态的距离。

    Args:
        terminal_output: 当前 terminal_output（用于检测文件存在性）
        oracle: OracleState 实例
        primer_content: primers.fasta 的内容（如果已存在）

    Returns:
        dict:
          - score: float, 0.0 = 完美, 1.0 = 完全偏离
          - components: dict[str, float], 各分量得分
          - details: list[str], 详细说明
          - summary: str, 一句话摘要（可直接注入 prompt）
    """
    components: dict[str, float] = {}
    details: list[str] = []
    total_weight = sum(oracle.weights.values())
    to_lower = terminal_output.lower()

    # ── 0a. 工具安装进度 ──
    has_emboss = "emboss" in to_lower
    has_primer3 = "primer3" in to_lower
    has_apt = "apt-get install" in to_lower
    if has_emboss and has_primer3:
        components["tools_installed"] = 0.0
    elif has_emboss or has_primer3:
        components["tools_installed"] = 0.5
        details.append("工具安装进行中（已安装 emboss 或 primer3 之一）")
    elif has_apt:
        components["tools_installed"] = 0.3
        details.append("正在安装工具（apt-get 已执行）")
    else:
        components["tools_installed"] = 0.8
        details.append("尚未开始安装工具（emboss + primer3 需要）")

    # ── 0b. 序列读取 ──
    if "sequences.fasta" in to_lower and (
        "cat" in to_lower or "read" in to_lower or ">" in terminal_output
    ):
        components["sequences_read"] = 0.0
    else:
        components["sequences_read"] = 0.5  # 部分读取
        if "sequences.fasta" not in to_lower:
            components["sequences_read"] = 1.0

    # ── 0c. Needle 比对 ──
    if (
        "needle" in to_lower
        and "alignment" in to_lower
        or ("needle" in to_lower and "output" in to_lower)
    ):
        components["needle_run"] = 0.0
        if "needle_run" not in [d for d in details if "needle" in d]:
            details.append("needle 比对已执行")
    elif "needle" in to_lower:
        components["needle_run"] = 0.4
    else:
        components["needle_run"] = 1.0

    # ── 0d. 尝试写入 primers.fasta ──
    has_write_attempt = "primers.fasta" in to_lower and (
        "write" in to_lower or ">" in terminal_output or "echo" in to_lower
    )
    components["attempted_write"] = 0.0 if has_write_attempt else 1.0
    if has_write_attempt:
        details.append("已尝试写入 primers.fasta")

    # ── 1. 引物缺失检查 ──
    if primer_content and primer_content.strip():
        primers = parse_primers_fasta(primer_content)
        missing = [n for n in oracle.primer_names if n not in primers]
        missing_ratio = len(missing) / len(oracle.primer_names)
        components["missing_primers"] = missing_ratio
        if missing:
            details.append(f"缺少引物: {', '.join(missing)}")
        else:
            details.append("8 条引物齐全")
    else:
        # 从 terminal_output 推断是否尝试过写文件
        has_attempt = "primers.fasta" in terminal_output.lower()
        components["missing_primers"] = 1.0 if not has_attempt else 0.8
        details.append(
            "primers.fasta 尚未创建"
            if not has_attempt
            else "primers.fasta 存在但内容为空"
        )

    # ── 2. BsaI 位点检查 ──
    if primer_content and primer_content.strip():
        primers = parse_primers_fasta(primer_content)
        bsai_site = oracle.bsai_site.lower()
        has_bsai = sum(1 for s in primers.values() if bsai_site in s.lower())
        expected = len(oracle.primer_names)
        bsai_ratio = 1.0 - (has_bsai / expected) if expected > 0 else 1.0
        components["bsai_missing"] = bsai_ratio
        if has_bsai < expected:
            details.append(f"{expected - has_bsai}/{expected} 条引物缺少 BsaI 位点")
        else:
            details.append("全部引物包含 BsaI 位点 (GGTCTC)")
    else:
        components["bsai_missing"] = 1.0

    # ── 3. Clamp 碱基检查 ──
    if primer_content and primer_content.strip():
        primers = parse_primers_fasta(primer_content)
        bsai_lower = oracle.bsai_site.lower()
        no_clamp = 0
        for name, seq in primers.items():
            pos = seq.lower().find(bsai_lower)
            if pos == 0 or pos < 0:
                no_clamp += 1
        clamp_ratio = (
            no_clamp / len(oracle.primer_names) if oracle.primer_names else 1.0
        )
        components["clamp_missing"] = clamp_ratio
        if no_clamp > 0:
            details.append(f"{no_clamp} 条引物在 GGTCTC 前缺少 clamp 保护碱基")
        else:
            details.append("全部引物有 clamp 保护碱基")
    else:
        components["clamp_missing"] = 1.0

    # ── 4. Overhang 检查（只做格式存在性检查） ──
    if primer_content and primer_content.strip():
        primers = parse_primers_fasta(primer_content)
        bsai_lower = oracle.bsai_site.lower()
        overhang_ok = 0
        for name, seq in primers.items():
            pos = seq.lower().find(bsai_lower)
            if pos >= 0:
                after_site = seq[pos + len(bsai_lower) :]
                if len(after_site) >= oracle.overhang_len + oracle.annealing_min_len:
                    overhang_ok += 1
        oh_ratio = (
            1.0 - (overhang_ok / len(oracle.primer_names))
            if oracle.primer_names
            else 1.0
        )
        components["overhang_errors"] = oh_ratio
        if overhang_ok < len(oracle.primer_names):
            details.append(
                f"{len(oracle.primer_names) - overhang_ok} 条引物 overhang/退火区格式不正确"
            )
    else:
        components["overhang_errors"] = 1.0

    # ── 5. Tm 估算检查 ──
    if primer_content and primer_content.strip():
        primers = parse_primers_fasta(primer_content)
        bsai_lower = oracle.bsai_site.lower()
        tm_out_of_range = 0
        for name, seq in primers.items():
            pos = seq.lower().find(bsai_lower)
            if pos >= 0:
                annealing = seq[pos + len(bsai_lower) + oracle.overhang_len :]
                if len(annealing) >= 10:
                    tm = estimate_tm(annealing)
                    if tm < oracle.tm_min or tm > oracle.tm_max:
                        tm_out_of_range += 1
        tm_ratio = (
            tm_out_of_range / len(oracle.primer_names) if oracle.primer_names else 1.0
        )
        components["tm_deviation"] = tm_ratio
    else:
        components["tm_deviation"] = 1.0

    # ── 总分 ──
    weighted_score = (
        sum(oracle.weights.get(k, 0.0) * v for k, v in components.items())
        / total_weight
        if total_weight > 0
        else 1.0
    )

    weighted_score = max(0.0, min(1.0, weighted_score))

    # ── 摘要 ──
    if weighted_score == 0.0:
        summary = "✅ 距离目标: 0.00 — 完美匹配 oracle"
    elif weighted_score < 0.2:
        summary = f"✅ 距离目标: {weighted_score:.2f} — 接近完成"
    elif weighted_score < 0.4:
        summary = f"📗 距离目标: {weighted_score:.2f} — 已有引物，需要修复"
    elif weighted_score < 0.6:
        summary = f"📙 距离目标: {weighted_score:.2f} — 已有进展，仍在早期"
    elif weighted_score < 0.8:
        summary = f"📘 距离目标: {weighted_score:.2f} — 工具/序列准备中"
    else:
        summary = f"🔴 距离目标: {weighted_score:.2f} — 尚未开始 / 严重偏离"

    return {
        "score": weighted_score,
        "components": components,
        "details": details,
        "summary": summary,
        "has_primers_file": primer_content is not None and primer_content.strip() != "",
        "total_primers": len(parse_primers_fasta(primer_content))
        if primer_content and primer_content.strip()
        else 0,
    }


def format_distance_for_prompt(
    distance_result: dict[str, Any],
    previous_score: float | None = None,
) -> str:
    """将距离结果格式化为可注入 prompt 的文本。"""
    score = distance_result["score"]
    details = distance_result["details"]

    # 趋势
    trend = ""
    if previous_score is not None:
        delta = previous_score - score
        if delta > 0.05:
            trend = f" (比上轮进步 {delta:.2f}) 🟢"
        elif delta < -0.05:
            trend = f" (比上轮退步 {abs(delta):.2f}) 🔴"
        else:
            trend = " (与上轮持平)"

    lines = [
        distance_result["summary"] + trend,
    ]

    if details:
        lines.append("  详情:")
        for d in details[:5]:  # 最多 5 条
            lines.append(f"    • {d}")

    return "\n".join(lines)
