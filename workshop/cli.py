"""Small shared helpers for the interactive command-line demos."""

from __future__ import annotations

import uuid
from typing import Callable

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel

from workshop.config import get_settings

console = Console()


def banner(title: str, subtitle: str, examples: list[str]) -> None:
    s = get_settings()
    mode = "[yellow]OFFLINE MOCK MODEL[/] (set MODEL in .env for a real LLM)" if s.is_mock else f"model [bold]{s.model}[/]"
    store = "PostgreSQL + pgvector" if s.database_url else "in-memory store"
    api = s.gov_api_url or "in-process Mock Gov API"
    console.print(Panel.fit(
        f"[bold]{title}[/]\n{subtitle}\n\n{mode} · {store} · {api}\n\n"
        "Try:\n" + "\n".join(f"  • {e}" for e in examples)
        + "\n\nCommands: /new (new thread)  /graph (show graph)  /exit",
        border_style="magenta",
    ))


def show_answer(text: str, title: str = "assistant") -> None:
    console.print(Panel(Markdown(text or "(no answer)"), title=title, border_style="green"))


def chat_loop(ask: Callable[[str, str], None], show_graph: Callable[[], None]) -> None:
    """`ask(question, thread_id)` runs one turn."""
    thread = uuid.uuid4().hex[:8]
    while True:
        try:
            q = console.input("[bold blue]you ›[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print()
            break
        if not q:
            continue
        if q in {"/exit", "/quit"}:
            break
        if q == "/new":
            thread = uuid.uuid4().hex[:8]
            console.print(f"[dim]new thread {thread} (short-term memory cleared)[/]")
            continue
        if q == "/graph":
            show_graph()
            continue
        ask(q, thread)
