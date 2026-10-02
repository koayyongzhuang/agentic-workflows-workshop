"""Citizen Services Platform: a supervisor coordinating three specialist agents.

                     ┌──────────────┐
    user ──▶ input_guard ──▶ supervisor ◀───────────────────────────┐
              (PII, injection)   │ Route(next=...)                   │
                                 ├──▶ retrieval_agent ───────────────┤
                                 ├──▶ validation_agent ──────────────┤
                                 ├──▶ action_agent ──▶ human_approval┤ (only if an action awaits approval)
                                 │         └─────────────────────────┘
                                 └──▶ respond ──▶ output_guard ──▶ END

Guardrails in this graph (the "Gov angle"):
  * input_guard      : PII redaction, prompt-injection and toxicity screening
  * tool governance  : each specialist can only call its allow-listed tools
  * policy           : book/submit only for schemes that passed validation
  * human approval   : sensitive actions pause (LangGraph interrupt) until a person approves
  * output_guard     : PII redaction on the final answer
"""

from __future__ import annotations

import json
from typing import Literal

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from part2_multi_agent.citizen_platform.agents import AGENTS, SUPERVISOR_PROMPT, Route
from part2_multi_agent.citizen_platform.state import PlatformState
from workshop.agents import run_specialist
from workshop.config import get_settings
from workshop.guardrails.input_checks import BLOCK_MESSAGES, check_input, check_output
from workshop.guardrails.tool_policy import REQUIRES_APPROVAL, PolicyContext, check_policy
from workshop.llm import get_chat_model
from workshop.tools import ALL_TOOLS

MAX_STEPS_PER_TURN = 6

RESPONDER_PROMPT = """You write the final reply to the citizen, using ONLY the specialist reports provided.
- Answer the user's actual question first, in plain language.
- Keep [source] citations from the retrieval agent.
- State eligibility outcomes and any booking/application references exactly.
- If an action is waiting for approval, was blocked by policy, or information is missing, say so and what happens next.
- Never include identity numbers or other personal data."""


