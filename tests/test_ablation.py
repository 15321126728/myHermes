import json
import sys

import pytest

from hermes_agent import experiment
from hermes_agent.ablation import (
    MECHANISM_NAMES,
    AblationConfig,
    standard_ablation_profiles,
)
from hermes_agent.guided_intervention import GuidedInterventionAgent
from hermes_agent.process_guidance import ProcessGuidanceEngine


def test_primary_profiles_are_base_full_and_seven_leave_one_out() -> None:
    profiles = standard_ablation_profiles()
    assert len(profiles) == 9
    assert not any(profiles["base"].as_dict().values())
    assert all(profiles["full"].as_dict().values())
    for mechanism in MECHANISM_NAMES:
        profile = profiles[f"full-minus-{mechanism.replace('_', '-')}"]
        disabled = [name for name, enabled in profile.as_dict().items() if not enabled]
        assert disabled == [mechanism]


def test_base_profile_has_no_guidance_side_effects() -> None:
    config = AblationConfig(**dict.fromkeys(MECHANISM_NAMES, False))
    engine = ProcessGuidanceEngine("", base_max_episodes=3, ablation_config=config)

    guidance = engine.process_episode(
        episode=11,
        commands=["pip install package"],
        terminal_output="invalid format and unable to verify",
        total_episodes=20,
        is_analysis_loop=True,
        is_productive=True,
        agent_response="Task complete!",
    )

    assert guidance == ""
    assert engine.last_feedback_level is None
    assert engine.last_diagnostics["cognitive_errors"] == []
    assert engine.last_diagnostics["diagnosis_layers"] == []
    assert engine.episode_manager._episode_type_history == []


def test_guided_base_profile_disables_all_seven_mechanisms() -> None:
    config = AblationConfig(**dict.fromkeys(MECHANISM_NAMES, False))
    agent = GuidedInterventionAgent(
        model_name="test-model",
        max_episodes=3,
        guidance_task_id="dna-assembly",
        ablation_config=config.as_dict(),
    )

    assert agent._guidance_engine is None
    assert agent._knowledge_file is None
    assert not agent._comprehension_enabled
    assert not agent._ablation_config.runtime_verification
    assert agent._trajectory_records[0]["ablation"] == config.as_dict()


def test_cognitive_only_profile_does_not_emit_ternary_or_layer_feedback() -> None:
    config = AblationConfig(**dict.fromkeys(MECHANISM_NAMES, False))
    config = AblationConfig.from_mapping(
        {**config.as_dict(), "cognitive_detection": True}
    )
    engine = ProcessGuidanceEngine("", ablation_config=config)

    guidance = engine.process_episode(
        0,
        [],
        "invalid csv format",
        20,
    )

    assert "认知提示" in guidance
    assert "RECOVERABLE" not in guidance
    assert engine.last_diagnostics["diagnosis_layers"] == []


def test_experiment_dry_run_writes_paired_manifest(monkeypatch, tmp_path) -> None:
    dataset = tmp_path / "tasks"
    (dataset / "task-a").mkdir(parents=True)
    (dataset / "task-b").mkdir()
    output = tmp_path / "runs"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hermes-ablation",
            "--dataset-path",
            str(dataset),
            "--tasks",
            "task-a",
            "task-b",
            "--profiles",
            "base",
            "full",
            "--seeds",
            "0",
            "1",
            "--output-path",
            str(output),
            "--experiment-id",
            "dry-test",
            "--dry-run",
        ],
    )

    experiment.main()

    manifest = json.loads(
        (output / "experiments" / "dry-test" / "manifest.json").read_text()
    )
    assert len(manifest["trials"]) == 8
    assert manifest["profiles"]["base"] == dict.fromkeys(MECHANISM_NAMES, False)
    assert all(manifest["profiles"]["full"].values())


def test_trajectory_metrics_count_mechanism_events(tmp_path) -> None:
    path = tmp_path / "trajectory.json"
    path.write_text(
        json.dumps(
            [
                {
                    "record_type": "run_config",
                    "effective_episode_limit": 25,
                    "extensions_granted": 1,
                },
                {
                    "episode": 0,
                    "intervention_type": "process_guidance",
                    "diagnostics": {
                        "cognitive_errors": ["format_misunderstanding"],
                        "diagnosis_layers": ["validation"],
                        "feedback_level": "RECOVERABLE",
                    },
                },
                {
                    "episode": 1,
                    "intervention_type": "knowledge_hint",
                    "completion_rejected": True,
                },
            ]
        )
    )

    metrics = experiment._trajectory_metrics(path)

    assert metrics["episodes"] == 2
    assert metrics["extensions_granted"] == 1
    assert metrics["cognitive_errors"] == 1
    assert metrics["diagnosis_layers"] == 1
    assert metrics["recoverable_feedback"] == 1
    assert metrics["knowledge_hints"] == 1
    assert metrics["completion_rejections"] == 1


def test_paired_statistics_and_holm_correction() -> None:
    paired = [
        ({"resolved": True}, {"resolved": False}),
        ({"resolved": True}, {"resolved": True}),
        ({"resolved": False}, {"resolved": False}),
    ]
    interval = experiment._paired_bootstrap_ci(paired, samples=1000)
    comparisons = {
        "base": {"mcnemar_p_value": 0.01},
        "full-minus-a": {"mcnemar_p_value": 0.01},
        "full-minus-b": {"mcnemar_p_value": 0.04},
    }

    experiment._apply_holm_correction(comparisons)

    assert interval is not None
    assert interval[0] <= 1 / 3 <= interval[1]
    assert experiment._mcnemar_exact_p_value(1, 0) == 1.0
    assert "holm_adjusted_p_value" not in comparisons["base"]
    assert comparisons["full-minus-a"]["holm_adjusted_p_value"] == 0.02
    assert comparisons["full-minus-b"]["holm_adjusted_p_value"] == 0.04


def test_failed_auth_preflight_marks_manifest_blocked(monkeypatch, tmp_path) -> None:
    dataset = tmp_path / "tasks"
    (dataset / "task-a").mkdir(parents=True)
    output = tmp_path / "runs"
    monkeypatch.setattr(
        experiment,
        "_auth_preflight",
        lambda _api_base, _model: (
            False,
            "credential_preflight_failed",
            None,
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "hermes-ablation",
            "--dataset-path",
            str(dataset),
            "--tasks",
            "task-a",
            "--profiles",
            "full",
            "--seeds",
            "0",
            "--output-path",
            str(output),
            "--experiment-id",
            "blocked-test",
        ],
    )

    with pytest.raises(SystemExit):
        experiment.main()

    manifest = json.loads(
        (output / "experiments" / "blocked-test" / "manifest.json").read_text()
    )
    assert manifest["status"] == "blocked"
    assert manifest["blocked_reason"] == "credential_preflight_failed"
