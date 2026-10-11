"""Lab 3: the Deep Agent is wired as the guide describes (runs offline with MODEL=mock)."""

from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver

from lab_3_deep_agent.agent import AGENCY_DIR, ELIGIBILITY_RESEARCHER, INTERRUPT_ON, MAIN_TOOLS, build_deep_agent


def _tool_names(agent) -> set[str]:
    return set(agent.get_graph().nodes["tools"].data.tools_by_name)


def test_harness_adds_its_own_tools():
    names = _tool_names(build_deep_agent())
    assert {"write_todos", "write_file", "read_file", "task"} <= names   # given by the harness
    assert set(MAIN_TOOLS) <= names                                        # given by us


def test_researcher_is_narrow_and_booking_needs_approval():
    researcher_tools = {t.name for t in ELIGIBILITY_RESEARCHER["tools"]}
    assert "book_appointment" not in researcher_tools and "check_eligibility" in researcher_tools
    assert INTERRUPT_ON.get("book_appointment") is True


def test_runs_offline():
    agent = build_deep_agent(checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "t-deep"}, "recursion_limit": 60}
    out = agent.invoke({"messages": [HumanMessage("What schemes are available?")]}, cfg)
    assert out["messages"][-1].content


def test_house_rules_and_skill_are_on_disk():
    assert "per-capita" in (AGENCY_DIR / "AGENTS.md").read_text()
    skill = (AGENCY_DIR / "skills" / "case-file-format" / "SKILL.md").read_text()
    assert skill.startswith("---\nname: case-file-format")
