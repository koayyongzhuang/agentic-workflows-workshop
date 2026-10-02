"""Pre-flight check: run this first (`make check`). Every line should be green."""

from __future__ import annotations

import sys

from rich.console import Console

console = Console()
ok = True


def step(name: str, fn) -> None:
    global ok
    try:
        detail = fn()
        console.print(f"[green]✓[/] {name}" + (f" [dim]{detail}[/]" if detail else ""))
    except Exception as exc:  # noqa: BLE001
        ok = False
        console.print(f"[red]✗ {name}[/]: {exc}")


def main() -> None:
    from workshop.config import get_settings

    s = get_settings()
    step("python >= 3.11", lambda: sys.version.split()[0] if sys.version_info >= (3, 11) else (_ for _ in ()).throw(RuntimeError(sys.version)))
    step("model configured", lambda: f"{s.model}" + ("  (offline mock: set MODEL in .env for the real workshop)" if s.is_mock else ""))

    def llm_call():
        from workshop.llm import get_chat_model
        return str(get_chat_model().invoke("Reply with the single word: ready").content)[:60]

    step("LLM responds", llm_call)

    def tool_calling():
        from workshop.llm import get_chat_model
        from workshop.tools import list_schemes
        msg = get_chat_model().bind_tools([list_schemes]).invoke("List the available schemes using the tool.")
        if not msg.tool_calls:
            raise RuntimeError("model did not call the tool. Does it support tool calling?")
        return f"called {msg.tool_calls[0]['name']}"

    step("LLM tool calling", tool_calling)

    def gov_api():
        from workshop.gov_api.client import call
        return f"{s.gov_api_url or 'in-process'}: {len(call('GET', '/schemes'))} schemes"

    step("Mock Gov Service", gov_api)

    def rag():
        from workshop.rag.ingest import retrieve
        hits = retrieve("mobility aids for seniors", k=1)
        backend = "pgvector" if s.database_url else "in-memory"
        return f"{backend}, embeddings '{s.embedding_model}', top hit: {hits[0].source}"

    step("RAG store", rag)

    def memory():
        from workshop.memory import get_checkpointer
        return type(get_checkpointer()).__name__

    step("checkpointer", memory)
    console.print("\n[bold green]All set![/]" if ok else "\n[bold red]Fix the items above (see README › Troubleshooting).[/]")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
