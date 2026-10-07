"""Central configuration, read from environment variables (and `.env`).

Everything is read lazily through `get_settings()` so tests and exercises can
change environment variables at runtime.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")


def _bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None or val == "":
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    # "provider:model", e.g. "openai:gpt-4o-mini", "anthropic:claude-sonnet-4-5",
    # "azure_openai:<deployment>", "bedrock_converse:<model-id>", "ollama:llama3.1".
    # "mock" runs a deterministic offline model (no API key needed).
    model: str
    # "hash" = offline deterministic embeddings; otherwise "provider:model",
    # e.g. "openai:text-embedding-3-small".
    embedding_model: str
    # None = don't send a temperature (some models, e.g. reasoning models, reject it).
    temperature: float | None
    # postgresql://user:pass@host:5432/db  -> pgvector store + Postgres checkpointer.
    # Empty -> in-memory store + in-memory checkpointer.
    database_url: str | None
    # Base URL of the Mock Gov Service. Empty -> the API runs in-process.
    gov_api_url: str | None
    knowledge_base_dir: Path
    trace_dir: Path
    # Ask a human before sensitive actions (bookings, submissions).
    human_approval: bool
    verbose: bool

    @property
    def is_mock(self) -> bool:
        return self.model == "mock"


def _temperature() -> float | None:
    raw = os.getenv("TEMPERATURE", "0").strip()
    return float(raw) if raw else None


def get_settings() -> Settings:
    return Settings(
        model=os.getenv("MODEL", "mock").strip() or "mock",
        embedding_model=os.getenv("EMBEDDING_MODEL", "hash").strip() or "hash",
        temperature=_temperature(),
        database_url=os.getenv("DATABASE_URL", "").strip() or None,
        gov_api_url=os.getenv("GOV_API_URL", "").strip() or None,
        knowledge_base_dir=Path(os.getenv("KNOWLEDGE_BASE_DIR", REPO_ROOT / "data" / "knowledge_base")),
        trace_dir=Path(os.getenv("TRACE_DIR", REPO_ROOT / "traces")),
        human_approval=_bool("HUMAN_APPROVAL", True),
        verbose=_bool("VERBOSE", True),
    )
