"""Turn exceptions into short, friendly messages, so a failed turn never ends the session.

    from workshop.errors import explain, show_error

    try:
        graph.invoke(...)
    except Exception as exc:
        show_error(exc)          # prints what went wrong and what to do next

Errors are recognised by class name and HTTP status code, so this module does not
need to import any provider SDK (OpenAI, Anthropic, OpenRouter, ...).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class Explanation:
    kind: str          # short machine-readable label, e.g. "rate_limit"
    headline: str      # one sentence: what happened
    advice: str        # one or two sentences: what to do now
    retryable: bool    # True if trying the same thing again may work
    detail: str = ""   # the provider's own message, trimmed

    @property
    def http_status(self) -> int:
        """Status code to return from the HTTP API (serve.py)."""
        return {"rate_limit": 429, "auth": 502, "model_not_found": 502, "bad_request": 502,
                "provider_down": 503, "network": 503, "gov_api": 503, "database": 503}.get(self.kind, 500)


def _chain(exc: BaseException) -> list[BaseException]:
    """The exception plus everything it was raised from (LangChain wraps provider errors)."""
    seen, out = set(), []
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        out.append(exc)
        exc = exc.__cause__ or exc.__context__
    return out


def _status(exc: BaseException) -> int | None:
    for e in _chain(exc):
        code = getattr(e, "status_code", None) or getattr(getattr(e, "response", None), "status_code", None)
        if isinstance(code, int):
            return code
    return None


def _names(exc: BaseException) -> str:
    return " ".join(type(e).__name__ for e in _chain(exc))


def _provider_detail(exc: BaseException) -> str:
    # Structured error body first (OpenAI-compatible APIs, including OpenRouter) ...
    for e in _chain(exc):
        body = getattr(e, "body", None)
        if isinstance(body, dict):
            err = body.get("error", body) if isinstance(body.get("error", body), dict) else body
            raw = (err.get("metadata") or {}).get("raw") if isinstance(err.get("metadata"), dict) else None
            msg = raw or err.get("message")
            if msg and str(msg).strip().lower() != "provider returned error":
                return str(msg).strip()[:240]
    # ... then whatever the exception's text says.
    text = str(exc)
    for pattern in (r"""['"]raw['"]:\s*['"]([^'"]+)""", r"""['"]message['"]:\s*['"]([^'"]+)"""):
        m = re.search(pattern, text)
        if m and m.group(1).strip().lower() != "provider returned error":
            return m.group(1).strip()[:240]
    return text.splitlines()[0][:240] if text else ""


def explain(exc: BaseException) -> Explanation:
    names = _names(exc)
    status = _status(exc)
    detail = _provider_detail(exc)

    def has(*words: str) -> bool:
        return any(w in names for w in words)

    if status == 429 or has("RateLimit"):
        return Explanation(
            "rate_limit", "The model is busy: the provider is rate-limiting requests right now.",
            "Wait 10 to 30 seconds and try again. Free models share one limit across everyone; "
            "a paid model or your own provider key avoids this.", True, detail)
    if status in (401, 403) or has("Authentication", "PermissionDenied"):
        return Explanation(
            "auth", "The model provider rejected your API key.",
            "Check the key for your provider in .env (for example OPENROUTER_API_KEY), "
            "then run `make up` so the container picks it up.", False, detail)
    if status == 404 or (has("NotFound") and "model" in str(exc).lower()):
        return Explanation(
            "model_not_found", "The model in MODEL wasn't found at the provider.",
            "Check the MODEL line in .env for a typo, then run `make up`.", False, detail)
    if status in (400, 422) or has("BadRequest", "UnprocessableEntity"):
        return Explanation(
            "bad_request", "The model rejected the request.",
            "This model may not support tool calling or structured output. Try another MODEL in .env.", False, detail)
    if (status and status >= 500) or has("InternalServer", "ServiceUnavailable", "Overloaded"):
        return Explanation(
            "provider_down", "The model provider had a temporary problem.",
            "Try again in a few seconds.", True, detail)
    if has("APIConnectionError", "APITimeoutError", "ConnectError", "ConnectTimeout", "ReadTimeout",
           "TimeoutException", "TimeoutError", "RemoteProtocolError"):
        return Explanation(
            "network", "Couldn't reach the model provider.",
            "Check your internet connection and try again. No internet? Set MODEL=mock in .env to keep going offline.",
            True, detail)
    if has("GovApiError"):
        return Explanation(
            "gov_api", "The Mock Gov API didn't respond.",
            "Run `make up` to restart it, then try again.", True, detail)
    if has("OperationalError", "PoolTimeout", "InterfaceError"):
        return Explanation(
            "database", "Couldn't reach the database.",
            "Run `make up`. If it still fails, `make logs` shows why the db container stopped.", True, detail)
    if has("GraphRecursionError"):
        return Explanation(
            "recursion", "The agent went round in circles and was stopped.",
            "Try again, or rephrase the question more specifically.", True, detail)
    if has("ModuleNotFoundError", "ImportError"):
        return Explanation(
            "missing_package", "A Python package is missing.",
            "Run `make up-build` to rebuild the container with every package installed.", False, detail)
    if has("ToolNotAllowed"):
        return Explanation(
            "config", "An agent is wired to a tool it isn't allowed to use.",
            "Add the tool to TOOL_ALLOWLIST in workshop/guardrails/tool_policy.py, or remove it from the agent.",
            False, detail)
    if "API_KEY" in str(exc) or "MODEL" in str(exc) or has("ValueError") and "provider" in str(exc).lower():
        return Explanation("config", "The model settings in .env are incomplete.",
                           "Fix .env as described below, then run `make up`.", False, detail)
    return Explanation(
        "unexpected", f"Something went wrong ({type(exc).__name__}).",
        "Try again. If it keeps happening, show this message to a facilitator.", True, detail)


def show_error(exc: BaseException, console=None, can_retry_with_enter: bool = False) -> Explanation:
    """Print a friendly error panel and return the explanation."""
    from rich.console import Console
    from rich.panel import Panel

    console = console or Console()
    e = explain(exc)
    lines = [f"[bold]{e.headline}[/]", e.advice]
    if e.detail:
        lines.append(f"[dim]Details: {e.detail}[/]")
    if can_retry_with_enter and e.retryable:
        lines.append("[cyan]Press Enter to retry, or type a new question.[/]")
    console.print(Panel("\n".join(lines), title="couldn't finish that", border_style="red"))
    return e
