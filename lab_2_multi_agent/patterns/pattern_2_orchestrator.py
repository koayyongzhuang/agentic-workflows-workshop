"""Pattern 2: Orchestrator ("Concierge"). Anthropic and LangGraph call this pattern routing.

                 ┌─▶ schemes_desk ──────┐
   orchestrator ─┼─▶ appointments_desk ─┼─▶ END
                 ├─▶ complaints_desk ───┤
                 └─▶ general_desk ──────┘

A central agent classifies intent and hands the request to ONE specialist.
Best for: customer service, task routing.

    python -m lab_2_multi_agent.patterns.pattern_2_orchestrator
    python -m lab_2_multi_agent.patterns.pattern_2_orchestrator "I want to reschedule my appointment"
"""

from __future__ import annotations

import sys
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from lab_2_multi_agent.patterns.common import ENQUIRY, ask_llm, run_demo
from workshop.llm import get_chat_model

Desk = Literal["schemes_desk", "appointments_desk", "complaints_desk", "general_desk"]


class Intent(BaseModel):
    desk: Desk = Field(description="schemes_desk: grants/eligibility; appointments_desk: booking/rescheduling; "
                                   "complaints_desk: unhappy with a decision or service; general_desk: anything else")
    confidence: float = Field(description="0.0 to 1.0")


class OrchestratorInput(TypedDict):
    """What Studio asks you for. The other state fields are written by the nodes."""
    enquiry: str


class OrchestratorState(TypedDict, total=False):
    enquiry: str
    desk: str
    reply: str


DESK_PROMPTS = {
    "schemes_desk": "You explain support schemes and likely eligibility. Be specific and list next steps.",
    "appointments_desk": "You handle appointment booking and rescheduling. Ask for the reference if needed.",
    "complaints_desk": "You acknowledge the concern with empathy, explain the appeal process and escalate to an officer.",
    "general_desk": "You answer general questions briefly and point to the right service.",
}


def orchestrator(state: OrchestratorState, config: RunnableConfig) -> dict:
    router = get_chat_model(role="orchestrator").with_structured_output(Intent)
    intent = router.invoke([SystemMessage("Classify the citizen's enquiry to the right desk."),
                            HumanMessage(state["enquiry"])], config)
    return {"desk": intent.desk}


def make_desk(name: str):
    def desk(state: OrchestratorState, config: RunnableConfig) -> dict:
        return {"reply": f"**[{name}]** " + ask_llm(name, DESK_PROMPTS[name], state["enquiry"], config)}
    return desk


def build_graph():
    g = StateGraph(OrchestratorState, input_schema=OrchestratorInput)
    g.add_node("orchestrator", orchestrator)
    for name in DESK_PROMPTS:
        g.add_node(name, make_desk(name))
        g.add_edge(name, END)
    g.add_edge(START, "orchestrator")
    g.add_conditional_edges("orchestrator", lambda s: s["desk"], list(DESK_PROMPTS))
    return g.compile(name="pattern_2_orchestrator")


def main() -> None:
    enquiry = " ".join(sys.argv[1:]) or ENQUIRY
    run_demo("pattern_2_orchestrator", build_graph(), {"enquiry": enquiry}, "reply")


if __name__ == "__main__":
    main()
