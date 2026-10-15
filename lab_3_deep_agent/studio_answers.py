"""Let Studio's resume box accept a typed answer for the approval pause.

`interrupt_on` pauses with LangChain's HumanInTheLoopMiddleware, which expects the resume
value to be an object: {"decisions": [{"type": "approve"}]}. Studio sends whatever you type
as text, so the middleware gets a string and fails with
"TypeError: string indices must be integers". This wraps the middleware's `interrupt` call so
a typed answer works too:

    {"decisions": [{"type": "approve"}]}   typed as text: read as JSON
    yes / approve / ok                      approve every paused tool call
    anything else (no, a reason, ...)       reject them, with your text as the message

The terminal chat (`make deep`) already sends a proper object, so nothing changes there.
"""

from __future__ import annotations

import json

import langchain.agents.middleware.human_in_the_loop as _hitl

APPROVE_WORDS = {"y", "yes", "approve", "approved", "ok"}
_original_interrupt = _hitl.interrupt


def _interrupt_accepting_text(value):
    answer = _original_interrupt(value)
    if not isinstance(answer, str):
        return answer
    text = answer.strip()
    try:
        parsed = json.loads(text)
    except ValueError:
        parsed = None
    if isinstance(parsed, dict):
        return parsed
    count = len(value.get("action_requests", [])) or 1
    if text.lower() in APPROVE_WORDS:
        return {"decisions": [{"type": "approve"}] * count}
    reason = text if text.lower() not in {"n", "no"} else "Rejected by the reviewer."
    return {"decisions": [{"type": "reject", "message": reason}] * count}


_hitl.interrupt = _interrupt_accepting_text
