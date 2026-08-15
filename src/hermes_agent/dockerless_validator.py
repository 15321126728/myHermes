"""
DockerlessValidator — 不执行代码的静态引物验证器。

代替「构建 Docker → 跑 pytest」的慢循环，在 agent 每次写入
primers.fasta 后立即做毫秒级的静态分析，反馈格式/结构问题。

验证维度：
  1. FASTA 格式正确性
  2. 引物数量和命名
  3. BsaI 位点存在性
  4. Clamp 碱基
  5. Overhang 长度与互补性（静态规则）
  6. Tm 估算（Wallace 规则）
  7. 序列合法性（仅含 ATCG）
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def rc(seq: str) -> str:
    """反向互补。"""
    return seq.translate(str.maketrans("acgtACGT", "tgcaTGCA"))[::-1]


def estimate_tm_wallace(seq: str) -> float:
    """Wallace 规则估算 Tm: 4*(G+C) + 2*(A+T)"""
    seq = seq.upper().strip()
    if not seq:
        return 0.0
    gc = seq.count("G") + seq.count("C")
    at = seq.count("A") + seq.count("T")
    if gc + at == 0:
        return 0.0
    return 4.0 * gc + 2.0 * at


@dataclass
class ValidationResult:
    """验证结果。"""

    passed: bool = False
    score: float = 0.0  # 0-100
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_prompt(self) -> str:
        """格式化为可注入 prompt 的反馈。"""
        if self.passed:
            return f"✅ Dockerless 验证通过 (得分: {self.score:.0f}/100)"

        lines = [f"📋 Dockerless 验证结果 (得分: {self.score:.0f}/100)"]
        if self.errors:
            lines.append("  ❌ 错误:")
            for e in self.errors[:5]:
                lines.append(f"    • {e}")
        if self.warnings:
            lines.append("  ⚠️  警告:")
            for w in self.warnings[:3]:
                lines.append(f"    • {w}")
        return "\n".join(lines)


def parse_fasta(content: str) -> dict[str, str]:
    """解析 FASTA 内容为 dict[name -> sequence]。"""
    primers: dict[str, str] = {}
    current_name = ""
    current_seq = ""

    for line in content.strip().split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            if current_name and current_seq:
                primers[current_name] = current_seq
            current_name = line[1:].strip()
            current_seq = ""
        else:
            current_seq += line

    if current_name and current_seq:
        primers[current_name] = current_seq

    return primers


DEFAULT_EXPECTED_PRIMERS = [
    "input_fwd",
    "input_rev",
    "egfp_fwd",
    "egfp_rev",
    "flag_fwd",
    "flag_rev",
    "snap_fwd",
    "snap_rev",
]


def validate_primers(
    content: str,
    expected_primers: list[str] | None = None,
) -> ValidationResult:
    """对 primers.fasta 做完整的静态验证。

    Args:
        content: primers.fasta 的文本内容
        expected_primers: 期望的引物名称列表

    Returns:
        ValidationResult: 验证结果
    """
    if expected_primers is None:
        expected_primers = DEFAULT_EXPECTED_PRIMERS

    result = ValidationResult()

    if not content or not content.strip():
        result.errors.append("primers.fasta 为空")
        result.score = 0
        return result

    primers = parse_fasta(content)

    # ── 1. 基本格式检查 ──
    if not primers:
        result.errors.append("无法解析 FASTA 格式：未找到任何 >header 行")
        result.score = 5
        return result

    lines = [line for line in content.strip().split("\n") if line.strip()]
    header_lines = sum(1 for line in lines if line.startswith(">"))
    seq_lines = len(lines) - header_lines

    if header_lines != seq_lines:
        result.warnings.append(
            f"header 行数 ({header_lines}) 与序列行数 ({seq_lines}) 不相等"
        )
        result.details["header_lines"] = header_lines
        result.details["seq_lines"] = seq_lines

    # ── 2. 引物数量与命名 ──
    result.details["total_primers"] = len(primers)
    result.details["primer_names"] = list(primers.keys())

    for name in primers:
        if name not in expected_primers:
            result.warnings.append(f"未知引物名称: {name}")

    missing = [n for n in expected_primers if n not in primers]
    extra = [n for n in primers if n not in expected_primers]

    if missing:
        result.errors.append(
            f"缺少 {len(missing)}/{len(expected_primers)} 条引物: {', '.join(missing)}"
        )
    if extra:
        result.warnings.append(f"多余的引物: {', '.join(extra)}")

    # ── 3. 序列合法性 ──
    for name, seq in primers.items():
        seq_upper = seq.upper()
        invalid_chars = set(seq_upper) - {"A", "T", "C", "G"}
        if invalid_chars:
            result.errors.append(f"{name}: 含非法字符 {invalid_chars}")

    # ── 4. BsaI 位点检查 ──
    bsai = "GGTCTC"
    bsai_lower = bsai.lower()
    has_bsai_count = 0
    for name, seq in primers.items():
        seq_lower = seq.lower()
        if bsai_lower in seq_lower:
            has_bsai_count += 1
            pos = seq_lower.find(bsai_lower)
            result.details[f"{name}:bsai_pos"] = pos
        else:
            result.errors.append(f"{name}: 缺少 BsaI 位点 {bsai}")

    result.details["primers_with_bsai"] = has_bsai_count

    # ── 5. Clamp 碱基检查 ──
    no_clamp_count = 0
    for name, seq in primers.items():
        seq_lower = seq.lower()
        pos = seq_lower.find(bsai_lower)
        if pos >= 0:
            if pos == 0:
                no_clamp_count += 1
                result.errors.append(
                    f"{name}: GGTCTC 前缺少 clamp 保护碱基 (GGTCTC 在序列开头)"
                )
            elif pos > 0:
                clamp = seq[:pos]
                result.details[f"{name}:clamp"] = clamp

    # ── 6. Overhang 提取和检查 ──
    overhang_details: dict[str, str] = {}
    for name, seq in primers.items():
        seq_lower = seq.lower()
        pos = seq_lower.find(bsai_lower)
        if pos >= 0:
            after_bsai = seq[pos + len(bsai) :]
            if len(after_bsai) >= 4:
                overhang = after_bsai[:4]
                annealing = after_bsai[4:]
                overhang_details[name] = overhang
                result.details[f"{name}:overhang"] = overhang
                result.details[f"{name}:annealing_len"] = len(annealing)
            else:
                result.errors.append(
                    f"{name}: BsaI 位点后序列过短 ({len(after_bsai)}nt, "
                    "需要至少 4bp overhang + 退火区)"
                )

    # ── 7. 退火区长度检查 ──
    annealing_len_errors = 0
    for name, seq in primers.items():
        seq_lower = seq.lower()
        pos = seq_lower.find(bsai_lower)
        if pos >= 0:
            after_bsai = seq[pos + len(bsai) :]
            if len(after_bsai) >= 4:
                annealing = after_bsai[4:]
                alen = len(annealing)
                if alen < 15:
                    result.errors.append(f"{name}: 退火区过短 ({alen}nt, 需要 15-45)")
                    annealing_len_errors += 1
                elif alen > 45:
                    result.warnings.append(f"{name}: 退火区过长 ({alen}nt, 建议 ≤45)")
                    annealing_len_errors += 1

    # ── 8. Overhang 互补性检查（基于已知的组装顺序） ──
    # 组装顺序: input → egfp → flag → snap → input(闭环)
    # overhang 互补: 左片段的右端 == rc(右片段的左端)
    fragment_order = ["input", "egfp", "flag", "snap"]
    oh_errors = 0
    for i in range(len(fragment_order)):
        left = fragment_order[i]
        right = fragment_order[(i + 1) % len(fragment_order)]
        left_rev_name = f"{left}_rev"
        right_fwd_name = f"{right}_fwd"

        left_oh = overhang_details.get(left_rev_name, "")
        right_oh = overhang_details.get(right_fwd_name, "")

        if left_oh and right_oh:
            expected_right_oh = rc(left_oh)
            if right_oh.lower() != expected_right_oh.lower():
                oh_errors += 1
                result.errors.append(
                    f"Overhang 不匹配: {left_rev_name} 的 overhang ({left_oh}) "
                    f"的 RC 应为 {right_fwd_name} 的 overhang, "
                    f"实际为 {right_oh}, 期望 {expected_right_oh}"
                )
            else:
                result.details[f"overhang_pair:{left}->{right}"] = "OK"

    # ── 9. Tm 估算 ──
    tm_errors = 0
    for name, seq in primers.items():
        seq_lower = seq.lower()
        pos = seq_lower.find(bsai_lower)
        if pos >= 0:
            after_bsai = seq[pos + len(bsai) :]
            if len(after_bsai) >= 4:
                annealing = after_bsai[4:]
                if len(annealing) >= 10:
                    tm = estimate_tm_wallace(annealing)
                    result.details[f"{name}:tm_est"] = round(tm, 1)
                    if tm < 58:
                        result.warnings.append(
                            f"{name}: Tm 估算偏低 ({tm:.0f}°C, 目标 58-72)"
                        )
                        tm_errors += 1
                    elif tm > 72:
                        result.warnings.append(
                            f"{name}: Tm 估算偏高 ({tm:.0f}°C, 目标 58-72)"
                        )
                        tm_errors += 1

    # ── 10. 配对 Tm 差检查 ──
    pairs = [
        ("input_fwd", "input_rev"),
        ("egfp_fwd", "egfp_rev"),
        ("flag_fwd", "flag_rev"),
        ("snap_fwd", "snap_rev"),
    ]
    for fwd_name, rev_name in pairs:
        fwd_tm = result.details.get(f"{fwd_name}:tm_est")
        rev_tm = result.details.get(f"{rev_name}:tm_est")
        if fwd_tm and rev_tm:
            diff = abs(fwd_tm - rev_tm)
            result.details[f"tm_diff:{fwd_name}/{rev_name}"] = round(diff, 1)
            if diff > 5:
                result.warnings.append(
                    f"{fwd_name}/{rev_name} Tm 差 {diff:.0f}°C (>5°C)"
                )

    # ── 最终评分 ──
    total_checks = 8
    failures = len(result.errors)
    score = max(0, 100 - (failures * 100 / total_checks))

    # 如果有致命缺陷（无引物、无 BsaI、格式错误），分数打折
    if not primers:
        score = 0
    elif has_bsai_count == 0:
        score = min(score, 20)
    elif len(missing) >= 4:
        score = min(score, 30)
    elif no_clamp_count > 0:
        score = min(score, 80)

    result.score = round(score, 1)
    result.passed = score >= 80 and len(result.errors) == 0

    return result


def format_validation_report(result: ValidationResult) -> str:
    """将验证结果格式化为结构化报告。"""
    lines = [
        "=" * 50,
        "Dockerless 验证报告",
        "=" * 50,
        f"得分: {result.score:.0f}/100  {'✅ 通过' if result.passed else '❌ 未通过'}",
        f"引物总数: {result.details.get('total_primers', 'N/A')}",
        f"含 BsaI 位点: {result.details.get('primers_with_bsai', 0)}",
        "",
    ]

    if result.errors:
        lines.append(f"错误 ({len(result.errors)}):")
        for e in result.errors:
            lines.append(f"  ❌ {e}")

    if result.warnings:
        lines.append(f"警告 ({len(result.warnings)}):")
        for w in result.warnings:
            lines.append(f"  ⚠️  {w}")

    lines.append("")
    lines.append("Tm 估算 (Wallace 规则):")
    for name in DEFAULT_EXPECTED_PRIMERS:
        tm_key = f"{name}:tm_est"
        if tm_key in result.details:
            lines.append(f"  {name}: {result.details[tm_key]}°C")

    # Overhang 互补
    lines.append("")
    lines.append("Overhang 互补检查:")
    for name in DEFAULT_EXPECTED_PRIMERS:
        oh_key = f"{name}:overhang"
        if oh_key in result.details:
            annealing_len = result.details.get(f"{name}:annealing_len", "?")
            lines.append(
                f"  {name}: overhang={result.details[oh_key]}, 退火区={annealing_len}nt"
            )

    return "\n".join(lines)
