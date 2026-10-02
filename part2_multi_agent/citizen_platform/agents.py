"""The three specialists and the supervisor of the Citizen Services Platform.

    Retrieval Agent   RAG-based knowledge      search_knowledge_base, list_schemes, get_scheme_details
    Validation Agent  policy compliance        check_eligibility, get_scheme_details, calculator
    Action Agent      API integration          get_appointment_slots, book_appointment,
                                               submit_application, check_application_status

Each one sees only its own tools (separation of responsibilities).
EXERCISE "Add more agents": copy one Specialist, give it a prompt + tools,
register it in AGENTS, allow its tools in workshop/guardrails/tool_policy.py.
"""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field

from workshop.agents import Specialist
from workshop.tools import ALL_TOOLS

T = ALL_TOOLS

RETRIEVAL_AGENT = Specialist(
    name="retrieval_agent",
    system_prompt="""You are the Retrieval Agent. You answer policy questions using ONLY the knowledge base.
Search, then report the relevant facts in 3-6 bullets, each ending with its [source].
If the knowledge base does not cover the question, say so plainly. Do not check eligibility or take actions.""",
    tools=[T["search_knowledge_base"], T["list_schemes"], T["get_scheme_details"]],
)

VALIDATION_AGENT = Specialist(
    name="validation_agent",
    system_prompt="""You are the Validation Agent. You check eligibility and data quality against policy.
1. Identify the scheme and the applicant facts: age, monthly household income, household size, residency.
2. If a required fact is missing, report exactly what is missing. Do not guess.
3. Otherwise call check_eligibility and report: ELIGIBLE or NOT ELIGIBLE, the per-capita income, and the reasons.
Never take actions such as booking or submitting.""",
    tools=[T["check_eligibility"], T["get_scheme_details"], T["calculator"]],
)

ACTION_AGENT = Specialist(
    name="action_agent",
    system_prompt="""You are the Action Agent. You carry out actions in the government service API:
list or book appointments, submit applications, check application status.
Only act on what the user asked for. If a tool says an action is blocked by policy or waiting
for approval, report that clearly and do not retry. Report references (APT-..., APP-...) exactly.""",
    tools=[T["get_appointment_slots"], T["book_appointment"], T["submit_application"], T["check_application_status"]],
)

AGENTS: dict[str, Specialist] = {a.name: a for a in (RETRIEVAL_AGENT, VALIDATION_AGENT, ACTION_AGENT)}


# ----------------------------------------------------------------------------- supervisor
SUPERVISOR_PROMPT = """You are the Supervisor of a citizen services platform. You route work to specialists
and decide when the user's request is fully handled.

Specialists:
- retrieval_agent: explains schemes, rules, benefits, documents, processes (knowledge base).
- validation_agent: checks eligibility for a specific scheme from the applicant's facts.
- action_agent: books appointments, submits applications, checks application status.

Rules:
- Consult each specialist at most once per user message; never repeat one that already reported.
- Booking or submitting requires the scheme to be validated first: route to validation_agent before action_agent.
- If validation reports NOT ELIGIBLE or missing information, do not route to action_agent.
- Choose FINISH when everything the user asked for has been handled (or cannot be)."""

INFO_WORDS = {"what", "how", "explain", "document", "documents", "which", "benefit", "benefits", "cover",
              "covers", "criteria", "tell", "list", "available", "who", "rules", "much"}
ELIGIBILITY_WORDS = {"eligible", "eligibility", "qualify", "qualifies"}
ACTION_WORDS = {"book", "booking", "appointment", "apply", "submit", "status", "application", "schedule"}


class Route(BaseModel):
    """The supervisor's routing decision."""

    next: Literal["retrieval_agent", "validation_agent", "action_agent", "FINISH"] = Field(
        description="Which specialist acts next, or FINISH."
    )
    task: str = Field(description="A specific instruction for that specialist (empty for FINISH).")
    reason: str = Field(description="One sentence explaining the choice.")

    @classmethod
    def mock_response(cls, text: str) -> "Route":
        """Keyword routing used ONLY by the offline mock model (a real LLM reads the prompt)."""
        request = re.search(r"User request:\s*(.*)", text)
        done = re.search(r"Agents consulted this turn:\s*(.*)", text)
        req = (request.group(1) if request else text).lower()
        consulted = done.group(1) if done else ""
        words = set(re.findall(r"[a-z]+", req))
        wants = []
        if words & INFO_WORDS and not words & ELIGIBILITY_WORDS:
            wants.append("retrieval_agent")
        if words & ELIGIBILITY_WORDS or ("apply" in words and "status" not in words):
            wants.append("validation_agent")
        if words & ACTION_WORDS:
            wants.append("action_agent")
        if not wants:
            wants.append("retrieval_agent")
        findings = text.split("Findings so far:", 1)[-1]
        not_eligible = "NOT ELIGIBLE" in findings or '"eligible": false' in findings
        for agent in wants:
            if agent in consulted:
                continue
            if agent == "action_agent" and not_eligible:
                continue
            return cls(next=agent, task=request.group(1) if request else text[:300], reason=f"mock: request needs {agent}")
        return cls(next="FINISH", task="", reason="mock: all requested work done")
