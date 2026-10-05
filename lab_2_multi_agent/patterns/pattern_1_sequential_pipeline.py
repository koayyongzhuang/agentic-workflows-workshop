"""Pattern 1: Sequential Pipeline ("Assembly Line").

    intake ──▶ researcher ──▶ drafter ──▶ END

Each agent passes its output to the next. Deterministic order, easy to debug:
if the answer is wrong you can inspect every intermediate field in the state.
Best for: data processing pipelines, sequential workflows.

    python -m lab_2_multi_agent.patterns.pattern_1_sequential_pipeline
"""

from __future__ import annotations

from typing import TypedDict

from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph

from lab_2_multi_agent.patterns.common import ENQUIRY, ask_llm, run_demo
from workshop.rag.ingest import format_hits, retrieve


class PipelineState(TypedDict, total=False):
    enquiry: str
    facts: str       # written by intake
    policy: str      # written by researcher
    reply: str       # written by drafter


def intake(state: PipelineState, config: RunnableConfig) -> dict:
    facts = ask_llm("intake", "Extract the applicant facts as bullets: age, household size, monthly household "
                    "income, per-capita income, need. Write 'unknown' for anything missing.", state["enquiry"], config)
    return {"facts": facts}


def researcher(state: PipelineState, config: RunnableConfig) -> dict:
    hits = retrieve(state["enquiry"], k=3)  # deterministic RAG step (no LLM needed)
    return {"policy": format_hits(hits)}


def drafter(state: PipelineState, config: RunnableConfig) -> dict:
    reply = ask_llm(
        "drafter",
        "Draft a short, friendly reply to the citizen using ONLY the facts and policy extracts. "
        "Include the likely scheme, whether they seem to qualify (show per-capita income), and next steps. Cite [source].",
        f"FACTS:\n{state['facts']}\n\nPOLICY:\n{state['policy']}",
        config,
    )
    return {"reply": reply}


def build_graph():
    g = StateGraph(PipelineState)
    g.add_node("intake", intake)
    g.add_node("researcher", researcher)
    g.add_node("drafter", drafter)
    g.add_edge(START, "intake")
    g.add_edge("intake", "researcher")
    g.add_edge("researcher", "drafter")
    g.add_edge("drafter", END)
    return g.compile(name="pattern_1_sequential_pipeline")


def main() -> None:
    run_demo("pattern_1_sequential_pipeline", build_graph(), {"enquiry": ENQUIRY}, "reply")


if __name__ == "__main__":
    main()
