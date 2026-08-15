"""Run a Hermes agent against one task in a local Terminal-Bench dataset."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from terminal_bench.harness.harness import Harness

AGENTS = {
    "replayable-hermes": "hermes_agent.replayable_hermes:ReplayableHermesAgent",
    "intervened-terminus": ("hermes_agent.intervened_terminus:IntervenedTerminusAgent"),
    "guided-intervention": ("hermes_agent.guided_intervention:GuidedInterventionAgent"),
}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-path", type=Path, required=True)
    parser.add_argument("--task", required=True)
    parser.add_argument("--agent", choices=sorted(AGENTS), default="replayable-hermes")
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
    parser.add_argument("--replay-path", type=Path)
    parser.add_argument("--replay-until", type=int, default=0)
    parser.add_argument("--intervention")
    parser.add_argument("--no-rebuild", action="store_true")
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

    results = Harness(
        output_path=output_path,
        run_id=run_id,
        agent_import_path=AGENTS[args.agent],
        model_name=args.model,
        dataset_path=dataset_path,
        task_ids=[args.task],
        agent_kwargs=agent_kwargs,
        no_rebuild=args.no_rebuild,
        cleanup=False,
        n_concurrent_trials=1,
        n_attempts=1,
        global_agent_timeout_sec=900,
        global_test_timeout_sec=360,
    ).run()
    print(
        json.dumps(
            {
                "run_id": run_id,
                "resolved": results.n_resolved,
                "unresolved": results.n_unresolved,
                "accuracy": results.accuracy,
                "trajectory": str(trajectory_path),
            }
        )
    )


if __name__ == "__main__":
    main()
