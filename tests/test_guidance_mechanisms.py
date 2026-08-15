import inspect
import sys

from hermes_agent import runner
from hermes_agent.guided_intervention import GuidedInterventionAgent
from hermes_agent.process_guidance import (
    AdaptiveEpisodeManager,
    CognitiveErrorDetector,
    LayerDiagnoser,
    TernaryEvaluator,
    TernaryFeedback,
)
from hermes_agent.task_contract import TaskContract


class ExecResult:
    def __init__(self, exit_code: int):
        self.exit_code = exit_code
        self.output = b""


class FakeContainer:
    def __init__(self, nonempty_paths: set[str]):
        self.nonempty_paths = nonempty_paths

    def exec_run(self, command):
        joined = " ".join(command)
        exists = any(path in joined for path in self.nonempty_paths)
        return ExecResult(0 if exists else 1)


class FakeSession:
    def __init__(self, nonempty_paths: set[str]):
        self.container = FakeContainer(nonempty_paths)


def make_agent(task_id: str = "") -> GuidedInterventionAgent:
    return GuidedInterventionAgent(
        model_name="test-model",
        max_episodes=5,
        guidance_task_id=task_id,
    )


def test_cognitive_detector_has_exactly_five_documented_categories() -> None:
    detector = CognitiveErrorDetector("")
    assert {pattern["name"] for pattern in detector.COGNITIVE_PATTERNS} == {
        "task_misunderstanding",
        "wrong_tool_choice",
        "format_misunderstanding",
        "premature_success",
        "analysis_paralysis",
    }

    errors = detector.analyze_episode(
        0, ["cat input.csv"], "invalid csv format", 10
    )
    assert "format_misunderstanding" in {error.type for error in errors}
    assert detector.get_progress_summary()["read_count"] == 1

    errors = detector.analyze_episode(
        1,
        ["head input.csv"],
        "",
        10,
        agent_response="The task is complete!",
    )
    kinds = {error.type for error in errors}
    assert "premature_success" in kinds
    assert "analysis_paralysis" in kinds


def test_layer_diagnoser_implements_all_seven_layers() -> None:
    diagnoser = LayerDiagnoser()
    assert set(diagnoser.LAYER_SIGNALS) == {
        "execution",
        "tool",
        "context",
        "lifecycle",
        "observability",
        "validation",
        "governance",
    }
    findings = diagnoser.diagnose(
        0,
        ["pip install package"],
        "I am unable to verify it, so I will skip the requirement",
    )
    assert {finding["layer"] for finding in findings} >= {
        "observability",
        "governance",
    }


def test_ternary_evaluator_reaches_every_state() -> None:
    evaluator = TernaryEvaluator()
    correct, _, _ = evaluator.evaluate(
        1, ["pytest"], "3 tests passed", has_output_file=True
    )
    recoverable, _, _ = evaluator.evaluate(1, [], "Traceback: error")
    irrecoverable, _, _ = evaluator.evaluate(
        11, ["cat input"], "still checking", is_analysis_loop=True
    )
    assert correct == TernaryFeedback.CORRECT
    assert recoverable == TernaryFeedback.RECOVERABLE
    assert irrecoverable == TernaryFeedback.IRRECOVERABLE


def test_adaptive_budget_extends_only_productive_boundary() -> None:
    productive = AdaptiveEpisodeManager(
        base_max_episodes=3, extension_size=2, max_extensions=1
    )
    for _ in range(3):
        productive.record_episode("active", 0.25)
    assert productive.should_extend(2, 3)
    assert productive.extend_limit(2, 3) == 5
    assert not productive.should_extend(4, 5)

    stalled = AdaptiveEpisodeManager(base_max_episodes=3)
    for _ in range(3):
        stalled.record_episode("analysis", 0.0)
    assert not stalled.should_extend(2, 3)

    source = inspect.getsource(GuidedInterventionAgent._run_agent_loop)
    assert "itertools.count()" in source


def test_productive_classifier_does_not_reward_python_reads() -> None:
    agent = make_agent()
    assert not agent._is_productive_command(
        "python -c \"print(open('/app/input.txt').read())\""
    )
    assert agent._is_productive_command(
        "python -c \"open('/app/out.txt', 'w').write('ok')\""
    )
    assert agent._is_productive_command("sed -i 's/old/new/' /app/config")


def test_runtime_output_validation_requires_nonempty_container_file() -> None:
    agent = make_agent()
    instruction = "Create /app/result.txt as the final output."
    missing = FakeSession(set())
    present = FakeSession({"/app/result.txt"})

    assert not agent._check_output_file("created result.txt", missing, instruction)
    assert agent._check_output_file("", present, instruction)
    assert agent._artifact_requirement_detected


def test_task_contract_extracts_relative_output_filename() -> None:
    contract = TaskContract.from_instruction(
        "Read source.csv and write the final data. Output file must be result.parquet."
    )
    assert contract.output_paths == ("/app/result.parquet",)


def test_knowledge_hint_requires_a_real_document() -> None:
    agent = make_agent("dna-assembly")
    assert not agent._knowledge_file_exists(FakeSession(set()))

    available_agent = make_agent("dna-assembly")
    session = FakeSession({"/app/KNOWLEDGE_GOLDEN_GATE.md"})
    assert available_agent._knowledge_file_exists(session)
    hint = available_agent._maybe_inject_knowledge_hint(0, "", "")
    assert "KNOWLEDGE_GOLDEN_GATE.md" in hint


def test_generic_comprehension_check_is_machine_verifiable() -> None:
    agent = make_agent("unconfigured-task")
    prompt = agent._build_comprehension_prompt(
        "Transform the source safely. Create /app/a.json and /app/b.json."
    )
    assert "/app/a.json" not in prompt

    failed, _ = agent._check_comprehension("I will create /app/a.json", "")
    assert failed
    failed, feedback = agent._check_comprehension(
        "I will transform safely and create /app/a.json and /app/b.json", ""
    )
    assert not failed
    assert feedback == ""


def test_cli_defaults_to_guided_agent_and_passes_task_id(
    monkeypatch, tmp_path
) -> None:
    captured = {}

    class Result:
        n_resolved = 1
        n_unresolved = 0
        accuracy = 1.0

    class FakeHarness:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def run(self):
            return Result()

    dataset = tmp_path / "tasks"
    (dataset / "sample-task").mkdir(parents=True)
    monkeypatch.setattr(runner, "Harness", FakeHarness)
    monkeypatch.setenv("OPENAI_API_KEY", "test-only")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hermes-agent",
            "--dataset-path",
            str(dataset),
            "--task",
            "sample-task",
        ],
    )

    runner.main()

    assert captured["agent_import_path"].endswith(":GuidedInterventionAgent")
    assert captured["agent_kwargs"]["guidance_task_id"] == "sample-task"
    assert captured["agent_kwargs"]["guidance_base_max"] == 20
