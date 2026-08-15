import json
from pathlib import Path

from hermes_agent.replay_support import (
    ReplayCommandSpec,
    ReplayTurnSpec,
    apply_message_intervention,
    default_artifact_path,
    load_replay_trajectory,
    render_replay_response,
)
from hermes_agent.terminus_json_plain_parser import TerminusJSONPlainParser


def test_replay_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "trajectory.json"
    path.write_text(
        json.dumps(
            {
                "turns": [
                    {
                        "commands": [{"keystrokes": "echo hello", "duration": 1}],
                        "task_complete": True,
                    }
                ]
            }
        )
    )

    turns = load_replay_trajectory(path)
    response = render_replay_response(turns[0], "json")
    parsed = TerminusJSONPlainParser().parse_response(response)

    assert parsed.error == ""
    assert parsed.is_task_complete is True
    assert parsed.commands[0].keystrokes == "echo hello"


def test_intervention_modes() -> None:
    messages = [
        {"role": "user", "content": "task"},
        {"role": "assistant", "content": "old"},
    ]
    apply_message_intervention(messages, "inject", "hint")
    apply_message_intervention(messages, "overwrite", "replacement")

    assert messages[-2] == {"role": "assistant", "content": "replacement"}
    assert messages[-1] == {"role": "user", "content": "hint"}


def test_default_artifact_path(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("TB_ARTIFACT_DIR", str(tmp_path))
    assert default_artifact_path("trace.json") == tmp_path / "trace.json"


def test_render_explicit_turn() -> None:
    turn = ReplayTurnSpec(commands=(ReplayCommandSpec("pwd", 0.5),))
    assert '"keystrokes": "pwd"' in render_replay_response(turn, "json")
