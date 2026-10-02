"""Pattern 3: Parallel Fan-Out / Gather ("Octopus").

              ┌─▶ policy_reviewer ────────┐
    START ────┼─▶ accessibility_reviewer ─┼─▶ synthesizer ─▶ END
              └─▶ tone_reviewer ──────────┘

Several agents review the same draft at the same time; a synthesizer merges
their feedback. LangGraph runs nodes in the same "superstep" concurrently.
`reviews` uses a reducer (operator.add) so parallel writes are appended, not overwritten.
Best for: speed, diverse perspectives, code/document review.

    python -m part2_multi_agent.patterns.parallel
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from part2_multi_agent.patterns.common import ask_llm, run_demo

DRAFT_NOTICE = """Notice: The SMG grant is disbursed subject to means-testing per capita inclusive of all
co-residing household members, contingent upon therapist certification. Apply via the portal.
Non-compliance with documentary requirements will result in rejection."""

REVIEWERS = {
    "policy_reviewer": "Check the notice against policy: SMG is for age 60+, per-capita income <= $1,500, "
                       "up to $2,000 every 5 years, needs a home assessment. List factual gaps or errors.",
    "accessibility_reviewer": "Review for plain language (reading age ~12), jargon and sentence length. List fixes.",
    "tone_reviewer": "Review tone for a citizen audience: respectful, reassuring, not threatening. List fixes.",
}


class ReviewState(TypedDict, total=False):
    draft: str
    reviews: Annotated[list[str], operator.add]
    final: str


def make_reviewer(name: str):
    def review(state: ReviewState, config: RunnableConfig) -> dict:
        return {"reviews": [f"### {name}\n" + ask_llm(name, REVIEWERS[name], state["draft"], config)]}
    return review


def synthesizer(state: ReviewState, config: RunnableConfig) -> dict:
    final = ask_llm(
        "synthesizer",
        "Rewrite the notice applying ALL reviewer feedback. Output only the improved notice (max 120 words).",
        f"DRAFT:\n{state['draft']}\n\nREVIEWS:\n" + "\n\n".join(state["reviews"]),
        config,
    )
    return {"final": final}


def build_graph():
    g = StateGraph(ReviewState)
    for name in REVIEWERS:
        g.add_node(name, make_reviewer(name))
        g.add_edge(START, name)          # fan-out
        g.add_edge(name, "synthesizer")  # gather (waits for all three)
    g.add_node("synthesizer", synthesizer)
    g.add_edge("synthesizer", END)
    return g.compile(name="parallel_fan_out")


def main() -> None:
    result = run_demo("parallel", build_graph(), {"draft": DRAFT_NOTICE}, "final")
    print(f"\n{len(result['reviews'])} reviews gathered.")


if __name__ == "__main__":
    main()
