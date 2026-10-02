"""PII protection: redact personal data before it reaches an LLM or leaves the system.

Regex detection is a fast, transparent first line of defence. In production,
pair it with an NER-based detector (for example Microsoft Presidio) and
tune the patterns for your jurisdiction.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# (label, pattern). Order matters: more specific patterns first.
PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("NRIC", re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.I)),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    ("PHONE", re.compile(r"(?:\+65[ -]?)?\b[689]\d{3}[ -]?\d{4}\b")),
    ("BANK_ACCOUNT", re.compile(r"\b\d{3}-\d{5,6}-\d{1,3}\b")),
]


@dataclass
class RedactionResult:
    text: str
    found: dict[str, int]

    @property
    def had_pii(self) -> bool:
        return bool(self.found)


def redact(text: str) -> RedactionResult:
    found: dict[str, int] = {}
    for label, pattern in PII_PATTERNS:
        text, n = pattern.subn(f"[{label}_REDACTED]", text)
        if n:
            found[label] = found.get(label, 0) + n
    return RedactionResult(text, found)
