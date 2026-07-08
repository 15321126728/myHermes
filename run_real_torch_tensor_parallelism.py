import os
import subprocess
import sys
from pathlib import Path


def main() -> None:
    repo_root = Path(__file__).resolve().parent
    run_id = "torch-tensor-parallelism-deepseek"
    trajectory_path = Path(f"/tmp/{run_id}-trajectory.json")

    model_name = os.environ.get("TB_MODEL_NAME", "deepseek/deepseek-chat")
    api_base = os.environ.get("TB_API_BASE", "https://api.deepseek.com/v1")

    cmd = [
        sys.executable,
        "-m",
        "terminal_bench.cli.tb.main",
        "run",
        "--dataset-path",
        str(repo_root / "original-tasks"),
        "--task-id",
        "torch-tensor-parallelism",
        "--run-id",
        run_id,
        "--agent-import-path",
        "terminal_bench.agents.replayable_hermes:ReplayableHermesAgent",
        "--model",
        model_name,
        "--agent-kwarg",
        f"api_base={api_base}",
        "--agent-kwarg",
        "max_episodes=20",
        "--agent-kwarg",
        "intervention_mode=none",
        "--agent-kwarg",
        f"trajectory_output_path={trajectory_path}",
        "--n-concurrent-trials",
        "1",
        "--n-attempts",
        "1",
        "--global-agent-timeout-sec",
        "900",
        "--global-test-timeout-sec",
        "600",
    ]

    print("========== 开始真实跑测 ==========")
    print(f"task= torch-tensor-parallelism")
    print(f"model= {model_name}")
    print(f"api_base= {api_base}")
    print(f"trajectory= {trajectory_path}")

    result = subprocess.run(cmd, text=True)
    print(f"========== 结束，return code={result.returncode} ==========")


if __name__ == "__main__":
    main()