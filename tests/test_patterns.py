import pytest

from lab_2_multi_agent.patterns import (
    pattern_1_sequential_pipeline,
    pattern_2_orchestrator,
    pattern_3_parallel_fan_out_gather,
    pattern_4_hierarchical_decomposition,
    pattern_5_generator_critic,
)


def test_sequential():
    out = pattern_1_sequential_pipeline.build_graph().invoke({"enquiry": pattern_1_sequential_pipeline.ENQUIRY})
    assert out["facts"] and out["policy"] and out["reply"]


def test_parallel_gathers_all_reviews():
    out = pattern_3_parallel_fan_out_gather.build_graph().invoke({"draft": pattern_3_parallel_fan_out_gather.DRAFT_NOTICE})
    assert len(out["reviews"]) == len(pattern_3_parallel_fan_out_gather.REVIEWERS) and out["final"]


def test_hierarchical_fans_out_per_subtask():
    out = pattern_4_hierarchical_decomposition.build_graph().invoke({"goal": pattern_4_hierarchical_decomposition.GOAL})
    assert len(out["findings"]) == len(out["subtasks"]) >= 2


def test_generator_critic_loops_until_approved():
    out = pattern_5_generator_critic.build_graph().invoke({"task": pattern_5_generator_critic.TASK})
    assert out["approved"] and out["round"] == 2


@pytest.mark.parametrize("text,desk", [
    ("I want to reschedule my appointment", "appointments_desk"),
    ("I am unhappy and want to make a complaint", "complaints_desk"),
])
def test_orchestrator_routes(text, desk):
    assert pattern_2_orchestrator.build_graph().invoke({"enquiry": text})["desk"] == desk

