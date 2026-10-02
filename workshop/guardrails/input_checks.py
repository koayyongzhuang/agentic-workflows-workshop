"""Input guardrails: prompt-injection and toxic-content screening.

These heuristics are intentionally readable. Production systems layer them
with a classifier (for example a moderation endpoint or a guard model) and
log every block for review.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from workshop.guardrails.pii import redact

INJECTION_PATTERNS = [
    r"ignore (all |any )?(previous|prior|above) (instructions|rules)",
    r"disregard (your|the) (rules|instructions|system prompt)",
    r"you are now (in )?(developer|dan|jailbreak) mode",
    r"reveal (your|the) (system prompt|instructions|hidden)",
    r"act as (an? )?(admin|administrator|officer) and approve",
    r"approve (my|this) application (now|immediately|without)",
    r"(bypass|skip|override) (the )?(eligibility|validation|policy|approval)",
]

# Placeholder list: swap in a real moderation model for production.
TOXIC_TERMS = ["idiot", "stupid bot", "kill you", "hate you"]


@dataclass
class GuardResult:
    allowed: bool
    text: str
    reasons: list[str] = field(default_factory=list)
    pii_found: dict[str, int] = field(default_factory=dict)


def check_input(text: str) -> GuardResult:
    """Run all input guardrails. Returns redacted text and whether to continue."""
    reasons: list[str] = []
    low = text.lower()
    for pat in INJECTION_PATTERNS:
        if re.search(pat, low):
            reasons.append("prompt_injection")
            break
    if any(term in low for term in TOXIC_TERMS):
        reasons.append("toxic_content")
    red = redact(text)
    return GuardResult(allowed=not reasons, text=red.text, reasons=reasons, pii_found=red.found)


def check_output(text: str) -> GuardResult:
    """Output guardrail: never echo personal data back, even if a tool returned it."""
    red = redact(text)
    return GuardResult(allowed=True, text=red.text, pii_found=red.found)


BLOCK_MESSAGES = {
    "prompt_injection": (
        "I can't follow instructions that try to change my rules. I can explain schemes, "
        "check eligibility, and help you book appointments or apply."
    ),
    "toxic_content": "I'm here to help. Let's keep things respectful. What would you like to do?",
}
