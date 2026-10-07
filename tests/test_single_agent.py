from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from lab_1_single_agent.agent import build_single_agent
from tests.conftest import ELIGIBLE_SMG


def test_agent_uses_tool_and_answers():
    agent = build_single_agent()
    out = agent.invoke({"messages": [HumanMessage(ELIGIBLE_SMG)]})
    tool_msgs = [m for m in out["messages"] if isinstance(m, ToolMessage)]
    assert tool_msgs and tool_msgs[0].name == "check_eligibility"
    assert '"eligible": true' in tool_msgs[0].content
    assert out["messages"][-1].content  # final answer produced


def test_role_limits_tools():
    agent = build_single_agent(role="policy_researcher")
    tools = agent.get_graph().nodes["act"].data.tools_by_name
    assert set(tools) == {"search_knowledge_base", "list_schemes", "get_scheme_details"}


def test_short_term_memory_per_thread():
    agent = build_single_agent(checkpointer=InMemorySaver())
    cfg = {"configurable": {"thread_id": "t-mem"}}
    agent.invoke({"messages": [HumanMessage("What schemes are available?")]}, cfg)
    agent.invoke({"messages": [HumanMessage("thanks")]}, cfg)
    history = agent.get_state(cfg).values["messages"]
    assert sum(isinstance(m, HumanMessage) for m in history) == 2


def test_long_term_memory_tools():
    from workshop.tools import recall_facts, remember_fact
    cfg = {"configurable": {"user_id": "pytest-user"}}
    remember_fact.invoke({"fact": "lives with spouse, household of 2, NRIC S1234567D"}, config=cfg)
    recalled = recall_facts.invoke({"query": "household"}, config=cfg)
    assert "household of 2" in recalled and "S1234567D" not in recalled


def test_studio_graph_switches_role_per_run():
    """Studio passes AgentSettings as run context: the same graph can play any role."""
    from lab_1_single_agent.agent import make_graph
    from lab_1_single_agent.prompts import ROLES

    graph = make_graph()
    schema = graph.get_context_jsonschema()["properties"]
    assert set(schema["role"]["enum"]) == set(ROLES)  # shown as a dropdown in Studio

    def tools_used(role):
        out = graph.invoke({"messages": [HumanMessage(ELIGIBLE_SMG)]}, context={"role": role})
        return {m.name for m in out["messages"] if isinstance(m, ToolMessage)}

    assert "check_eligibility" in tools_used("eligibility_checker")
    assert tools_used("policy_researcher") <= set(ROLES["policy_researcher"]["tools"])
