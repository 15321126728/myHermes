import json
from pathlib import Path

from terminal_bench.agents.replay_support import (
    ReplayCommandSpec,
    ReplayTurnSpec,
    apply_message_intervention,
    load_replay_trajectory,
    render_replay_response,
)
from terminal_bench.agents.terminus_2.terminus_json_plain_parser import (
    TerminusJSONPlainParser,
)
from terminal_bench.agents.terminus_2.terminus_xml_plain_parser import (
    TerminusXMLPlainParser,
)


def test_load_replay_trajectory_normalizes_turns(tmp_path: Path):
    """Test that replay turns are normalized from mixed input shapes."""
    trajectory_path = tmp_path / "trajectory.json"
    trajectory_path.write_text(
        json.dumps(
            {
                "turns": [
                    {
                        "commands": [
                            "echo hello",
                            {"keystrokes": "sleep 1", "duration_sec": 2},
                        ],
                        "task_complete": True,
                    }
                ]
            }
        )
    )

    turns = load_replay_trajectory(trajectory_path)

    assert len(turns) == 1
    assert turns[0].task_complete is True
    assert turns[0].commands[0].keystrokes == "echo hello"
    assert turns[0].commands[0].duration_sec == 1.0
    assert turns[0].commands[1].duration_sec == 2.0


def test_render_replay_response_is_valid_json():
    """Test that JSON replay responses remain parseable by the terminal parser."""
    response = render_replay_response(
        ReplayTurnSpec(
            commands=(ReplayCommandSpec(keystrokes="echo hello", duration_sec=1.5),),
            task_complete=True,
        ),
        parser_name="json",
    )

    result = TerminusJSONPlainParser().parse_response(response)
    assert result.error == ""
    assert result.is_task_complete is True
    assert result.commands[0].keystrokes == "echo hello"


def test_render_replay_response_is_valid_xml():
    """Test that XML replay responses remain parseable by the terminal parser."""
    response = render_replay_response(
        ReplayTurnSpec(
            commands=(ReplayCommandSpec(keystrokes="echo hello", duration_sec=1.5),),
            task_complete=False,
        ),
        parser_name="xml",
    )

    result = TerminusXMLPlainParser().parse_response(response)
    assert result.error == ""
    assert result.is_task_complete is False
    assert result.commands[0].keystrokes == "echo hello"


def test_apply_message_intervention_injects_and_overwrites():
    """Test that message history can be injected into or overwritten in place."""
    messages = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": "reply"},
    ]

    apply_message_intervention(messages, "inject", "new hint")
    assert messages[-1] == {"role": "user", "content": "new hint"}

    apply_message_intervention(messages, "overwrite", "replaced reply")
    assert messages[-2] == {"role": "assistant", "content": "replaced reply"}