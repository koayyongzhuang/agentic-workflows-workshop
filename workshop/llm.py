"""Model factory: one place to choose (and swap) the LLM and embedding models.

    MODEL=bedrock_converse:global.anthropic.claude-sonnet-4-6   # Amazon Bedrock (the default; AWS_BEARER_TOKEN_BEDROCK)
    MODEL=openai:gpt-4o-mini            # any provider supported by init_chat_model
    MODEL_VALIDATION=anthropic:...      # optional per-agent override (role name in caps)
    MODEL=openrouter:openai/gpt-6-luna  # any OpenRouter model ID (needs OPENROUTER_API_KEY)
    MODEL=bifrost:bedrock/global.anthropic.claude-haiku-4-5-20251001-v1:0   # through a Bifrost gateway (BIFROST_URL, BIFROST_API_KEY)
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
            **({"temperature": temp} if temp is not None else {}),
            max_retries=retries,
            timeout=60,
            default_headers={"X-Title": "Agentic Workflows Workshop"},
        )

    if spec.startswith("bifrost:"):
        # Bifrost is an LLM gateway with an OpenAI-compatible API. The model name after
        # "bifrost:" is Bifrost's own "provider/model", e.g. bedrock/global.anthropic.claude-...
        from langchain_openai import ChatOpenAI

        url = os.getenv("BIFROST_URL", "").strip().rstrip("/")
        api_key = os.getenv("BIFROST_API_KEY", "").strip()
        if not url or not api_key:
            raise RuntimeError("MODEL uses bifrost: but BIFROST_URL or BIFROST_API_KEY is not set in .env")
        return ChatOpenAI(
            model=spec.split(":", 1)[1],
            base_url=url if url.endswith("/v1") else url + "/v1",
            api_key=api_key,
            **({"temperature": temp} if temp is not None else {}),
            max_retries=retries,
            timeout=60,
        )

    if spec.startswith(("bedrock_converse:", "bedrock:")):
        # Amazon Bedrock through its Converse API. boto3 signs the calls with the Bedrock API key
        # in AWS_BEARER_TOKEN_BEDROCK, or with normal AWS credentials (AWS_ACCESS_KEY_ID, a profile, SSO).
        from botocore.config import Config
        from langchain_aws import ChatBedrockConverse

        if not (os.getenv("AWS_BEARER_TOKEN_BEDROCK", "").strip() or os.getenv("AWS_ACCESS_KEY_ID", "").strip()
                or os.getenv("AWS_PROFILE", "").strip()):
            raise RuntimeError("MODEL uses Bedrock but AWS_BEARER_TOKEN_BEDROCK is not set in .env")
        return ChatBedrockConverse(
            model=spec.split(":", 1)[1],
            region_name=os.getenv("AWS_REGION", "").strip() or "ap-southeast-1",
            **({"temperature": temp} if temp is not None else {}),
            config=Config(retries={"max_attempts": retries + 1, "mode": "adaptive"},
                          read_timeout=60, connect_timeout=10),
        )

    from langchain.chat_models import init_chat_model

    provider = spec.split(":", 1)[0]
    extra: dict = {"max_retries": retries} if provider in RETRYING_PROVIDERS else {}
    if temp is not None:
        extra["temperature"] = temp
    return init_chat_model(spec, **extra)


def get_embeddings(model: str | None = None) -> Embeddings:
    spec = model or get_settings().embedding_model
    if spec == "hash":
        from workshop.rag.embeddings import HashEmbeddings

        return HashEmbeddings()
    from langchain.embeddings import init_embeddings

    return init_embeddings(spec)
