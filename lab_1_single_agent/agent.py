"""A single tool-using agent, built by hand with LangGraph.

    ┌─────────┐   tool calls?   ┌───────┐
    │ reason  │ ──── yes ─────▶ │  act  │
    │  (LLM)  │ ◀── results ─── │(tools)│
    └────┬────┘                 └───────┘
         │ no: final answer
         ▼
        END

Mapping to the "Single Agent Architecture" slide:
  * LLM core   -> the `reason` node (decides: answer, or which tool to call)
  * Tools      -> the `act` node (a ToolNode that executes the chosen calls)
  * Memory     -> the checkpointer (per-thread conversation) + remember/recall tools
  * State      -> `AgentState` (messages + bookkeeping), saved after every step
  * Tool Selection → Tool Invocation → Result Processing = reason → act → reason
"""

from __future__ import annotations

from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from lab_1_single_agent.extra_tools import EXTRA_TOOLS
from lab_1_single_agent.prompts import PROMPTS, ROLES
from workshop.llm import get_chat_model
from workshop.tools import ALL_TOOLS


class AgentState(MessagesState):
    """Conversation messages. Add fields here to track more state (exercise idea)."""


def tool_rounds_this_turn(messages) -> int:
    """How many tool calls happened since the user's latest message."""
    n = 0
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            break
        if isinstance(m, ToolMessage):
            n += 1
    return n


def build_single_agent(
    role: str = "helpdesk",
    tools: list[BaseTool] | None = None,
    system_prompt: str | None = None,
    model: str | None = None,
    checkpointer=None,
    max_tool_calls: int = 6,
):
    spec = ROLES[role]
    registry = {**ALL_TOOLS, **EXTRA_TOOLS}
    tools = tools if tools is not None else [registry[name] for name in spec["tools"]]
    prompt = system_prompt or PROMPTS[spec["prompt"]]

    base_llm = get_chat_model(model, role="single_agent")
    llm_with_tools = base_llm.bind_tools(tools) if tools else base_llm

    # ---- node 1: reason (tool SELECTION + result PROCESSING) -------------------
    def reason(state: AgentState) -> dict:
        messages = [SystemMessage(prompt), *state["messages"]]
        if tool_rounds_this_turn(state["messages"]) >= max_tool_calls:
            # Safety valve against tool loops: force a final answer without tools.
            messages.append(SystemMessage("Tool budget reached. Answer now with what you have."))
            return {"messages": [base_llm.invoke(messages)]}
        return {"messages": [llm_with_tools.invoke(messages)]}

    # ---- node 2: act (tool INVOCATION) -------------------------------------------
    # handle_tool_errors=True turns exceptions into a ToolMessage the LLM can read and recover from.
    act = ToolNode(tools, handle_tool_errors=True)

    # ---- edge: did the LLM ask for tools? -------------------------------------------
    def route(state: AgentState) -> Literal["act", "__end__"]:
        last = state["messages"][-1]
        return "act" if isinstance(last, AIMessage) and last.tool_calls else END

    graph = StateGraph(AgentState)
    graph.add_node("reason", reason)
    graph.add_node("act", act)
    graph.add_edge(START, "reason")
    graph.add_conditional_edges("reason", route, ["act", END])
    graph.add_edge("act", "reason")
    return graph.compile(checkpointer=checkpointer, name=f"single_agent:{role}")


def make_graph(config=None):
    """Factory used by LangGraph Studio (see langgraph.json)."""
    return build_single_agent()
