import json
import tempfile
from pathlib import Path

from terminal_bench.agents.replay_support import (
    apply_message_intervention,
    load_replay_trajectory,
    render_replay_response,
)
from terminal_bench.agents.replayable_hermes import ReplayableHermesAgent


class _FakeModel:
    def count_tokens(self, messages: list[dict[str, str]]) -> int:
        return sum(len(message.get("content", "").split()) for message in messages)

    def call(self, prompt: str, message_history: list[dict[str, str]], **kwargs) -> str:
        return json.dumps(
            {
                "analysis": "fallback",
                "plan": "fallback",
                "commands": [],
            }
        )


class _FakeSession:
    def __init__(self) -> None:
        self.sent_keys: list[tuple[str, bool, float]] = []

    def is_session_alive(self) -> bool:
        return True

    def get_incremental_output(self) -> str:
        return "smoke session ready\n"

    def get_asciinema_timestamp(self) -> float:
        return 0.0

    def send_keys(
        self,
        keys: str,
        block: bool = False,
        min_timeout_sec: float = 0.0,
    ) -> None:
        self.sent_keys.append((keys, block, min_timeout_sec))


def _write_smoke_replay(replay_path: Path) -> None:
    replay_path.write_text(
        json.dumps(
            {
                "turns": [
                    {
                        "analysis": "Replay step 1",
                        "plan": "Verify replay wiring",
                        "commands": [],
                        "task_complete": True,
                    },
                    {
                        "analysis": "Replay step 2",
                        "plan": "Confirm completion handling",
                        "commands": [],
                        "task_complete": True,
                    },
                ]
            },
            indent=2,
        )
    )


def _validate_replay_support(replay_path: Path) -> None:
    turns = load_replay_trajectory(replay_path)
    assert len(turns) == 2, "expected two replay turns"
    assert turns[0].task_complete and turns[1].task_complete, (
        "replay turns should mark task completion"
    )

    rendered = render_replay_response(turns[0], "json")
    assert "Replay step 1" in rendered, (
        "rendered replay response should preserve turn content"
    )

    messages = [{"role": "assistant", "content": "previous assistant answer"}]
    apply_message_intervention(messages, "inject", "check the failing file first")
    assert messages[-1]["content"] == "check the failing file first", (
        "inject intervention should append a user message"
    )


def _validate_agent_loop(replay_path: Path, trajectory_path: Path) -> None:
    fake_session = _FakeSession()

    agent = ReplayableHermesAgent(
        model_name="gpt-4o-mini",
        max_episodes=2,
        parser_name="json",
        replay_path=str(replay_path),
        trajectory_output_path=str(trajectory_path),
    )
    agent._llm = _FakeModel()

    result = agent.perform_task(
        instruction="Smoke validate replayable agent behavior",
        session=fake_session,
        logging_dir=None,
    )

    assert result.failure_mode.name == "NONE", "agent should finish without failure"
    assert result.total_input_tokens > 0, "agent should account for input tokens"
    assert trajectory_path.exists(), "agent should write a trajectory file"

    trajectory = json.loads(trajectory_path.read_text())
    assert len(trajectory) == 2, "trajectory should include both replay episodes"
    assert trajectory[0]["replayed"] is True, "first episode should come from replay"
    assert trajectory[1]["task_complete"] is True, (
        "final replay episode should confirm completion"
    )
    assert fake_session.sent_keys == [], (
        "replay-only smoke should not execute terminal commands"
    )


def main() -> None:
    print("========== 备份已完成，开始做本地 agent smoke test ==========")

    with tempfile.TemporaryDirectory(prefix="replayable-hermes-smoke-") as temp_dir:
        temp_root = Path(temp_dir)
        replay_path = temp_root / "replay.json"
        trajectory_path = temp_root / "trajectory.json"

        _write_smoke_replay(replay_path)
        assert replay_path.exists(), "replay fixture should exist before validation"

        _validate_replay_support(replay_path)
        _validate_agent_loop(replay_path, trajectory_path)

        print(f"  -> replay fixture: {replay_path}")
        print(f"  -> trajectory output: {trajectory_path}")
        print("  -> local agent smoke test passed")


if __name__ == "__main__":
    main()