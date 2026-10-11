"""Extra tools for EXERCISE 2 (swap tools).

Swap these in and out of a role's tool list, or pass them directly:

    from lab_1_single_agent.agent import build_single_agent
    from lab_1_single_agent.extra_tools import keyword_faq_search
    from workshop.tools import ALL_TOOLS
    agent = build_single_agent(tools=[keyword_faq_search, ALL_TOOLS["check_eligibility"]])
"""

from __future__ import annotations

from langchain_core.tools import tool

from workshop.config import get_settings


@tool
def keyword_faq_search(query: str) -> str:
    """Search the policy documents by exact keyword match (no embeddings).
    Returns lines that contain any of the query's words."""
    words = {w.strip("?.,!").lower() for w in query.split() if len(w) > 3}
    hits = []
    for path in sorted(get_settings().knowledge_base_dir.glob("*.md")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if any(w in line.lower() for w in words):
                hits.append(f"[{path.name}] {line.strip()}")
    return "\n".join(hits[:12]) or "No matching lines."


@tool
def estimate_energy_rebate(monthly_household_income: float, household_size: int = 1) -> str:
    """Estimate the quarterly Household Energy Rebate from income and household size."""
    # TODO (exercise): implement using the table in data/knowledge_base/household_energy_rebate.md
    #   per-capita $0-1,000 -> $150 ; $1,001-1,800 -> $100 ; $1,801-2,500 -> $60 ; above -> not eligible
    # Lab 1 guide, Exercise B: ask the question below first (you'll see this error), then implement.
    #   "My household of 3 earns $4,200 a month. How much energy rebate would we get?"
    raise NotImplementedError("estimate_energy_rebate is not implemented yet (Lab 1, Exercise B)")


@tool
def get_weather(city: str) -> str:
    """Get today's weather forecast for a city."""
    # A deliberately irrelevant tool. Add it (and a few more like it) to see whether
    # tool selection gets worse as the tool list grows.
    return f"Forecast for {city}: 31°C, afternoon thunderstorms."


EXTRA_TOOLS = {t.name: t for t in [keyword_faq_search, estimate_energy_rebate, get_weather]}
