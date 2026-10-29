"""Shared state for the Citizen Services Platform graph.

Every node reads this state and returns a partial update. With a
checkpointer, the whole state is saved after each step, so a paused run
(human approval) can resume later, even in another process.
"""

from __future__ import annotations

import operator
from typing import Annotated, TypedDict

from langgraph.graph import MessagesState


class PlatformInput(MessagesState):
    """What code callers send (run.py, serve.py, tests): the conversation. The nodes fill in everything else."""


class PlatformTextInput(TypedDict):
    """What Studio asks you for: type your message. The nodes fill in everything else."""

    message: str


class PlatformState(MessagesState):
    # routing
    next: str                                   # set by the supervisor
    task: str                                   # instruction for the chosen specialist
    turn_steps: list[str]                       # agents consulted for the current user message
    # facts established by agents
    user_request: str                           # latest user message (after PII redaction)
    context: str                                # findings shared between agents this turn
    validated_schemes: list[str]                # scheme IDs that passed eligibility (persists across turns)
    # actions
    pending_actions: list[dict]                 # sensitive tool calls waiting for human approval
    completed_actions: Annotated[list[dict], operator.add]
    # guardrails
    blocked: bool
    guardrail_events: Annotated[list[str], operator.add]


class GuardState(PlatformState):
    """What input_guard reads: the state plus the text typed into Studio's `message` box."""

    message: str
