import pytest
from langchain_core.messages import HumanMessage

from part2_multi_agent.patterns import coordinator, generator_critic, hierarchical, parallel, sequential, supervisor_travel


def test_sequential():
    out = sequential.build_graph().invoke({"enquiry": sequential.ENQUIRY})
    assert out["facts"] and out["policy"] and out["reply"]


def test_parallel_gathers_all_reviews():
    out = parallel.build_graph().invoke({"draft": parallel.DRAFT_NOTICE})
    assert len(out["reviews"]) == len(parallel.REVIEWERS) and out["final"]


def test_hierarchical_fans_out_per_subtask():
    out = hierarchical.build_graph().invoke({"goal": hierarchical.GOAL})
    assert len(out["findings"]) == len(out["subtasks"]) >= 2


def test_generator_critic_loops_until_approved():
    out = generator_critic.build_graph().invoke({"task": generator_critic.TASK})
    assert out["approved"] and out["round"] == 2


@pytest.mark.parametrize("text,desk", [
    ("I want to reschedule my appointment", "appointments_desk"),
    ("I am unhappy and want to make a complaint", "complaints_desk"),
])
def test_coordinator_routes(text, desk):
    assert coordinator.build_graph().invoke({"enquiry": text})["desk"] == desk


def test_travel_supervisor():
    out = supervisor_travel.build_graph().invoke(
        {"messages": [HumanMessage("Change my flight BK-1001 to 2026-12-20 and suggest hotels in Tokyo.")]}
    )
    assert out["done"] == ["flight_agent", "hotel_agent"]
    assert "2026-12-20" in out["reports"] and "Tokyo" in out["reports"]
