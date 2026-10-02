"""Observability: see every reasoning step, tool call and result as it happens.

`Tracer` is a LangChain callback handler. Pass it in the run config and it
  * prints graph nodes, tool selection, tool invocation and results live, and
  * appends one JSON line per run to traces/traces.jsonl, which
    `python scripts/trace_report.py` turns into the key metrics from the slides
    (success rate, tools used, average response time).

It works alongside hosted tracing: set LANGSMITH_TRACING=true and
LANGSMITH_API_KEY in .env and the same runs also appear in LangSmith.
"""

from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Iterator

from langchain_core.callbacks import BaseCallbackHandler
from rich.console import Console

from workshop.config import get_settings

console = Console()


def _short(value: Any, n: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1] + "…"


class Tracer(BaseCallbackHandler):
    """Collects a structured trace of one agent run."""

    raise_error = False

    def __init__(self, label: str, question: str = "", verbose: bool | None = None):
        self.label = label
        self.question = question
        self.verbose = get_settings().verbose if verbose is None else verbose
        self.run_id = uuid.uuid4().hex[:12]
        self.started = time.perf_counter()
        self.nodes: list[str] = []
        self.tools: list[dict] = []
        self.llm_calls = 0
        self.tokens = 0
        self._tool_start: dict[uuid.UUID, tuple[str, float, str]] = {}
        self._llm_start: dict[uuid.UUID, float] = {}
        self.llm_latency_s = 0.0

    # ---- graph nodes -----------------------------------------------------
    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, tags=None, metadata=None, **kwargs):
        node = (metadata or {}).get("langgraph_node")
        if node and kwargs.get("name") == node and not str(node).startswith("__"):
            self.nodes.append(node)
            if self.verbose:
                console.print(f"[bold magenta]▶ node[/] [magenta]{node}[/]")

    # ---- LLM calls ---------------------------------------------------------
    def on_chat_model_start(self, serialized, messages, *, run_id, **kwargs):
        self.llm_calls += 1
        self._llm_start[run_id] = time.perf_counter()

    def on_llm_end(self, response, *, run_id, **kwargs):
        start = self._llm_start.pop(run_id, None)
        if start:
            self.llm_latency_s += time.perf_counter() - start
        try:
            usage = response.generations[0][0].message.usage_metadata or {}
            self.tokens += int(usage.get("total_tokens", 0))
        except (AttributeError, IndexError, TypeError):
            pass

    # ---- tools -------------------------------------------------------------
    def on_tool_start(self, serialized, input_str, *, run_id, inputs=None, **kwargs):
        name = (serialized or {}).get("name") or kwargs.get("name", "tool")
        args = inputs if inputs is not None else input_str
        self._tool_start[run_id] = (name, time.perf_counter(), _short(args, 400))
        if self.verbose:
            console.print(f"  [bold cyan]🔧 tool selected[/] [cyan]{name}[/]  [dim]{_short(args)}[/]")

    def on_tool_end(self, output, *, run_id, **kwargs):
        name, start, args = self._tool_start.pop(run_id, ("tool", time.perf_counter(), ""))
        content = getattr(output, "content", output)
        ms = (time.perf_counter() - start) * 1000
        self.tools.append({"tool": name, "args": args, "ok": True, "ms": round(ms, 1), "output": _short(content, 400)})
        if self.verbose:
            console.print(f"  [green]✓ result[/] [dim]({ms:.0f} ms)[/] {_short(content)}")

    def on_tool_error(self, error, *, run_id, **kwargs):
        name, start, args = self._tool_start.pop(run_id, ("tool", time.perf_counter(), ""))
        self.tools.append({"tool": name, "args": args, "ok": False, "error": str(error)})
        if self.verbose:
            console.print(f"  [red]✗ tool error[/] {name}: {error}")

    # ---- persistence -------------------------------------------------------
    def record(self, success: bool, answer: str = "", error: str | None = None, extra: dict | None = None) -> dict:
        elapsed = time.perf_counter() - self.started
        row = {
            "run_id": self.run_id,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": self.label,
            "model": get_settings().model,
            "question": self.question,
            "success": success,
            "error": error,
            "response_time_s": round(elapsed, 3),
            "llm_calls": self.llm_calls,
            "llm_latency_s": round(self.llm_latency_s, 3),
            "tokens": self.tokens,
            "nodes": self.nodes,
            "tools": self.tools,
            "answer": _short(answer, 1000),
            **(extra or {}),
        }
        trace_dir = get_settings().trace_dir
        trace_dir.mkdir(parents=True, exist_ok=True)
        with open(trace_dir / "traces.jsonl", "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, default=str) + "\n")
        if self.verbose:
            console.print(
                f"[dim]trace {self.run_id}: {elapsed:.2f}s · {self.llm_calls} LLM calls · "
                f"{len(self.tools)} tool calls · path: {' → '.join(self.nodes) or '-'}[/]"
            )
        return row


@contextmanager
def traced(label: str, question: str = "", verbose: bool | None = None, **config: Any) -> Iterator[tuple[dict, Tracer]]:
    """Usage:
        with traced("single-agent", q) as (config, tracer):
            result = graph.invoke(inputs, config)
            tracer.outcome = result["messages"][-1].content
    """
    tracer = Tracer(label, question, verbose)
    tracer.outcome = ""  # type: ignore[attr-defined]
    cfg = {"callbacks": [tracer], "run_name": label, "metadata": {"workshop_run": tracer.run_id}, **config}
    try:
        yield cfg, tracer
    except Exception as exc:  # noqa: BLE001
        tracer.record(False, error=repr(exc))
        raise
    else:
        answer = getattr(tracer, "outcome", "")
        tracer.record(getattr(tracer, "success", True), answer=answer)
