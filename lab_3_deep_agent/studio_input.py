"""Give Lab 3's Studio graph a single text box, like the Lab 2 patterns.

`create_deep_agent` asks for a list of messages, so Studio's input form shows a message
editor where you click "+ Message" before typing. For Studio only (make_graph), the deep
agent runs inside a two-step graph:

    ask ──▶ lab_3_deep_agent ──▶ END
    (your text becomes a HumanMessage)   (the unchanged deep agent; expand it in Studio)

The terminal chat (`make deep`) and the tests use the deep agent directly with
{"messages": [...]}.
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph


class StudioInput(TypedDict):
    """What Studio asks you for: type your request into `message`."""

    message: str


def with_text_input(agent):
    """Wrap a compiled agent so Studio shows one `message` text box instead of a message list."""

    def ask(state: StudioInput) -> dict:
        return {"messages": [HumanMessage(state["message"])]}

    # Same state as the agent (messages, todos, files), so Studio still shows them; `message` stays out of the output.
    g = StateGraph(agent.builder.state_schema, input_schema=StudioInput, output_schema=agent.builder.output_schema)
    g.add_node("ask", ask)
    g.add_node(agent.name, agent)
    g.add_edge(START, "ask")
    g.add_edge("ask", agent.name)
    g.add_edge(agent.name, END)
    return g.compile(name=agent.name)
