from hermes_agent.guided_intervention import GuidedInterventionAgent
from hermes_agent.intervened_terminus import IntervenedTerminusAgent
from hermes_agent.replayable_hermes import ReplayableHermesAgent
from hermes_agent.terminus import Terminus2


def test_agent_hierarchy() -> None:
    assert issubclass(ReplayableHermesAgent, Terminus2)
    assert issubclass(IntervenedTerminusAgent, ReplayableHermesAgent)
    assert issubclass(GuidedInterventionAgent, IntervenedTerminusAgent)


def test_intervened_agent_constructs() -> None:
    agent = IntervenedTerminusAgent(
        model_name="test-model",
        max_episodes=2,
        intervention_schedule=[
            {"episode": 1, "mode": "inject", "payload": "check progress"}
        ],
    )
    assert len(agent._intervention_schedule) == 1