def build_platform(require_approval: bool | None = None, checkpointer=None):
    approval_on = get_settings().human_approval if require_approval is None else require_approval
    supervisor_llm = get_chat_model(role="supervisor").with_structured_output(Route)
    responder_llm = get_chat_model(role="responder")

    # ------------------------------------------------------------------ guards
    def input_guard(state: PlatformState) -> dict:
        last = state["messages"][-1]
        result = check_input(str(last.content))
        update: dict = {
            "turn_steps": [], "context": "", "pending_actions": [],
            "user_request": result.text, "blocked": not result.allowed,
            "messages": [HumanMessage(content=result.text, id=last.id)],  # same id -> replaces the original
        }
        events = [f"pii_redacted:{k}x{v}" for k, v in result.pii_found.items()] + [f"blocked:{r}" for r in result.reasons]
        if events:
            update["guardrail_events"] = events
        if not result.allowed:
            update["messages"].append(AIMessage(BLOCK_MESSAGES[result.reasons[0]], name="input_guard"))
        return update

    def after_input_guard(state: PlatformState) -> Literal["supervisor", "__end__"]:
        return END if state.get("blocked") else "supervisor"

    def output_guard(state: PlatformState) -> dict:
        last = state["messages"][-1]
        result = check_output(str(last.content))
        if not result.pii_found:
            return {}
        return {
            "messages": [AIMessage(content=result.text, id=last.id, name=last.name)],
            "guardrail_events": [f"output_pii_redacted:{k}x{v}" for k, v in result.pii_found.items()],
        }

    # ------------------------------------------------------------------ supervisor
    def supervisor(state: PlatformState, config: RunnableConfig) -> dict:
        steps = state.get("turn_steps", [])
        if len(steps) >= MAX_STEPS_PER_TURN:
            return {"next": "FINISH", "task": ""}
        summary = (
            f"User request: {state.get('user_request', '')}\n"
            f"Agents consulted this turn: {', '.join(steps) or 'none'}\n"
            f"Validated schemes: {', '.join(state.get('validated_schemes', [])) or 'none'}\n"
            f"Findings so far:\n{state.get('context') or '(none yet)'}"
        )
        decision: Route = supervisor_llm.invoke([SystemMessage(SUPERVISOR_PROMPT), HumanMessage(summary)], config)
        if decision.next in steps:  # hard stop on loops, whatever the model says
            decision = Route(next="FINISH", task="", reason="agent already consulted")
        return {"next": decision.next, "task": decision.task}

    def route_supervisor(state: PlatformState) -> Literal["retrieval_agent", "validation_agent", "action_agent", "respond"]:
        nxt = state.get("next", "FINISH")
        return nxt if nxt in AGENTS else "respond"

    # ------------------------------------------------------------------ specialists
    def _task_messages(state: PlatformState) -> list:
        task = state.get("task") or state.get("user_request", "")
        return [HumanMessage(f"{task}\n\n(Original user request: {state.get('user_request', '')})")]

    def _report(state: PlatformState, name: str, result) -> dict:
        ctx = (state.get("context") or "") + f"\n[{name}] {result.report.content}"
        return {"messages": [result.report], "turn_steps": [*state.get("turn_steps", []), name], "context": ctx.strip()}

    def retrieval_agent(state: PlatformState, config: RunnableConfig) -> dict:
        result = run_specialist(AGENTS["retrieval_agent"], _task_messages(state), config, context=state.get("context", ""))
        return _report(state, "retrieval_agent", result)

    def validation_agent(state: PlatformState, config: RunnableConfig) -> dict:
        result = run_specialist(AGENTS["validation_agent"], _task_messages(state), config, context=state.get("context", ""))
        validated = set(state.get("validated_schemes", []))
        for tm in result.tool_results("check_eligibility"):
            try:
                data = json.loads(tm.content)
            except (TypeError, ValueError):
                continue
            if data.get("eligible"):
                validated.add(data["scheme_id"])
        update = _report(state, "validation_agent", result)
        update["validated_schemes"] = sorted(validated)
        return update

    def action_agent(state: PlatformState, config: RunnableConfig) -> dict:
        ctx = PolicyContext(validated_schemes=set(state.get("validated_schemes", [])))
        pending: list[dict] = []
        events: list[str] = []

        def guard(tool_name: str, args: dict) -> str | None:
            decision = check_policy(tool_name, args, ctx)
            if not decision.allowed:
                events.append(f"policy_blocked:{tool_name}")
                return f"BLOCKED BY POLICY: {decision.reason}"
            if approval_on and tool_name in REQUIRES_APPROVAL:
                pending.append({"tool": tool_name, "args": args})
                return "PENDING HUMAN APPROVAL: the request has been queued for an officer/user to confirm."
            return None

        result = run_specialist(AGENTS["action_agent"], _task_messages(state), config, guard=guard, context=state.get("context", ""))
        update = _report(state, "action_agent", result)
        update["pending_actions"] = pending
        if events:
            update["guardrail_events"] = events
        return update

    def after_action(state: PlatformState) -> Literal["human_approval", "supervisor"]:
        return "human_approval" if state.get("pending_actions") else "supervisor"

    # ------------------------------------------------------------------ human in the loop
    def human_approval(state: PlatformState, config: RunnableConfig) -> dict:
        done, lines = [], []
        for action in state.get("pending_actions", []):
            answer = interrupt({
                "type": "approval_request",
                "tool": action["tool"],
                "args": action["args"],
                "question": f"Approve {action['tool']} for scheme '{action['args'].get('scheme', '')[:60]}'? (yes/no)",
            })
            approved = str(answer).strip().lower() in {"y", "yes", "approve", "approved", "true", "ok"}
            if approved:
                output = ALL_TOOLS[action["tool"]].invoke(action["args"], config)
                done.append({"tool": action["tool"], "status": "done", "result": output})
                lines.append(f"APPROVED and executed {action['tool']}: {output}")
            else:
                done.append({"tool": action["tool"], "status": "rejected"})
                lines.append(f"REJECTED by human: {action['tool']} was not executed.")
        msg = AIMessage("\n".join(lines) or "Nothing to approve.", name="human_approval")
        ctx = (state.get("context") or "") + "\n[human_approval] " + msg.content
        return {"pending_actions": [], "completed_actions": done, "messages": [msg], "context": ctx.strip(),
                "turn_steps": [*state.get("turn_steps", []), "human_approval"]}

    # ------------------------------------------------------------------ final answer
    def respond(state: PlatformState, config: RunnableConfig) -> dict:
        prompt = [
            SystemMessage(RESPONDER_PROMPT),
            HumanMessage(f"User request: {state.get('user_request', '')}\n\nSpecialist reports:\n{state.get('context') or '(none)'}"),
        ]
        answer = responder_llm.invoke(prompt, config)
        return {"messages": [AIMessage(content=str(answer.content), name="responder")]}

    # ------------------------------------------------------------------ wiring
    g = StateGraph(PlatformState)
    g.add_node("input_guard", input_guard)
    g.add_node("supervisor", supervisor)
    g.add_node("retrieval_agent", retrieval_agent)
    g.add_node("validation_agent", validation_agent)
    g.add_node("action_agent", action_agent)
    g.add_node("human_approval", human_approval)
    g.add_node("respond", respond)
    g.add_node("output_guard", output_guard)

    g.add_edge(START, "input_guard")
    g.add_conditional_edges("input_guard", after_input_guard, ["supervisor", END])
    g.add_conditional_edges("supervisor", route_supervisor, ["retrieval_agent", "validation_agent", "action_agent", "respond"])
    g.add_edge("retrieval_agent", "supervisor")
    g.add_edge("validation_agent", "supervisor")
    g.add_conditional_edges("action_agent", after_action, ["human_approval", "supervisor"])
    g.add_edge("human_approval", "supervisor")
    g.add_edge("respond", "output_guard")
    g.add_edge("output_guard", END)
    return g.compile(checkpointer=checkpointer, name="citizen_services_platform")


def make_graph(config=None):
    """Factory used by LangGraph Studio (see langgraph.json)."""
    return build_platform()
