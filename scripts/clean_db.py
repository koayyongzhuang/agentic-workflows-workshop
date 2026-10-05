"""Empty the workshop database: knowledge base, long-term memories and saved conversations,
plus LangGraph Studio's saved threads (.langgraph_api/).

    make clean-db

Containers keep running. Tables are emptied, not dropped, so nothing needs a restart.
The knowledge base reloads by itself on the next search (or run `make ingest` now).
Studio keeps its threads in memory while it runs, so stop `make studio` first.
"""

from __future__ import annotations

import shutil
import socket
import sys
from pathlib import Path

from rich.console import Console

console = Console()

# what each table holds, for the summary
LABELS = {
    "kb_chunks": "knowledge base + long-term memories",
    "kb_collections": "vector collections",
    "checkpoints": "saved conversations",
    "checkpoint_writes": "saved conversation steps",
    "checkpoint_blobs": "saved conversation data",
}
KEEP = {"checkpoint_migrations"}  # schema version bookkeeping, not data
STUDIO_DIR = Path(__file__).resolve().parents[1] / ".langgraph_api"
STUDIO_PORT = 2024


def studio_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", STUDIO_PORT), timeout=0.5):
            return True
    except OSError:
        return False


def clean_studio() -> None:
    """Studio (`make studio`) saves its threads to .langgraph_api/, not to Postgres."""
    if not STUDIO_DIR.exists():
        return
    if studio_running():
        console.print("[yellow]![/] Studio threads were [bold]not[/] cleared: `make studio` is running and would write "
                      "them back. Stop it (Ctrl-C), then run [cyan]make clean-db[/] again.")
        return
    shutil.rmtree(STUDIO_DIR)
    console.print(f"[green]✓[/] cleared  {'.langgraph_api/':<20} [dim]Studio's saved threads[/]")


def main() -> None:
    from workshop.config import get_settings

    url = get_settings().database_url
    if not url:
        console.print("No DATABASE_URL set: the knowledge base and memory live in the running process.")
        clean_studio()
        return

    import psycopg

    try:
        with psycopg.connect(url, autocommit=True) as conn, conn.cursor() as cur:
            cur.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
            tables = [t for (t,) in cur.fetchall() if t not in KEEP]
            if not tables:
                console.print("The database is already empty.")
                clean_studio()
                return
            counts = {}
            for t in tables:
                cur.execute(f'SELECT count(*) FROM "{t}"')
                counts[t] = cur.fetchone()[0]
            cur.execute("TRUNCATE " + ", ".join(f'"{t}"' for t in tables) + " CASCADE")
    except psycopg.OperationalError as exc:
        console.print(f"[red]Couldn't reach the database.[/] Run `make up`, then try again. [dim]({exc})[/]")
        sys.exit(1)

    for t in tables:
        console.print(f"[green]✓[/] emptied {t:<20} [dim]{counts[t]:>6} rows · {LABELS.get(t, '')}[/]")
    clean_studio()
    console.print("\n[bold]Database is clean.[/] The knowledge base reloads on the next search, "
                  "or run [cyan]make ingest[/] to load it now.")


if __name__ == "__main__":
    main()
