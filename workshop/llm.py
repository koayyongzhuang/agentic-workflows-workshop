"""Model factory: one place to choose (and swap) the LLM and embedding models.

    MODEL=openai:gpt-4o-mini            # any provider supported by init_chat_model
    MODEL_VALIDATION=anthropic:...      # optional per-agent override (role name in caps)
    MODEL=openrouter:openai/gpt-6-luna  # any OpenRouter model ID (needs OPENROUTER_API_KEY)
    MODEL=mock                          # offline, deterministic, no API key

The same code runs against every provider because LangChain normalises
tool-calling across them.
"""

from __future__ import annotations

import os

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from workshop.config import get_settings


# providers whose LangChain chat model accepts `max_retries`
RETRYING_PROVIDERS = {"openai", "azure_openai", "anthropic", "google_genai", "mistralai", "groq"}


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

    temp = get_settings().temperature if temperature is None else temperature
    # Rate limits (429), timeouts and 5xx errors are retried with exponential backoff
    # before an error reaches the user. Override with MODEL_MAX_RETRIES in .env.
    retries = int(os.getenv("MODEL_MAX_RETRIES", "4") or 4)

    if spec.startswith("openrouter:"):
        # OpenRouter speaks the OpenAI API, so ChatOpenAI works with a different base URL and key.
        from langchain_openai import ChatOpenAI

        api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("MODEL uses openrouter: but OPENROUTER_API_KEY is not set in .env")
        return ChatOpenAI(
            model=spec.split(":", 1)[1],
            base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
            api_key=api_key,
            temperature=temp,
            max_retries=retries,
            timeout=60,
            default_headers={"X-Title": "Agentic Workflows Workshop"},
        )

    from langchain.chat_models import init_chat_model

    provider = spec.split(":", 1)[0]
    extra = {"max_retries": retries} if provider in RETRYING_PROVIDERS else {}
    return init_chat_model(spec, temperature=temp, **extra)


def get_embeddings(model: str | None = None) -> Embeddings:
    spec = model or get_settings().embedding_model
    if spec == "hash":
        from workshop.rag.embeddings import HashEmbeddings

        return HashEmbeddings()
    from langchain.embeddings import init_embeddings

    return init_embeddings(spec)
