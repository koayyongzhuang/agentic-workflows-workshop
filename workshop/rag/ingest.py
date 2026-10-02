"""RAG pipeline: Loading → Indexing (chunk + embed) → Storing → Querying.

    python -m workshop.rag.ingest                 # build the knowledge base
    python -m workshop.rag.ingest --query "Who can get the mobility grant?"
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from rich.console import Console
from rich.table import Table

from workshop.config import get_settings
from workshop.rag.store import Chunk, Hit, get_store

console = Console()


# 1) LOADING -------------------------------------------------------------------
def load_documents(folder: Path | None = None) -> list[tuple[str, str]]:
    folder = folder or get_settings().knowledge_base_dir
    return [(p.name, p.read_text(encoding="utf-8")) for p in sorted(folder.glob("*.md"))]


def parse(text: str) -> tuple[dict, str]:
    """Split YAML-ish front matter from the markdown body."""
    meta: dict = {}
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if m:
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        text = text[m.end():]
    return meta, text


# 2) INDEXING (chunking) ---------------------------------------------------------
def chunk_markdown(text: str, max_chars: int = 900, overlap: int = 120) -> list[str]:
    """Split on headings first (keeps sections intact), then by size with overlap."""
    sections = re.split(r"\n(?=#{1,3} )", text.strip())
    # merge heading-only sections (e.g. the "# Title" line) into the next section
    merged: list[str] = []
    for sec in sections:
        if merged and len(merged[-1].strip().splitlines()) == 1 and merged[-1].lstrip().startswith("#"):
            merged[-1] = merged[-1] + "\n" + sec
        else:
            merged.append(sec)
    sections = merged
    title = next((s.splitlines()[0].lstrip("# ") for s in sections if s.startswith("# ")), "")
    chunks: list[str] = []
    for sec in sections:
        sec = sec.strip()
        if not sec or sec.startswith(">"):
            continue
        # prefix the document title so each chunk is self-describing
        prefixed = sec if sec.startswith("# ") else f"{title}\n{sec}"
        while len(prefixed) > max_chars:
            cut = prefixed.rfind("\n", 0, max_chars)
            cut = cut if cut > max_chars // 2 else max_chars
            chunks.append(prefixed[:cut].strip())
            prefixed = f"{title}\n" + prefixed[max(cut - overlap, 0):]
        chunks.append(prefixed.strip())
    return chunks


def build_chunks(folder: Path | None = None) -> list[Chunk]:
    out: list[Chunk] = []
    for source, raw in load_documents(folder):
        meta, body = parse(raw)
        for i, piece in enumerate(chunk_markdown(body)):
            out.append(Chunk(content=piece, source=source, chunk_index=i, metadata=meta))
    return out


# 3) STORING ---------------------------------------------------------------------
def ingest(collection: str = "knowledge_base", verbose: bool = True) -> int:
    store = get_store(collection)
    docs = load_documents()
    chunks = build_chunks()
    store.reset()
    n = store.add(chunks)  # embeds + stores
    if verbose:
        s = get_settings()
        backend = "PostgreSQL + pgvector" if s.database_url else "in-memory"
        console.print(f"[bold]1 Loading[/]  {len(docs)} documents from {s.knowledge_base_dir}")
        console.print(f"[bold]2 Indexing[/] {len(chunks)} chunks, embedded with '{s.embedding_model}'")
        console.print(f"[bold]3 Storing[/]  {n} vectors in {backend} (collection '{collection}')")
    return n


# 4) QUERYING --------------------------------------------------------------------
def retrieve(query: str, k: int = 4, collection: str = "knowledge_base", where: dict | None = None) -> list[Hit]:
    store = get_store(collection)
    if store.count() == 0:  # first use without docker: build on the fly
        ingest(collection, verbose=False)
    return store.search(query, k=k, where=where)


def format_hits(hits: list[Hit]) -> str:
    return "\n\n".join(f"[source: {h.source} | score {h.score:.2f}]\n{h.content}" for h in hits)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--query", "-q", help="run a similarity search after ingesting")
    ap.add_argument("-k", type=int, default=4)
    ap.add_argument("--skip-ingest", action="store_true")
    args = ap.parse_args()
    if not args.skip_ingest:
        ingest()
    if args.query:
        hits = retrieve(args.query, args.k)
        table = Table(title=f"4 Querying: “{args.query}”")
        table.add_column("score", justify="right")
        table.add_column("source")
        table.add_column("chunk")
        for h in hits:
            table.add_row(f"{h.score:.3f}", h.source, h.content[:160].replace("\n", " ") + "…")
        console.print(table)


if __name__ == "__main__":
    main()
