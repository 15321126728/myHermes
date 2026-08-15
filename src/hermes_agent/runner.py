"""Run a Hermes agent against one task in a local Terminal-Bench dataset."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from terminal_bench.harness.harness import Harness

from hermes_agent.ablation import (
    MECHANISM_NAMES,
    resolve_ablation_profile,
    standard_ablation_profiles,
)

AGENTS = {
    "replayable-hermes": "hermes_agent.replayable_hermes:ReplayableHermesAgent",
    "intervened-terminus": ("hermes_agent.intervened_terminus:IntervenedTerminusAgent"),
    "guided-intervention": ("hermes_agent.guided_intervention:GuidedInterventionAgent"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument(
        "--agent", choices=sorted(AGENTS), default="guided-intervention"
    )
    parser.add_argument(
        "--model", default=os.environ.get("TB_MODEL_NAME", "deepseek/deepseek-chat")
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("TB_API_BASE", "https://api.deepseek.com/v1"),
    )
    parser.add_argument("--output-path", type=Path, default=Path("runs"))
    parser.add_argument("--run-id")
    parser.add_argument("--max-episodes", type=int, default=20)
    parser.add_argument("--agent-timeout", type=int, default=900)
    parser.add_argument("--test-timeout", type=int, default=360)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--seed", type=int)
    parser.add_argument("--replay-path", type=Path)
    parser.add_argument("--replay-until", type=int, default=0)
    parser.add_argument("--intervention")
    parser.add_argument(
        "--knowledge-file",
        help="Optional path to a domain knowledge document inside the task container",
    )
    parser.add_argument("--no-comprehension-check", action="store_true")
    parser.add_argument("--no-process-guidance", action="store_true")
    parser.add_argument(
        "--ablation-profile",
        choices=standard_ablation_profiles(include_additive=True),
        default="full",
    )
    for mechanism in MECHANISM_NAMES:
        parser.add_argument(
            f"--disable-{mechanism.replace('_', '-')}",
            action="store_true",
        )
    parser.add_argument("--no-rebuild", action="store_true")
    parser.add_argument("--cleanup", action="store_true")
    parser.add_argument(
        "--api-key-env",
        choices=("OPENAI_API_KEY", "DEEPSEEK_API_KEY"),
        help="Environment variable to map to the selected model provider",
    )
    args = parser.parse_args()

    dataset_path = args.dataset_path.expanduser().resolve()
    if not (dataset_path / args.task).is_dir():
        parser.error(f"task does not exist: {dataset_path / args.task}")
    if args.max_episodes < 1:
        parser.error("--max-episodes must be at least 1")
    if args.replay_until < 0:
        parser.error("--replay-until cannot be negative")
    if args.replay_path and not args.replay_path.is_file():
        parser.error(f"replay file does not exist: {args.replay_path}")

    if args.api_key_env:
        selected_key = os.environ.get(args.api_key_env)
        if not selected_key:
            parser.error(f"{args.api_key_env} is not set")
        provider_env = (
            "DEEPSEEK_API_KEY"
            if args.model.startswith("deepseek/")
            else "OPENAI_API_KEY"
        )
        os.environ[provider_env] = selected_key
        selected_key = ""
    if "OPENAI_API_KEY" not in os.environ and "DEEPSEEK_API_KEY" in os.environ:
        os.environ["OPENAI_API_KEY"] = os.environ["DEEPSEEK_API_KEY"]
    if "OPENAI_API_KEY" not in os.environ:
        parser.error("set OPENAI_API_KEY or DEEPSEEK_API_KEY before running")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    run_id = args.run_id or f"hermes-{args.task}-{timestamp}"
    output_path = args.output_path.expanduser().resolve()
    trajectory_path = output_path / run_id / "trajectory.json"
    agent_kwargs: dict[str, object] = {
        "model_name": args.model,
        "api_base": args.api_base,
        "max_episodes": args.max_episodes,
        "temperature": args.temperature,
        "seed": args.seed,
        "trajectory_output_path": str(trajectory_path),
    }
    if args.replay_path:
        agent_kwargs.update(
            replay_path=str(args.replay_path.resolve()),
            replay_until_episode=args.replay_until,
        )
    if args.intervention:
        agent_kwargs.update(
            intervention_mode="inject",
            intervention_payload=args.intervention,
        )
    if args.agent == "guided-intervention":
        ablation = resolve_ablation_profile(args.ablation_profile)
        disabled = [
            mechanism
            for mechanism in MECHANISM_NAMES
            if getattr(args, f"disable_{mechanism}")
        ]
        if args.no_process_guidance:
            disabled.extend(
                [
                    "cognitive_detection",
                    "layer_diagnosis",
                    "ternary_feedback",
                    "adaptive_episodes",
                ]
            )
        if args.no_comprehension_check:
            disabled.append("comprehension_check")
        ablation = ablation.with_disabled(*disabled)
        agent_kwargs.update(
            guidance_task_id=args.task,
            guidance_base_max=args.max_episodes,
            ablation_config=ablation.as_dict(),
        )
        if args.knowledge_file:
            agent_kwargs["knowledge_file"] = args.knowledge_file

    results = Harness(
        output_path=output_path,
        run_id=run_id,
        agent_import_path=AGENTS[args.agent],
        model_name=args.model,
        dataset_path=dataset_path,
        task_ids=[args.task],
        agent_kwargs=agent_kwargs,
        no_rebuild=args.no_rebuild,
        cleanup=args.cleanup,
        n_concurrent_trials=1,
        n_attempts=1,
        global_agent_timeout_sec=args.agent_timeout,
        global_test_timeout_sec=args.test_timeout,
    ).run()
    print(
        json.dumps(
            {
                "run_id": run_id,
                "resolved": results.n_resolved,
                "unresolved": results.n_unresolved,
                "accuracy": results.accuracy,
                "trajectory": str(trajectory_path),
                "ablation_profile": args.ablation_profile,
                "seed": args.seed,
            }
        )
    )


if __name__ == "__main__":
    main()
