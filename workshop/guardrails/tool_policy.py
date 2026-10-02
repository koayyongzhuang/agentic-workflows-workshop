"""Tool governance and policy enforcement.

Three controls from the "Guardrail Types" slide:
  1. Tool governance: each agent may only use the tools on its allow-list.
  2. Policy enforcement: some tools are only callable when a condition holds
     (for example: submit only after eligibility was validated).
  3. Human approval: sensitive tools pause for a person to confirm.
"""

from __future__ import annotations

from dataclasses import dataclass, field

# 1) Which agent may call which tool. Anything not listed is denied.
TOOL_ALLOWLIST: dict[str, set[str]] = {
    "retrieval_agent": {"search_knowledge_base", "list_schemes", "get_scheme_details"},
    "validation_agent": {"check_eligibility", "get_scheme_details", "calculator"},
    "action_agent": {"get_appointment_slots", "book_appointment", "submit_application", "check_application_status"},
}

# 3) Tools that change something in the outside world need a human "yes".
REQUIRES_APPROVAL: set[str] = {"book_appointment", "submit_application"}


class ToolNotAllowed(PermissionError):
    pass


def enforce_allowlist(agent: str, tool_names: list[str]) -> None:
    """Fail fast at build time if an agent is wired to a tool it may not use."""
    allowed = TOOL_ALLOWLIST.get(agent, set())
    denied = [t for t in tool_names if t not in allowed]
    if denied:
        raise ToolNotAllowed(f"{agent} is not allowed to use: {', '.join(denied)}")


def is_allowed(agent: str, tool_name: str) -> bool:
    return tool_name in TOOL_ALLOWLIST.get(agent, set())


@dataclass
class PolicyDecision:
    allowed: bool
    reason: str = ""


@dataclass
class PolicyContext:
    """What the policy engine knows about the conversation so far."""

    validated_schemes: set[str] = field(default_factory=set)  # scheme IDs that passed eligibility


# 2) Conditional API access.
def check_policy(tool_name: str, args: dict, ctx: PolicyContext) -> PolicyDecision:
    if tool_name in {"submit_application", "book_appointment"}:
        from workshop.gov_api.app import resolve_scheme  # local import keeps this module light

        try:
            scheme_id = resolve_scheme(str(args.get("scheme", "")))["id"]
        except Exception:  # noqa: BLE001
            return PolicyDecision(False, "Unknown scheme. Check the scheme name first.")
        if scheme_id not in ctx.validated_schemes:
            return PolicyDecision(
                False,
                f"Policy: eligibility for {scheme_id} must be validated before '{tool_name}'. "
                "Ask the validation agent to check eligibility first.",
            )
    return PolicyDecision(True)
