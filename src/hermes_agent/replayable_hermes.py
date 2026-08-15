import json
from pathlib import Path

from terminal_bench.agents.base_agent import AgentResult
from terminal_bench.agents.failure_mode import FailureMode
from terminal_bench.llms.chat import Chat
from terminal_bench.terminal.tmux_session import TmuxSession

from hermes_agent.replay_support import (
    apply_message_intervention,
    default_artifact_path,
    load_replay_trajectory,
    render_replay_response,
)
from hermes_agent.terminus import Command, Terminus2


class ReplayableHermesAgent(Terminus2):
    def __init__(
        self,
        model_name: str,
        max_episodes: int | None = None,
        parser_name: str = "json",
        api_base: str | None = None,
        temperature: float = 0.7,
        replay_path: str | None = None,
        replay_until_episode: int = 0,
        intervention_mode: str = "none",
        intervention_payload: str | None = None,
        trajectory_output_path: str | None = None,
        **kwargs,
    ):
        super().__init__(
            model_name=model_name,
            max_episodes=max_episodes,
            parser_name=parser_name,
            api_base=api_base,
            temperature=temperature,
            **kwargs,
        )
        self._replay_path = Path(replay_path) if replay_path else None
        self._replay_until_episode = max(0, replay_until_episode)
        self._intervention_mode = intervention_mode
        self._intervention_payload = intervention_payload
        self._trajectory_output_path = (
            Path(trajectory_output_path) if trajectory_output_path else None
        )
        self._replay_turns = (
            load_replay_trajectory(self._replay_path)
            if self._replay_path is not None
            else []
        )
        self._trajectory_records: list[dict[str, object]] = []

    @staticmethod
    def name() -> str:
        return "replayable-hermes"

    def _append_chat_turn(self, chat: Chat, prompt: str, response: str) -> None:
        input_tokens = chat._model.count_tokens(
            chat._messages + [{"role": "user", "content": prompt}]
        )
        output_tokens = chat._model.count_tokens(
            [{"role": "assistant", "content": response}]
        )

        chat._cumulative_input_tokens += input_tokens
        chat._cumulative_output_tokens += output_tokens
        chat._messages.extend(
            [
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": response},
            ]
        )

    @staticmethod
    def _serialize_commands(commands: list[Command]) -> list[dict[str, object]]:
        return [
            {"keystrokes": cmd.keystrokes, "duration": cmd.duration_sec}
            for cmd in commands
        ]

    def _handle_replay_interaction(
        self,
        chat: Chat,
        prompt: str,
        logging_paths: tuple[Path | None, Path | None, Path | None],
        episode: int,
        session: TmuxSession,
    ) -> tuple[list[Command], bool, str, str]:
        _logging_path, prompt_path, response_path = logging_paths

        if prompt_path is not None:
            prompt_path.write_text(prompt)

        replay_turn = self._replay_turns[episode]
        response = render_replay_response(replay_turn, self._parser_name)

        if response_path is not None:
            response_path.write_text(response)

        self._append_chat_turn(chat=chat, prompt=prompt, response=response)

        result = self._parser.parse_response(response)
        feedback = ""
        if result.error:
            feedback += f"ERROR: {result.error}"
            if result.warning:
                feedback += f"\nWARNINGS: {result.warning}"
        elif result.warning:
            feedback += f"WARNINGS: {result.warning}"

        commands = [
            Command(
                keystrokes=parsed_cmd.keystrokes,
                duration_sec=min(parsed_cmd.duration, 60),
            )
            for parsed_cmd in result.commands
        ]

        self._record_asciinema_marker(
            f"Replay episode {episode}: {len(commands)} commands", session
        )

        return commands, result.is_task_complete, feedback, response

    def _handle_llm_interaction(
        self,
        chat: Chat,
        prompt: str,
        logging_paths: tuple[Path | None, Path | None, Path | None],
        original_instruction: str = "",
        session: TmuxSession | None = None,
        **kwargs,
    ) -> tuple[list[Command], bool, str, str | None]:
        """Also return the raw LLM response text for trajectory recording."""
        commands, is_task_complete, feedback = super()._handle_llm_interaction(
            chat, prompt, logging_paths, original_instruction, session, **kwargs
        )
        # Read the response from the file written by the parent's _query_llm
        # (response_path is the third element of logging_paths)
        response_text: str | None = None
        response_path = logging_paths[2]
        if response_path is not None and response_path.exists():
            response_text = response_path.read_text()
        return commands, is_task_complete, feedback, response_text

    def _run_agent_loop(
        self,
        initial_prompt: str,
        session: TmuxSession,
        chat: Chat,
        logging_dir: Path | None = None,
        original_instruction: str = "",
    ) -> None:
        prompt = initial_prompt
        replay_cutoff = self._replay_until_episode

        try:
            for episode in range(self._max_episodes):
                if not session.is_session_alive():
                    self._logger.info("Session has ended, breaking out of agent loop")
                    break

                if original_instruction:
                    proactive_summary = self._check_proactive_summarization(
                        chat, original_instruction, session
                    )
                    if proactive_summary:
                        prompt = proactive_summary

                logging_paths = self._setup_episode_logging(logging_dir, episode)

                replay_mode = episode < min(replay_cutoff, len(self._replay_turns))
                if replay_mode:
                    commands, is_task_complete, feedback, response = (
                        self._handle_replay_interaction(
                            chat=chat,
                            prompt=prompt,
                            logging_paths=logging_paths,
                            episode=episode,
                            session=session,
                        )
                    )
                else:
                    if (
                        self._intervention_mode != "none"
                        and episode == self._replay_until_episode
                    ):
                        apply_message_intervention(
                            chat._messages,
                            self._intervention_mode,
                            self._intervention_payload,
                        )

                    commands, is_task_complete, feedback, response = (
                        self._handle_llm_interaction(
                            chat, prompt, logging_paths, original_instruction, session
                        )
                    )
                    self._record_asciinema_marker(
                        f"Episode {episode}: {len(commands)} commands", session
                    )

                if feedback and "ERROR:" in feedback:
                    prompt = (
                        f"Previous response had parsing errors:\n{feedback}\n\n"
                        f"Please fix these issues and provide a proper "
                        f"{self._get_error_response_type()}."
                    )
                    self._trajectory_records.append(
                        {
                            "episode": episode,
                            "replayed": replay_mode,
                            "prompt": prompt,
                            "response": response,
                            "commands": self._serialize_commands(commands),
                            "feedback": feedback,
                        }
                    )
                    continue

                _, terminal_output = self._execute_commands(commands, session)

                if is_task_complete:
                    if self._pending_completion:
                        self._trajectory_records.append(
                            {
                                "episode": episode,
                                "replayed": replay_mode,
                                "prompt": prompt,
                                "response": response,
                                "commands": self._serialize_commands(commands),
                                "terminal_output": terminal_output,
                                "task_complete": True,
                            }
                        )
                        break

                    self._pending_completion = True
                    prompt = self._get_completion_confirmation_message(terminal_output)
                    self._trajectory_records.append(
                        {
                            "episode": episode,
                            "replayed": replay_mode,
                            "prompt": prompt,
                            "response": response,
                            "commands": self._serialize_commands(commands),
                            "terminal_output": terminal_output,
                            "task_complete": False,
                        }
                    )
                    continue

                self._pending_completion = False

                if feedback and "WARNINGS:" in feedback:
                    prompt = (
                        f"Previous response had warnings:\n{feedback}\n\n"
                        f"{self._limit_output_length(terminal_output)}"
                    )
                else:
                    prompt = self._limit_output_length(terminal_output)

                self._trajectory_records.append(
                    {
                        "episode": episode,
                        "replayed": replay_mode,
                        "prompt": prompt,
                        "response": response,
                        "commands": self._serialize_commands(commands),
                        "terminal_output": terminal_output,
                        "task_complete": False,
                    }
                )

        finally:
            # 【终极保险：强行落盘机制】
            # 无论上方发生了 break 还是框架抛出了异常崩溃，这里一定会执行
            if not self._trajectory_records:
                print("\n⚠️ [ReplayableHermes] 轨迹记录为空，无内容可落盘。")
            else:
                output_path = self._trajectory_output_path or default_artifact_path(
                    "replayable-hermes-trajectory.json"
                )
                try:
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    output_path.write_text(
                        json.dumps(
                            self._trajectory_records, indent=2, ensure_ascii=False
                        ),
                        encoding="utf-8",
                    )
                    print(f"[ReplayableHermes] 轨迹已保存至: {output_path}")
                except Exception as e:
                    self._logger.warning("Failed to save trajectory: %s", e)

    def perform_task(
        self,
        instruction: str,
        session: TmuxSession,
        logging_dir: Path | None = None,
        time_limit_seconds: float | None = None,
    ) -> AgentResult:
        chat = Chat(self._llm)

        initial_prompt = self._prompt_template.format(
            instruction=instruction,
            terminal_state=self._limit_output_length(session.get_incremental_output()),
        )

        self._run_agent_loop(initial_prompt, session, chat, logging_dir, instruction)

        return AgentResult(
            total_input_tokens=chat.total_input_tokens,
            total_output_tokens=chat.total_output_tokens,
            failure_mode=FailureMode.NONE,
            timestamped_markers=self._timestamped_markers,
        )
