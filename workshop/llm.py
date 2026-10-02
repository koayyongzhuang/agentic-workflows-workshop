"""Model factory: one place to choose (and swap) the LLM and embedding models.

    MODEL=openai:gpt-4o-mini            # any provider supported by init_chat_model
    MODEL_VALIDATION=anthropic:...      # optional per-agent override (role name in caps)
    MODEL=mock                          # offline, deterministic, no API key

The same code runs against every provider because LangChain normalises
tool-calling across them.
"""

from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from workshop.config import get_settings


def model_name_for(role: str | None = None) -> str:
    settings = get_settings()
    if role:
        override = os.getenv(f"MODEL_{role.upper()}", "").strip()
        if override:
            return override
    return settings.model


def get_chat_model(model: str | None = None, role: str | None = None, temperature: float | None = None) -> BaseChatModel:
    """Return a chat model.

    `role` lets each agent use a different model (set MODEL_<ROLE> in .env),
    e.g. a cheap fast model for routing and a stronger one for validation.
    """
    spec = model or model_name_for(role)
    if spec == "mock":
        from workshop.mock_llm import MockChatModel

        return MockChatModel(role=role or "assistant")

    from langchain.chat_models import init_chat_model

    temp = get_settings().temperature if temperature is None else temperature
    return init_chat_model(spec, temperature=temp)


def get_embeddings(model: str | None = None) -> Embeddings:
    spec = model or get_settings().embedding_model
    if spec == "hash":
        from workshop.rag.embeddings import HashEmbeddings

        return HashEmbeddings()
    from langchain.embeddings import init_embeddings

    return init_embeddings(spec)
