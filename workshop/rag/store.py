"""Vector stores: PostgreSQL + pgvector (default in docker) or in-memory.

The pgvector implementation is plain SQL on purpose so you can see exactly
what "Storing" and "Querying" mean:

    INSERT INTO kb_chunks (..., embedding) VALUES (..., '[0.12, -0.03, ...]'::vector)
    SELECT ... ORDER BY embedding <=> '[query vector]'::vector LIMIT k   -- cosine distance
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol

from langchain_core.embeddings import Embeddings

from workshop.config import get_settings
from workshop.llm import get_embeddings


@dataclass
class Chunk:
    content: str
    source: str
    chunk_index: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class Hit:
    content: str
    source: str
    score: float
    metadata: dict


class VectorStore(Protocol):
    collection: str

    def reset(self) -> None: ...
    def add(self, chunks: list[Chunk]) -> int: ...
    def search(self, query: str, k: int = 4, where: dict | None = None) -> list[Hit]: ...
    def count(self) -> int: ...


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


class InMemoryVectorStore:
    """Used when DATABASE_URL is empty (local runs, tests)."""

    _data: dict[str, list[tuple[Chunk, list[float]]]] = {}

    def __init__(self, collection: str, embeddings: Embeddings):
        self.collection = collection
        self.embeddings = embeddings
        self._data.setdefault(collection, [])

    def reset(self) -> None:
        self._data[self.collection] = []

    def add(self, chunks: list[Chunk]) -> int:
        vectors = self.embeddings.embed_documents([c.content for c in chunks])
        self._data[self.collection].extend(zip(chunks, vectors))
        return len(chunks)

    def search(self, query: str, k: int = 4, where: dict | None = None) -> list[Hit]:
        q = self.embeddings.embed_query(query)
        rows = [
            (c, _cosine(q, v))
            for c, v in self._data[self.collection]
            if not where or all(c.metadata.get(key) == val for key, val in where.items())
        ]
        rows.sort(key=lambda r: r[1], reverse=True)
        return [Hit(c.content, c.source, round(s, 4), c.metadata) for c, s in rows[:k]]

    def count(self) -> int:
        return len(self._data[self.collection])


SCHEMA_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS kb_collections (
    name            text PRIMARY KEY,
    embedding_model text NOT NULL,
    dim             int  NOT NULL,
    updated_at      timestamptz DEFAULT now()
);
CREATE TABLE IF NOT EXISTS kb_chunks (
    id          bigserial PRIMARY KEY,
    collection  text NOT NULL REFERENCES kb_collections(name) ON DELETE CASCADE,
    source      text NOT NULL,
    chunk_index int  NOT NULL,
    content     text NOT NULL,
    metadata    jsonb NOT NULL DEFAULT '{}'::jsonb,
    embedding   vector NOT NULL
);
CREATE INDEX IF NOT EXISTS kb_chunks_collection_idx ON kb_chunks (collection);
"""


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


class PgVectorStore:
    """PostgreSQL + pgvector. ACID transactions and point-in-time recovery come with Postgres."""

    def __init__(self, collection: str, embeddings: Embeddings, database_url: str, model_name: str):
        import psycopg

        self.collection = collection
        self.embeddings = embeddings
        self.model_name = model_name
        self.conn = psycopg.connect(database_url, autocommit=True)
        with self.conn.cursor() as cur:
            cur.execute(SCHEMA_SQL)

    def _check_model(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("SELECT embedding_model FROM kb_collections WHERE name=%s", (self.collection,))
            row = cur.fetchone()
        if row and row[0] != self.model_name:
            raise RuntimeError(
                f"Collection '{self.collection}' was embedded with '{row[0]}' but EMBEDDING_MODEL is "
                f"'{self.model_name}'. Re-run: python -m workshop.rag.ingest"
            )

    def reset(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM kb_collections WHERE name=%s", (self.collection,))

    def add(self, chunks: list[Chunk]) -> int:
        if not chunks:
            return 0
        vectors = self.embeddings.embed_documents([c.content for c in chunks])
        with self.conn.transaction(), self.conn.cursor() as cur:
            cur.execute(
                """INSERT INTO kb_collections (name, embedding_model, dim) VALUES (%s, %s, %s)
                   ON CONFLICT (name) DO UPDATE SET updated_at = now()""",
                (self.collection, self.model_name, len(vectors[0])),
            )
            self._check_model()
            cur.executemany(
                """INSERT INTO kb_chunks (collection, source, chunk_index, content, metadata, embedding)
                   VALUES (%s, %s, %s, %s, %s, %s::vector)""",
                [
                    (self.collection, c.source, c.chunk_index, c.content, json.dumps(c.metadata), _vec(v))
                    for c, v in zip(chunks, vectors)
                ],
            )
        return len(chunks)

    def search(self, query: str, k: int = 4, where: dict | None = None) -> list[Hit]:
        self._check_model()
        q = _vec(self.embeddings.embed_query(query))
        filter_sql, params = "", []
        if where:
            filter_sql = " AND metadata @> %s::jsonb"
            params.append(json.dumps(where))
        with self.conn.cursor() as cur:
            cur.execute(
                f"""SELECT content, source, metadata, 1 - (embedding <=> %s::vector) AS score
                    FROM kb_chunks WHERE collection = %s{filter_sql}
                    ORDER BY embedding <=> %s::vector LIMIT %s""",
                [q, self.collection, *params, q, k],
            )
            rows = cur.fetchall()
        return [Hit(r[0], r[1], round(float(r[3]), 4), r[2]) for r in rows]

    def count(self) -> int:
        with self.conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM kb_chunks WHERE collection=%s", (self.collection,))
            return cur.fetchone()[0]


@lru_cache(maxsize=16)
def _cached_store(collection: str, database_url: str | None, model_name: str) -> VectorStore:
    embeddings = get_embeddings(model_name)
    if database_url:
        return PgVectorStore(collection, embeddings, database_url, model_name)
    return InMemoryVectorStore(collection, embeddings)


def get_store(collection: str = "knowledge_base") -> VectorStore:
    s = get_settings()
    return _cached_store(collection, s.database_url, s.embedding_model)
