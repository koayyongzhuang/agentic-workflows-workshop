"""Citizen-services tools shared by Part 1 and Part 2.

A tool is just a Python function with a clear name, typed arguments and a
docstring. The LLM only ever sees the name, the docstring and the argument
schema, so those three things ARE the tool's interface. Write them for a
reader who has never seen your code.
"""

from __future__ import annotations

import ast
import json
import operator
from datetime import date

from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool

from workshop.gov_api.client import GovApiError, call
from workshop.rag.ingest import format_hits, retrieve


def _json(data) -> str:
    return json.dumps(data, indent=1, default=str)


# ----------------------------------------------------------------------------- knowledge
@tool
def search_knowledge_base(query: str) -> str:
    """Search the official policy knowledge base (RAG): what a scheme, grant, rebate, credit or
    voucher covers, who is eligible, benefit amounts, documents required, how to apply,
    appointments, processing times and the data privacy policy.
    Use this to explain or answer questions; cite the [source] in your answer."""
    hits = retrieve(query, k=3)
    return format_hits(hits) if hits else "No relevant passages found."


@tool
def list_schemes() -> str:
    """List all available support schemes (grants, rebates, credits, vouchers) with a one-line summary."""
    try:
        return _json(call("GET", "/schemes"))
    except GovApiError as e:
        return f"ERROR {e}"


@tool
def get_scheme_details(scheme: str) -> str:
    """Get the full details of one scheme: eligibility criteria, benefit amount,
    required documents and whether an appointment is needed.
    `scheme` may be the scheme ID (e.g. SMG) or its name."""
    try:
        return _json(call("GET", f"/schemes/{scheme}"))
    except GovApiError as e:
        return f"ERROR {e}"


# ----------------------------------------------------------------------------- validation
@tool
def check_eligibility(
    scheme: str,
    age: int,
    monthly_household_income: float,
    household_size: int = 1,
    residency: str = "citizen",
) -> str:
    """Check whether an applicant is eligible (qualifies) for a scheme using the official eligibility service.
    `scheme`: scheme ID or name. `monthly_household_income`: total for the whole household in dollars.
    `household_size`: number of people living in the household. `residency`: citizen, pr or foreigner."""
    try:
        return _json(call("POST", "/eligibility", json={
            "scheme": scheme, "age": age, "monthly_household_income": monthly_household_income,
            "household_size": household_size, "residency": residency,
        }))
    except GovApiError as e:
        return f"ERROR {e}"


_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.Mod: operator.mod}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Only numbers and + - * / ** % are allowed")


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression, e.g. '3600 / 3' for per-capita income. Numbers and + - * / only."""
    try:
        return str(round(_safe_eval(ast.parse(expression, mode="eval").body), 4))
    except (ValueError, SyntaxError, ZeroDivisionError) as e:
        return f"ERROR {e}"


# ----------------------------------------------------------------------------- actions
@tool
def get_appointment_slots(scheme: str) -> str:
    """List available appointment slots (date, time, service centre) for a scheme that needs an appointment."""
    try:
        slots = call("GET", "/appointments/slots", params={"scheme": scheme})
        return _json(slots[:6]) if slots else "This scheme does not need an appointment."
    except GovApiError as e:
        return f"ERROR {e}"


@tool
def book_appointment(scheme: str, slot: str | None = None, applicant_ref: str = "ANON-0001") -> str:
    """Book an appointment (e.g. a home mobility assessment) for a scheme.
    `slot`: a slot ID from get_appointment_slots; omit to book the earliest available slot.
    `applicant_ref`: pseudonymous reference; never pass identity numbers."""
    try:
        return _json(call("POST", "/appointments", json={"scheme": scheme, "slot": slot, "applicant_ref": applicant_ref}))
    except GovApiError as e:
        return f"ERROR {e}"


@tool
def submit_application(scheme: str, applicant_ref: str = "ANON-0001") -> str:
    """Submit an application for a scheme on behalf of the applicant. Only do this after
    eligibility has been checked and the user has confirmed they want to apply."""
    try:
        return _json(call("POST", "/applications", json={
            "scheme": scheme, "applicant_ref": applicant_ref, "eligibility_checked": True,
        }))
    except GovApiError as e:
        return f"ERROR {e}"


@tool
def check_application_status(application_id: str) -> str:
    """Look up the status of a submitted application by its ID (format APP-1234)."""
    try:
        return _json(call("GET", f"/applications/{application_id}"))
    except GovApiError as e:
        return f"ERROR {e}"


# ----------------------------------------------------------------------------- utilities
@tool
def get_today() -> str:
    """Return today's date (YYYY-MM-DD, weekday). Use for questions about deadlines or 'this week'."""
    d = date.today()
    return f"{d.isoformat()} ({d:%A})"


# ----------------------------------------------------------------------------- long-term memory
@tool
def remember_fact(fact: str, config: RunnableConfig) -> str:
    """Save a durable fact about the user for future conversations (long-term memory),
    e.g. 'lives with spouse, household of 2'. Never store identity numbers."""
    from workshop.guardrails.pii import redact
    from workshop.rag.store import Chunk, get_store

    user = (config.get("configurable") or {}).get("user_id", "demo-user")
    clean = redact(fact).text
    get_store("memories").add([Chunk(content=clean, source="memory", metadata={"user_id": user})])
    return f"Saved to long-term memory for {user}: {clean}"


@tool
def recall_facts(query: str, config: RunnableConfig) -> str:
    """Recall facts saved about the user in earlier conversations (long-term memory, remembered facts)."""
    from workshop.rag.store import get_store

    user = (config.get("configurable") or {}).get("user_id", "demo-user")
    hits = get_store("memories").search(query, k=5, where={"user_id": user})
    return "\n".join(f"- {h.content}" for h in hits) or "Nothing remembered yet."


ALL_TOOLS = {
    t.name: t
    for t in [
        search_knowledge_base, list_schemes, get_scheme_details, check_eligibility, calculator,
        get_appointment_slots, book_appointment, submit_application, check_application_status,
        get_today, remember_fact, recall_facts,
    ]
}
