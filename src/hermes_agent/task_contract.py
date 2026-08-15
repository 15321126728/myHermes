from __future__ import annotations

import re
from dataclasses import dataclass

_ABS_PATH_RE = re.compile(r"(?<![\w.-])(/app/[A-Za-z0-9_./-]+)")
_TITLED_RE = re.compile(
    r"(?:titled|named|called)\s+[`'\"]?([A-Za-z0-9_.-]+)[`'\"]?",
    re.IGNORECASE,
)
_OUTPUT_FILENAME_RE = re.compile(
    r"(?:output(?:\s+file)?(?:\s+(?:is|must be|should be))?|"
    r"save(?:\s+as)?|write(?:\s+to)?|create|generate)\s*[:=]?\s*"
    r"[`'\"]?([A-Za-z0-9_.-]+\.[A-Za-z0-9]+)[`'\"]?",
    re.IGNORECASE,
)
_OUTPUT_LINE_RE = re.compile(
    r"\b(output|convert|create|generate|save|write|record|implementation|solution)\b",
    re.IGNORECASE,
)
_OPTIONAL_OUTPUT_RE = re.compile(r"\b(?:one|either)\b[^\n]{0,120}\bor\b", re.IGNORECASE)


@dataclass(frozen=True)
class TaskContract:
    """Small, answer-free contract extracted from the task instruction."""

    artifact_paths: tuple[str, ...]
    requirements: tuple[str, ...]
    output_paths: tuple[str, ...] = ()
    optional_output_groups: tuple[tuple[str, ...], ...] = ()

    @classmethod
    def from_instruction(cls, instruction: str) -> "TaskContract":
        paths: list[str] = []
        for match in _ABS_PATH_RE.findall(instruction):
            path = match.rstrip(".,;:)")
            if path not in paths:
                paths.append(path)

        for name in _TITLED_RE.findall(instruction):
            name = name.rstrip(".,;:)")
            if "." not in name:
                continue
            path = f"/app/{name}"
            if path not in paths:
                paths.append(path)
        for name in _OUTPUT_FILENAME_RE.findall(instruction):
            path = f"/app/{name.rstrip('.,;:')}"
            if path not in paths:
                paths.append(path)

        requirements: list[str] = []
        output_paths: list[str] = []
        first_goal_recorded = False
        for raw_line in instruction.splitlines():
            line = raw_line.strip().lstrip("-* ").strip()
            lower = line.lower()
            if not line:
                continue
            if not first_goal_recorded:
                requirements.append(line[:500])
                first_goal_recorded = True
            if len(line) > 260:
                continue
            if any(
                word in lower
                for word in ("must", "should", "output", "create", "record", "write")
            ) or line.startswith("/"):
                if line not in requirements:
                    requirements.append(line)
            if len(requirements) >= 10:
                break

        optional_groups: list[tuple[str, ...]] = []
        for raw_line in instruction.splitlines():
            for clause in re.split(r"(?<=[.!?])\s+", raw_line.strip()):
                if not _OUTPUT_LINE_RE.search(clause):
                    continue
                line_paths = [
                    match.rstrip(".,;:)") for match in _ABS_PATH_RE.findall(clause)
                ]
                for name in _TITLED_RE.findall(clause):
                    name = name.rstrip(".,;:)")
                    if "." in name:
                        line_paths.append(f"/app/{name}")
                for name in _OUTPUT_FILENAME_RE.findall(clause):
                    line_paths.append(f"/app/{name.rstrip('.,;:')}")
                line_paths = list(dict.fromkeys(line_paths))
                if re.search(r"\bconvert\b", clause, re.IGNORECASE):
                    if len(line_paths) < 2 and not re.search(
                        r"\b(?:into|to)\b", clause, re.IGNORECASE
                    ):
                        continue
                    line_paths = line_paths[-1:]
                if len(line_paths) > 1 and _OPTIONAL_OUTPUT_RE.search(clause):
                    optional_groups.append(tuple(line_paths))
                    continue
                for path in line_paths:
                    if path not in output_paths:
                        output_paths.append(path)

        return cls(
            tuple(paths),
            tuple(requirements),
            tuple(output_paths),
            tuple(optional_groups),
        )

    def render_runtime_reminder(self) -> str:
        """Compact, answer-free specification reminder for early error detection."""
        outputs = ", ".join(self.output_paths) or "no explicit file output"
        if self.optional_output_groups:
            choices = [" OR ".join(group) for group in self.optional_output_groups]
            outputs = "; ".join(filter(None, (outputs, *choices)))
        constraints = " | ".join(self.requirements[:4])
        if len(constraints) > 700:
            constraints = constraints[:697] + "..."
        judged_constraints = constraints or "all explicit task requirements"
        return (
            "[SPECIFICATION LEDGER]\n"
            f"Required output: {outputs}\n"
            f"Judge actions against: {judged_constraints}\n"
            "Keep VERIFIED facts separate from assumptions. Before a "
            "state-changing action, "
            "probe any assumption whose failure would invalidate the plan."
        )

    def render_grounding_gate(self) -> str:
        artifacts = "\n".join(f"- {path}" for path in self.artifact_paths)
        constraints = "\n".join(f"- {item}" for item in self.requirements)
        if not artifacts:
            artifacts = "- Infer the required final artifact from the task text."
        if not constraints:
            constraints = "- Preserve every explicit requirement in the task text."
        return (
            "\n\n[EARLY GROUNDING GATE]\n"
            "Before the first state-changing action, verify critical assumptions with "
            "cheap environment evidence (paths, installed tools, service endpoints, "
            "formats, shapes, or schemas). Do not merely restate the task. Keep "
            "a short "
            "ledger of VERIFIED FACTS and OPEN ASSUMPTIONS, and test assumptions whose "
            "failure would invalidate the plan. Recoverable exploration is allowed.\n"
            f"Candidate task paths/artifacts:\n{artifacts}\n"
            f"Explicit requirements extracted from the task:\n{constraints}\n"
            "This gate contains no solution; derive the implementation yourself."
        )
