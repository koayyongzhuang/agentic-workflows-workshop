"""Small shared helpers for the interactive command-line demos."""

from __future__ import annotations

import uuid
from typing import Callable

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from workshop.config import get_settings
from workshop.errors import show_error

console = Console()


def banner(title: str, subtitle: str, examples: list[str]) -> None:
    s = get_settings()
    mode = "[yellow]OFFLINE MOCK MODEL[/] (set MODEL in .env for a real LLM)" if s.is_mock else f"model [bold]{s.model}[/]"
    store = "PostgreSQL + pgvector" if s.database_url else "in-memory store"
    api = s.gov_api_url or "in-process Mock Gov API"
    console.print(Panel.fit(
        f"[bold]{title}[/]\n{subtitle}\n\n{mode} · {store} · {api}\n\n"
        "Try:\n" + "\n".join(f"  • {e}" for e in examples)
        + "\n\nCommands: /new (new thread)  /graph (show graph)  /exit\n"
        "If a turn fails, press Enter to retry it.",
        border_style="magenta",
    ))


def show_answer(text: str, title: str = "assistant") -> None:
    console.print(Panel(Markdown(text or "(no answer)"), title=title, border_style="green"))


def chat_loop(ask: Callable[[str, str, bool], None], show_graph: Callable[[], None]) -> None:
    """`ask(question, thread_id, resume)` runs one turn.

    An error never ends the session: it is explained, and pressing Enter retries
    the failed turn from where it stopped (resume=True), without repeating the
    question in the conversation history.
    """
    thread = uuid.uuid4().hex[:8]
    failed: str | None = None  # the question whose turn failed, if it can be retried
    while True:
        try:
            q = console.input("[bold blue]you ›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        resume = False
        if not q:
            if not failed:
                continue
            q, resume = failed, True
            console.print(f"[dim]retrying: {q}[/]")
        if q in {"/exit", "/quit"}:
            break
        if q == "/new":
            thread, failed = uuid.uuid4().hex[:8], None
            console.print(f"[dim]new thread {thread} (short-term memory cleared)[/]")
            continue
        if q == "/graph":
            show_graph()
            continue
        try:
            ask(q, thread, resume)
            failed = None
        except KeyboardInterrupt:
            failed = q
            console.print("[yellow]Stopped. Press Enter to retry, or type a new question.[/]")
        except Exception as exc:  # noqa: BLE001 - explain the error and keep the session alive
            failed = q if show_error(exc, console, can_retry_with_enter=True).retryable else None


def run_once(ask: Callable[[str, str, bool], None], question: str) -> None:
    """One-shot mode (-q): explain any error instead of printing a traceback."""
    try:
        ask(question, "cli", False)
    except KeyboardInterrupt:
        console.print("[yellow]Stopped.[/]")
        raise SystemExit(130) from None
    except Exception as exc:  # noqa: BLE001
        show_error(exc, console)
        raise SystemExit(1) from None
