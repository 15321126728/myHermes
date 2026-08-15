"""Run resumable, paired ablation experiments for the guided Hermes agent."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import random
import subprocess
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from hermes_agent.ablation import resolve_ablation_profile

PRIMARY_PROFILES = (
    "base",
    "full",
    "full-minus-cognitive-detection",
    "full-minus-layer-diagnosis",
    "full-minus-ternary-feedback",
    "full-minus-adaptive-episodes",
    "full-minus-runtime-verification",
    "full-minus-knowledge-hints",
    "full-minus-comprehension-check",
)


@dataclass(frozen=True)
class TrialSpec:
    task: str
    profile: str
    seed: int
    run_id: str


def _paired_bootstrap_ci(
    paired: list[tuple[dict[str, Any], dict[str, Any]]],
    samples: int = 10_000,
) -> list[float] | None:
    if not paired:
        return None
    rng = random.Random(0)
    deltas = []
    for _ in range(samples):
        selected = [paired[rng.randrange(len(paired))] for _ in paired]
        deltas.append(
            sum(full["resolved"] - other["resolved"] for full, other in selected)
            / len(selected)
        )
    deltas.sort()
    return [
        deltas[int(0.025 * (samples - 1))],
        deltas[int(0.975 * (samples - 1))],
    ]


def _mcnemar_exact_p_value(full_wins: int, profile_wins: int) -> float:
    discordant = full_wins + profile_wins
    if not discordant:
        return 1.0
    tail = sum(
        math.comb(discordant, index)
        for index in range(min(full_wins, profile_wins) + 1)
    ) / (2**discordant)
    return min(1.0, 2 * tail)


def _apply_holm_correction(comparisons: dict[str, dict[str, Any]]) -> None:
    tested = [
        (name, values["mcnemar_p_value"])
        for name, values in comparisons.items()
        if name.startswith("full-minus-")
    ]
    ordered = sorted(tested, key=lambda item: item[1])
    adjusted_floor = 0.0
    total = len(ordered)
    for rank, (name, p_value) in enumerate(ordered):
        adjusted = min(1.0, (total - rank) * p_value)
        adjusted_floor = max(adjusted_floor, adjusted)
        comparisons[name]["holm_adjusted_p_value"] = adjusted_floor


def _slug(value: str) -> str:
    return "".join(char if char.isalnum() or char in "-_" else "-" for char in value)


def _load_tasks(args: argparse.Namespace) -> list[str]:
    tasks = list(args.tasks or [])
    if args.task_file:
        tasks.extend(
            line.strip()
            for line in args.task_file.read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        )
    return list(dict.fromkeys(tasks))


def _trial_result(output_path: Path, spec: TrialSpec) -> dict[str, Any] | None:
    result_path = output_path / spec.run_id / "results.json"
    if not result_path.is_file():
        return None
    payload = json.loads(result_path.read_text())
    rows = payload.get("results", [])
    if not rows:
        return None
    row = rows[0]
    if row.get("failure_mode") == "unknown_agent_error":
        return None
    started = row.get("trial_started_at")
    ended = row.get("trial_ended_at")
    wall_seconds = None
    if started and ended:
        wall_seconds = (
            datetime.fromisoformat(ended) - datetime.fromisoformat(started)
        ).total_seconds()
    result = {
        "task": spec.task,
        "profile": spec.profile,
        "seed": spec.seed,
        "run_id": spec.run_id,
        "resolved": bool(row.get("is_resolved")),
        "failure_mode": row.get("failure_mode"),
        "input_tokens": row.get("total_input_tokens"),
        "output_tokens": row.get("total_output_tokens"),
        "wall_seconds": wall_seconds,
    }
    result.update(_trajectory_metrics(output_path / spec.run_id / "trajectory.json"))
    return result


def _trajectory_metrics(path: Path) -> dict[str, Any]:
    metrics = {
        "episodes": None,
        "effective_episode_limit": None,
        "extensions_granted": 0,
        "cognitive_errors": 0,
        "diagnosis_layers": 0,
        "correct_feedback": 0,
        "recoverable_feedback": 0,
        "irrecoverable_feedback": 0,
        "completion_rejections": 0,
        "knowledge_hints": 0,
        "comprehension_failures": 0,
        "trajectory_resets": 0,
    }
    if not path.is_file():
        return metrics
    records = json.loads(path.read_text())
    if not isinstance(records, list):
        return metrics
    episode_numbers = {
        record["episode"]
        for record in records
        if isinstance(record, dict) and isinstance(record.get("episode"), int)
    }
    metrics["episodes"] = len(episode_numbers)
    for record in records:
        if not isinstance(record, dict):
            continue
        if record.get("record_type") == "run_config":
            metrics["effective_episode_limit"] = record.get("effective_episode_limit")
            metrics["extensions_granted"] = record.get("extensions_granted", 0)
        diagnostics = record.get("diagnostics") or {}
        metrics["cognitive_errors"] += len(diagnostics.get("cognitive_errors", []))
        metrics["diagnosis_layers"] += len(diagnostics.get("diagnosis_layers", []))
        feedback = diagnostics.get("feedback_level") or ""
        if "IRRECOVERABLE" in feedback:
            metrics["irrecoverable_feedback"] += 1
        elif "RECOVERABLE" in feedback:
            metrics["recoverable_feedback"] += 1
        elif "CORRECT" in feedback:
            metrics["correct_feedback"] += 1
        intervention = record.get("intervention_type")
        if record.get("completion_rejected"):
            metrics["completion_rejections"] += 1
        if intervention == "knowledge_hint":
            metrics["knowledge_hints"] += 1
        if (
            intervention == "comprehension_check"
            and record.get("kind") == "misunderstanding_detected"
        ):
            metrics["comprehension_failures"] += 1
        if intervention == "trajectory_reset":
            metrics["trajectory_resets"] += 1
    return metrics


def _write_summary(experiment_dir: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "task",
        "profile",
        "seed",
        "run_id",
        "resolved",
        "failure_mode",
        "input_tokens",
        "output_tokens",
        "wall_seconds",
        "episodes",
        "effective_episode_limit",
        "extensions_granted",
        "cognitive_errors",
        "diagnosis_layers",
        "correct_feedback",
        "recoverable_feedback",
        "irrecoverable_feedback",
        "completion_rejections",
        "knowledge_hints",
        "comprehension_failures",
        "trajectory_resets",
    ]
    with (experiment_dir / "results.csv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    profiles: dict[str, dict[str, Any]] = {}
    for profile in dict.fromkeys(row["profile"] for row in rows):
        profile_rows = [row for row in rows if row["profile"] == profile]
        resolved = sum(row["resolved"] for row in profile_rows)
        input_tokens = [
            row["input_tokens"]
            for row in profile_rows
            if row["input_tokens"] is not None
        ]
        output_tokens = [
            row["output_tokens"]
            for row in profile_rows
            if row["output_tokens"] is not None
        ]
        total_tokens = [
            row["input_tokens"] + row["output_tokens"]
            for row in profile_rows
            if row["input_tokens"] is not None and row["output_tokens"] is not None
        ]
        episodes = [
            row["episodes"] for row in profile_rows if row["episodes"] is not None
        ]
        profiles[profile] = {
            "trials": len(profile_rows),
            "resolved": resolved,
            "accuracy": resolved / len(profile_rows),
            "mean_input_tokens": mean(input_tokens) if input_tokens else None,
            "mean_output_tokens": mean(output_tokens) if output_tokens else None,
            "mean_total_tokens": mean(total_tokens) if total_tokens else None,
            "total_tokens_per_resolved_task": (
                sum(total_tokens) / resolved if resolved and total_tokens else None
            ),
            "mean_episodes": mean(episodes) if episodes else None,
            "mechanism_events": {
                name: sum(row[name] for row in profile_rows)
                for name in (
                    "extensions_granted",
                    "cognitive_errors",
                    "diagnosis_layers",
                    "correct_feedback",
                    "recoverable_feedback",
                    "irrecoverable_feedback",
                    "completion_rejections",
                    "knowledge_hints",
                    "comprehension_failures",
                    "trajectory_resets",
                )
            },
        }

    full_accuracy = profiles.get("full", {}).get("accuracy")
    for profile, values in profiles.items():
        values["delta_vs_full"] = (
            values["accuracy"] - full_accuracy if full_accuracy is not None else None
        )
    comparisons = {}
    full_rows = {
        (row["task"], row["seed"]): row for row in rows if row["profile"] == "full"
    }
    for profile in profiles:
        if profile == "full":
            continue
        paired = [
            (full_rows[(row["task"], row["seed"])], row)
            for row in rows
            if row["profile"] == profile and (row["task"], row["seed"]) in full_rows
        ]
        full_wins = sum(
            full["resolved"] and not other["resolved"] for full, other in paired
        )
        profile_wins = sum(
            other["resolved"] and not full["resolved"] for full, other in paired
        )
        comparisons[profile] = {
            "paired_trials": len(paired),
            "full_minus_profile_accuracy": (
                sum(full["resolved"] - other["resolved"] for full, other in paired)
                / len(paired)
                if paired
                else None
            ),
            "bootstrap_95_ci": _paired_bootstrap_ci(paired),
            "full_wins": full_wins,
            "profile_wins": profile_wins,
            "mcnemar_p_value": _mcnemar_exact_p_value(full_wins, profile_wins),
            "both_resolved": sum(
                full["resolved"] and other["resolved"] for full, other in paired
            ),
            "both_failed": sum(
                not full["resolved"] and not other["resolved"] for full, other in paired
            ),
        }
    _apply_holm_correction(comparisons)
    (experiment_dir / "summary.json").write_text(
        json.dumps(
            {
                "profiles": profiles,
                "comparisons_vs_full": comparisons,
                "completed_trials": len(rows),
            },
            indent=2,
        )
    )


def _build_command(args: argparse.Namespace, spec: TrialSpec) -> list[str]:
    command = [
        sys.executable,
        "-m",
        "hermes_agent.runner",
        "--dataset-path",
        str(args.dataset_path),
        "--task",
        spec.task,
        "--agent",
        "guided-intervention",
        "--model",
        args.model,
        "--api-base",
        args.api_base,
        "--output-path",
        str(args.output_path),
        "--run-id",
        spec.run_id,
        "--max-episodes",
        str(args.max_episodes),
        "--agent-timeout",
        str(args.agent_timeout),
        "--test-timeout",
        str(args.test_timeout),
        "--temperature",
        str(args.temperature),
        "--seed",
        str(spec.seed),
        "--ablation-profile",
        spec.profile,
        "--cleanup",
    ]
    if args.no_rebuild:
        command.append("--no-rebuild")
    if args.selected_api_key_env:
        command.extend(("--api-key-env", args.selected_api_key_env))
    return command


def _auth_preflight(api_base: str, model: str) -> tuple[bool, str, str | None]:
    candidates = (
        ("DEEPSEEK_API_KEY", "OPENAI_API_KEY")
        if model.startswith("deepseek/")
        else ("OPENAI_API_KEY",)
    )
    available = [name for name in candidates if os.environ.get(name)]
    if not available:
        return False, "missing_api_key", None
    endpoint_model = model.split("/", 1)[-1]
    request_body = json.dumps(
        {
            "model": endpoint_model,
            "messages": [{"role": "user", "content": "Reply OK"}],
            "max_tokens": 1,
            "temperature": 0,
        }
    )
    last_reason = "credential_preflight_failed"
    for env_name in available:
        key = os.environ[env_name]
        curl_config = "\n".join(
            (
                f'url = "{api_base.rstrip("/")}/chat/completions"',
                f'header = "Authorization: Bearer {key}"',
                'output = "/dev/null"',
                'write-out = "%{http_code}"',
                "silent",
                "show-error",
                "connect-timeout = 10",
                "max-time = 20",
            )
        )
        try:
            result = subprocess.run(
                [
                    "curl",
                    "--config",
                    "-",
                    "--request",
                    "POST",
                    "--header",
                    "Content-Type: application/json",
                    "--data",
                    request_body,
                ],
                input=curl_config,
                text=True,
                capture_output=True,
                check=False,
            )
        except OSError:
            return False, "curl_preflight_unavailable", None
        finally:
            key = ""
            curl_config = ""
        status = result.stdout.strip()
        if result.returncode != 0 or not status.isdigit():
            last_reason = "network_preflight_failed"
        elif status.startswith("2"):
            return True, "ok", env_name
        elif status in {"401", "403", "400"}:
            last_reason = "credential_preflight_failed"
        else:
            last_reason = f"preflight_http_{status}"
    request_body = ""
    return False, last_reason, None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--tasks", nargs="*")
    parser.add_argument("--task-file", type=Path)
    parser.add_argument("--profiles", nargs="+", default=list(PRIMARY_PROFILES))
    parser.add_argument("--seeds", nargs="+", type=int, default=[0, 1, 2])
    parser.add_argument("--max-episodes", type=int, default=20)
    parser.add_argument("--agent-timeout", type=int, default=600)
    parser.add_argument("--test-timeout", type=int, default=360)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument(
        "--model", default=os.environ.get("TB_MODEL_NAME", "deepseek/deepseek-chat")
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("TB_API_BASE", "https://api.deepseek.com/v1"),
    )
    parser.add_argument("--output-path", type=Path, default=Path("runs"))
    parser.add_argument("--experiment-id")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-rebuild", action="store_true")
    parser.add_argument("--skip-auth-preflight", action="store_true")
    args = parser.parse_args()
    args.selected_api_key_env = None

    args.dataset_path = args.dataset_path.expanduser().resolve()
    args.output_path = args.output_path.expanduser().resolve()
    tasks = _load_tasks(args)
    if not tasks:
        parser.error("provide --tasks or --task-file")
    missing = [task for task in tasks if not (args.dataset_path / task).is_dir()]
    if missing:
        parser.error(f"tasks not found in dataset: {', '.join(missing)}")
    for profile in args.profiles:
        try:
            resolve_ablation_profile(profile)
        except ValueError as exc:
            parser.error(str(exc))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    experiment_id = args.experiment_id or f"ablation-{timestamp}"
    experiment_dir = args.output_path / "experiments" / experiment_id
    experiment_dir.mkdir(parents=True, exist_ok=True)
    specs = [
        TrialSpec(
            task=task,
            profile=profile,
            seed=seed,
            run_id=_slug(f"{experiment_id}-{profile}-{task}-s{seed}"),
        )
        for profile in args.profiles
        for task in tasks
        for seed in args.seeds
    ]
    manifest = {
        "experiment_id": experiment_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset_path": str(args.dataset_path),
        "model": args.model,
        "api_base": args.api_base,
        "temperature": args.temperature,
        "base_episode_limit": args.max_episodes,
        "agent_timeout": args.agent_timeout,
        "test_timeout": args.test_timeout,
        "tasks": tasks,
        "seeds": args.seeds,
        "profiles": {
            name: resolve_ablation_profile(name).as_dict() for name in args.profiles
        },
        "trials": [asdict(spec) for spec in specs],
        "status": "planned",
    }
    manifest_path = experiment_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Experiment {experiment_id}: {len(specs)} paired trials")
    if args.dry_run:
        print(f"Manifest written to {experiment_dir / 'manifest.json'}")
        return

    if not args.skip_auth_preflight:
        authenticated, reason, selected_env = _auth_preflight(args.api_base, args.model)
        if not authenticated:
            manifest["status"] = "blocked"
            manifest["blocked_reason"] = reason
            manifest_path.write_text(json.dumps(manifest, indent=2))
            parser.error(
                f"experiment blocked by API preflight: {reason}; "
                "fix credentials and rerun the same command"
            )
        args.selected_api_key_env = selected_env
        manifest["api_key_env"] = selected_env
    manifest["status"] = "running"
    manifest_path.write_text(json.dumps(manifest, indent=2))

    rows = []
    failed_trials = []
    for index, spec in enumerate(specs, 1):
        existing = _trial_result(args.output_path, spec)
        if existing is not None:
            rows.append(existing)
            print(f"[{index}/{len(specs)}] resume {spec.run_id}")
            continue
        print(f"[{index}/{len(specs)}] run {spec.run_id}")
        log_path = experiment_dir / f"{spec.run_id}.log"
        with log_path.open("w") as log_handle:
            subprocess.run(
                _build_command(args, spec),
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                check=False,
            )
        result = _trial_result(args.output_path, spec)
        if result is not None:
            rows.append(result)
        else:
            failed_trials.append(spec.run_id)
        _write_summary(experiment_dir, rows)

    _write_summary(experiment_dir, rows)
    manifest["status"] = "complete" if not failed_trials else "partial"
    manifest["failed_trials"] = failed_trials
    manifest["completed_at"] = datetime.now(timezone.utc).isoformat()
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"Results written to {experiment_dir}")
    if failed_trials:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
