"""A small, readable runner for specialist agents used in Part 2.

Each specialist is a prompt + a tool list. `run_specialist` runs the same
reason → act loop you built as a graph in Part 1, with guardrail hooks on
every tool call:

    LLM proposes tool call
        ├─ not on this agent's allow-list?   -> DENIED (tool governance)
        ├─ `guard` returns a message?        -> that message instead (policy / approval)
        └─ otherwise                         -> execute tool, feed result back
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from langchain_core.messages import AIMessage, BaseMessage, SystemMessage, ToolMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import BaseTool

from workshop.guardrails.tool_policy import enforce_allowlist, is_allowed
from workshop.llm import get_chat_model

# guard(tool_name, args) -> None to allow, or a string returned to the LLM instead of running the tool
ToolGuard = Callable[[str, dict], "str | None"]


@dataclass
class Specialist:
    name: str
    system_prompt: str
    tools: list[BaseTool] = field(default_factory=list)
    max_tool_calls: int = 5
    governed: bool = True  # enforce TOOL_ALLOWLIST for this agent

    def __post_init__(self) -> None:
        if self.governed:
            enforce_allowlist(self.name, [t.name for t in self.tools])


@dataclass
class SpecialistResult:
    report: AIMessage                 # the agent's final message (goes back to the orchestrator)
    transcript: list[BaseMessage]     # everything it did (for tracing / state updates)

    def tool_results(self, tool_name: str) -> list[ToolMessage]:
        return [m for m in self.transcript if isinstance(m, ToolMessage) and m.name == tool_name]


def run_specialist(
    spec: Specialist,
    task_messages: list[BaseMessage],
    config: RunnableConfig | None = None,
    guard: ToolGuard | None = None,
    context: str = "",
) -> SpecialistResult:
    tools_by_name = {t.name: t for t in spec.tools}
    base = get_chat_model(role=spec.name)
    llm = base.bind_tools(spec.tools) if spec.tools else base

    messages: list[BaseMessage] = [SystemMessage(spec.system_prompt)]
    if context:
        messages.append(SystemMessage(f"Context from other agents:\n{context}"))
    messages.extend(task_messages)
    transcript: list[BaseMessage] = []

    calls = 0
    while True:
        ai = llm.invoke(messages, config)
        messages.append(ai)
        transcript.append(ai)
        if not ai.tool_calls:
            break
        if calls >= spec.max_tool_calls:
            messages.pop()  # drop the unanswered tool call and force an answer
            ai = base.invoke(messages + [SystemMessage("Tool budget reached. Report what you have.")], config)
            transcript.append(ai)
            break
        for tc in ai.tool_calls:
            calls += 1
            name, args = tc["name"], tc.get("args", {})
            if spec.governed and not is_allowed(spec.name, name):
                content = f"DENIED: {spec.name} is not permitted to call '{name}'."
            elif name not in tools_by_name:
                content = f"ERROR: unknown tool '{name}'."
            elif guard and (blocked := guard(name, args)):
                content = blocked
            else:
                try:
                    out = tools_by_name[name].invoke(args, config)
                    content = out if isinstance(out, str) else str(out)
                except Exception as exc:  # noqa: BLE001 - let the LLM see and recover from tool errors
                    content = f"ERROR: {exc}"
            tm = ToolMessage(content=content, tool_call_id=tc["id"], name=name)
            messages.append(tm)
            transcript.append(tm)

    report = AIMessage(content=str(ai.content), name=spec.name)
    return SpecialistResult(report=report, transcript=transcript)
