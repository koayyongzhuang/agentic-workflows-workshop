"""Pattern 4: Hierarchical Decomposition ("Russian Doll").

    planner ──Send()──▶ worker (×N, each is itself a small graph) ──▶ aggregator ─▶ END
                          └─ research ─▶ summarise ─┘

A high-level agent breaks a goal into sub-tasks and delegates each to a
sub-agent. Here each worker is a compiled sub-graph (a graph inside a graph),
and `Send` fans out one worker per sub-task, however many the planner creates.
Best for: complex, multi-step tasks, and keeping each context window small.

    python -m part2_multi_agent.patterns.hierarchical
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from part2_multi_agent.patterns.common import ask_llm, run_demo
from workshop.llm import get_chat_model
from workshop.rag.ingest import format_hits, retrieve

GOAL = ("Prepare a one-page briefing for a community centre volunteer on ALL support a 70-year-old "
        "resident living alone on $1,200 a month could get, and how to apply for each.")


class Plan(BaseModel):
    subtasks: list[str] = Field(description="2-4 independent research sub-tasks, one per scheme or topic")

    @classmethod
    def mock_response(cls, text: str) -> "Plan":  # used only by the offline mock model
        return cls(subtasks=[
            "Senior Mobility Grant: eligibility and how to apply",
            "Household Energy Rebate: eligibility and rebate amount",
            "How to apply and book appointments",
        ])


# ---- worker sub-graph (the inner doll) ---------------------------------------------------
class WorkerState(TypedDict, total=False):
    subtask: str
    notes: str
    findings: Annotated[list[str], operator.add]


def research(state: WorkerState, config: RunnableConfig) -> dict:
    return {"notes": format_hits(retrieve(state["subtask"], k=2))}


def summarise(state: WorkerState, config: RunnableConfig) -> dict:
    text = ask_llm("worker", "Summarise the extracts for the sub-task in 3 bullets with [source].",
                   f"SUB-TASK: {state['subtask']}\n\nEXTRACTS:\n{state['notes']}", config)
    return {"findings": [f"#### {state['subtask']}\n{text}"]}


def build_worker():
    w = StateGraph(WorkerState)
    w.add_node("research", research)
    w.add_node("summarise", summarise)
    w.add_edge(START, "research")
    w.add_edge("research", "summarise")
    w.add_edge("summarise", END)
    return w.compile(name="worker")


# ---- manager graph (the outer doll) -----------------------------------------------------
class ManagerState(TypedDict, total=False):
    goal: str
    subtasks: list[str]
    findings: Annotated[list[str], operator.add]
    briefing: str


def planner(state: ManagerState, config: RunnableConfig) -> dict:
    llm = get_chat_model(role="planner").with_structured_output(Plan)
    plan = llm.invoke([SystemMessage("Break the goal into independent research sub-tasks."), HumanMessage(state["goal"])], config)
    return {"subtasks": plan.subtasks[:4]}


def delegate(state: ManagerState):
    return [Send("worker", {"subtask": t}) for t in state["subtasks"]]


def aggregator(state: ManagerState, config: RunnableConfig) -> dict:
    briefing = ask_llm("aggregator", "Combine the findings into a clear one-page briefing with headings per scheme.",
                       f"GOAL: {state['goal']}\n\nFINDINGS:\n" + "\n\n".join(state["findings"]), config)
    return {"briefing": briefing}


def build_graph():
    g = StateGraph(ManagerState)
    g.add_node("planner", planner)
    g.add_node("worker", build_worker())  # a compiled graph used as a node
    g.add_node("aggregator", aggregator)
    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", delegate, ["worker"])
    g.add_edge("worker", "aggregator")
    g.add_edge("aggregator", END)
    return g.compile(name="hierarchical_decomposition")


def main() -> None:
    result = run_demo("hierarchical", build_graph(), {"goal": GOAL}, "briefing")
    print(f"\nPlanner created {len(result['subtasks'])} sub-tasks; {len(result['findings'])} workers reported.")


if __name__ == "__main__":
    main()
