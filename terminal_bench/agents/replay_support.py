import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ReplayCommandSpec:
    keystrokes: str
    duration_sec: float = 1.0


@dataclass(frozen=True)
class ReplayTurnSpec:
    commands: tuple[ReplayCommandSpec, ...]
    task_complete: bool = False
    analysis: str = "Replay step"
    plan: str = "Replay step"
    response: str | None = None


def load_replay_trajectory(path: Path) -> list[ReplayTurnSpec]:
    data = json.loads(path.read_text())

    if isinstance(data, dict):
        turns = data.get("turns") or data.get("episodes") or data.get("steps")
        if turns is None:
            raise ValueError("Replay trajectory must contain turns, episodes, or steps")
    elif isinstance(data, list):
        turns = data
    else:
        raise ValueError("Replay trajectory must be a list or an object containing turns")

    if not isinstance(turns, list):
        raise ValueError("Replay trajectory turns must be a list")

    normalized_turns: list[ReplayTurnSpec] = []
    for turn_index, turn in enumerate(turns):
        if not isinstance(turn, dict):
            raise ValueError(f"Replay turn {turn_index} must be an object")

        raw_commands = turn.get("commands") or turn.get("command_batch") or []
        if not isinstance(raw_commands, list):
            raise ValueError(f"Replay turn {turn_index} commands must be a list")

        normalized_commands: list[ReplayCommandSpec] = []
        for command_index, command in enumerate(raw_commands):
            if isinstance(command, str):
                normalized_commands.append(ReplayCommandSpec(keystrokes=command))
                continue

            if not isinstance(command, dict):
                raise ValueError(
                    f"Replay turn {turn_index} command {command_index} must be a string or object"
                )

            keystrokes = command.get("keystrokes")
            if not isinstance(keystrokes, str):
                raise ValueError(
                    f"Replay turn {turn_index} command {command_index} missing keystrokes"
                )

            duration_value = command.get("duration_sec", command.get("duration", 1.0))
            try:
                duration_sec = float(duration_value)
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    f"Replay turn {turn_index} command {command_index} has invalid duration"
                ) from exc

            normalized_commands.append(
                ReplayCommandSpec(keystrokes=keystrokes, duration_sec=duration_sec)
            )

        normalized_turns.append(
            ReplayTurnSpec(
                commands=tuple(normalized_commands),
                task_complete=bool(turn.get("task_complete", False)),
                analysis=str(turn.get("analysis", "Replay step")),
                plan=str(turn.get("plan", "Replay step")),
                response=turn.get("response"),
            )
        )

    return normalized_turns


def render_replay_response(
    turn: ReplayTurnSpec,
    parser_name: str,
) -> str:
    if turn.response:
        return turn.response

    if parser_name == "json":
        payload = {
            "analysis": turn.analysis,
            "plan": turn.plan,
            "commands": [
                {"keystrokes": command.keystrokes, "duration": command.duration_sec}
                for command in turn.commands
            ],
        }
        if turn.task_complete:
            payload["task_complete"] = True
        return json.dumps(payload, indent=2)

    if parser_name == "xml":
        commands_xml = "\n".join(
            (
                f'<keystrokes duration="{command.duration_sec}">' 
                f"{command.keystrokes}</keystrokes>"
            )
            for command in turn.commands
        )
        task_complete_xml = (
            "\n<task_complete>true</task_complete>" if turn.task_complete else ""
        )
        return (
            "<response>\n"
            f"<analysis>{turn.analysis}</analysis>\n"
            f"<plan>{turn.plan}</plan>\n"
            f"<commands>\n{commands_xml}\n</commands>"
            f"{task_complete_xml}\n"
            "</response>"
        )

    raise ValueError(f"Unsupported parser name: {parser_name}")


def apply_message_intervention(
    messages: list[dict[str, str]],
    mode: str,
    payload: str | None,
) -> None:
    if mode == "none" or not payload:
        return

    if mode == "inject":
        messages.append({"role": "user", "content": payload})
        return

    if mode == "overwrite":
        for index in range(len(messages) - 1, -1, -1):
            if messages[index].get("role") == "assistant":
                messages[index] = {"role": "assistant", "content": payload}
                return

        messages.append({"role": "assistant", "content": payload})
        return

    raise ValueError("Intervention mode must be one of none, inject, overwrite")