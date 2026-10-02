"""Pattern 5: Generator & Critic ("Editor's Desk").

    generator ──▶ critic ──approved?──▶ END
        ▲            │ no (and iterations left)
        └────────────┘

One agent writes, another checks against explicit criteria and sends it back
with feedback until it passes (or a maximum number of rounds is reached).
Best for: quality assurance, code generation, compliance review.

    python -m part2_multi_agent.patterns.generator_critic
"""

from __future__ import annotations

import re
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from part2_multi_agent.patterns.common import ask_llm, run_demo
from workshop.llm import get_chat_model

MAX_ROUNDS = 3
TASK = "Write an SMS (max 300 characters) reminding a senior of their home mobility assessment tomorrow at 10:00."
CRITERIA = """1. At most 300 characters.
2. States date/time and what the visit is for.
3. Tells them how to reschedule.
4. Contains NO personal identifiers (no ID numbers, no full names).
5. Warm, plain language."""


class Critique(BaseModel):
    approved: bool = Field(description="True only if ALL criteria are met")
    feedback: str = Field(description="Specific, actionable fixes if not approved")

    @classmethod
    def mock_response(cls, text: str) -> "Critique":  # offline mock: approve on round 2
        m = re.search(r"Round:\s*(\d+)", text)
        rnd = int(m.group(1)) if m else 1
        return cls(approved=rnd >= 2, feedback="" if rnd >= 2 else "Add how to reschedule; keep under 300 characters.")


class GCState(TypedDict, total=False):
    task: str
    draft: str
    feedback: str
    approved: bool
    round: int
    history: list[str]


def generator(state: GCState, config: RunnableConfig) -> dict:
    rnd = state.get("round", 0) + 1
    prompt = state["task"] + (f"\n\nRevise your previous draft using this feedback:\n{state['feedback']}\n\nPrevious draft:\n{state['draft']}"
                              if state.get("feedback") else "")
    draft = ask_llm("generator", "You write concise public-service messages.", prompt, config)
    return {"draft": draft, "round": rnd, "history": [*state.get("history", []), f"Round {rnd} draft: {draft}"]}


def critic(state: GCState, config: RunnableConfig) -> dict:
    llm = get_chat_model(role="critic").with_structured_output(Critique)
    c = llm.invoke([
        SystemMessage(f"You are a strict compliance editor. Criteria:\n{CRITERIA}"),
        HumanMessage(f"Round: {state['round']}\nDraft ({len(state['draft'])} chars):\n{state['draft']}"),
    ], config)
    return {"approved": c.approved, "feedback": c.feedback,
            "history": [*state.get("history", []), f"Round {state['round']} critique: {'APPROVED' if c.approved else c.feedback}"]}


def loop_or_stop(state: GCState) -> Literal["generator", "__end__"]:
    return END if state["approved"] or state["round"] >= MAX_ROUNDS else "generator"


def build_graph():
    g = StateGraph(GCState)
    g.add_node("generator", generator)
    g.add_node("critic", critic)
    g.add_edge(START, "generator")
    g.add_edge("generator", "critic")
    g.add_conditional_edges("critic", loop_or_stop, ["generator", END])
    return g.compile(name="generator_critic")


def main() -> None:
    result = run_demo("generator_critic", build_graph(), {"task": TASK}, "draft")
    print("\n".join(result["history"]))


if __name__ == "__main__":
    main()
