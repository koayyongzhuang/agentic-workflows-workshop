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

from dataclasses import dataclass
from typing import Literal, Optional

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import BaseTool
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from lab_1_single_agent.extra_tools import EXTRA_TOOLS
from lab_1_single_agent.prompts import PROMPTS, ROLES
from workshop.llm import get_chat_model
from workshop.tools import ALL_TOOLS


class AgentState(MessagesState):
    """Conversation messages. Add fields here to track more state (exercise idea)."""


# Settings you can change per run. In LangGraph Studio each assistant stores its own values
# (make studio creates one per prompt and role), so the exercises switch prompt and role without a terminal.
# The choices come from prompts.py: add a role there and it appears here.
RoleName = Literal[tuple(ROLES)]  # type: ignore[valid-type]
PromptName = Literal[tuple(PROMPTS)]  # type: ignore[valid-type]


@dataclass
class AgentSettings:
    """Which role (prompt + tools) the agent plays, and optionally a different system prompt."""

    role: RoleName = "helpdesk"
    prompt: Optional[PromptName] = None


def tool_rounds_this_turn(messages) -> int:
    """How many tool calls happened since the user's latest message."""
    n = 0
    for m in reversed(messages):
        if isinstance(m, HumanMessage):
            break
        if isinstance(m, ToolMessage):
            n += 1
    return n


def plain_text(msg: AIMessage) -> AIMessage:
    """Make a final answer's content a plain string.

    Some models (OpenAI via the Responses API, Anthropic, ...) return content as a list of
    blocks, e.g. [{"type": "text", "text": "..."}]. Studio's Chat view, run.py and the
    multi-agent code expect a string, so a list can show up as an empty reply.
    Messages with tool calls are left alone: providers may need their reasoning blocks back.
    """
    if isinstance(msg, AIMessage) and not msg.tool_calls and isinstance(msg.content, list):
        return msg.model_copy(update={"content": str(msg.text)})
    return msg


def build_single_agent(
    role: str = "helpdesk",
    tools: list[BaseTool] | None = None,
    system_prompt: str | None = None,
    model: str | None = None,
    checkpointer=None,
    max_tool_calls: int = 6,
    switchable: bool = False,
):
    """Build the agent.

    role / system_prompt fix the behaviour at build time (command line, tests).
    switchable=True lets each run pick its role and prompt through AgentSettings
    (how LangGraph Studio runs it): every tool can then be executed, but the model is
    only ever offered the tools of the selected role.
    """
    registry = {**ALL_TOOLS, **EXTRA_TOOLS}
    fixed_tools = tools

    def tools_for(r: str) -> list[BaseTool]:
        return fixed_tools if fixed_tools is not None else [registry[name] for name in ROLES[r]["tools"]]

    def prompt_for(r: str, prompt_name: str | None) -> str:
        if prompt_name:
            return PROMPTS[prompt_name]
        if r == role and system_prompt:
            return system_prompt
        return PROMPTS[ROLES[r]["prompt"]]

    base_llm = get_chat_model(model, role="single_agent")
    bound: dict[str, object] = {}  # role -> model with that role's tools bound

    def llm_for(r: str):
        if r not in bound:
            ts = tools_for(r)
            bound[r] = base_llm.bind_tools(ts) if ts else base_llm
        return bound[r]

    # ---- node 1: reason (tool SELECTION + result PROCESSING) -------------------
    def reason(state: AgentState, runtime: Runtime[AgentSettings]) -> dict:
        settings = runtime.context if switchable else None
        r = settings.role if settings else role
        prompt = prompt_for(r, settings.prompt if settings else None)
        messages = [SystemMessage(prompt), *state["messages"]]
        if tool_rounds_this_turn(state["messages"]) >= max_tool_calls:
            # Safety valve against tool loops: force a final answer without tools.
            messages.append(SystemMessage("Tool budget reached. Answer now with what you have."))
            return {"messages": [plain_text(base_llm.invoke(messages))]}
        return {"messages": [plain_text(llm_for(r).invoke(messages))]}

    # ---- node 2: act (tool INVOCATION) -------------------------------------------
    # handle_tool_errors=True turns exceptions into a ToolMessage the LLM can read and recover from.
    act_tools = list(registry.values()) if (switchable and fixed_tools is None) else tools_for(role)
    act = ToolNode(act_tools, handle_tool_errors=True)

    # ---- edge: did the LLM ask for tools? -------------------------------------------
    def route(state: AgentState) -> Literal["act", "__end__"]:
        last = state["messages"][-1]
        return "act" if isinstance(last, AIMessage) and last.tool_calls else END

    graph = StateGraph(AgentState, context_schema=AgentSettings)
    graph.add_node("reason", reason)
    graph.add_node("act", act)
    graph.add_edge(START, "reason")
    graph.add_conditional_edges("reason", route, ["act", END])
    graph.add_edge("act", "reason")
    return graph.compile(checkpointer=checkpointer, name=f"single_agent:{role}")


def make_graph(config=None):
    """Factory used by LangGraph Studio (see langgraph.json).

    `make studio` also creates one Studio assistant per prompt and role in prompts.py
    (scripts/studio_assistants.py); pick one from Studio's assistant menu.
    """
    return build_single_agent(switchable=True)
