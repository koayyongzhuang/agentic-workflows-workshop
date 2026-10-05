"""Errors are explained, and a failed chat turn can be retried without restarting."""

import httpx
import openai

from workshop import cli
from workshop.errors import explain
from workshop.gov_api import client as gov_client


def _rate_limit_error() -> Exception:
    req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    body = {"error": {"message": "Provider returned error", "code": 429,
                      "metadata": {"raw": "model is temporarily rate-limited upstream"}}}
    return openai.RateLimitError("Error code: 429", response=httpx.Response(429, request=req, json=body), body=body)


def test_rate_limit_is_explained_and_retryable():
    e = explain(_rate_limit_error())
    assert e.kind == "rate_limit" and e.retryable and e.http_status == 429
    assert "rate-limited upstream" in e.detail


def test_bad_key_is_not_retryable():
    req = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    e = explain(openai.AuthenticationError("bad key", response=httpx.Response(401, request=req), body=None))
    assert e.kind == "auth" and not e.retryable


def test_chat_loop_survives_an_error_and_retries_on_enter(monkeypatch):
    typed = iter(["Am I eligible?", "", "/exit"])
    monkeypatch.setattr(cli.console, "input", lambda prompt="": next(typed))
    calls = []

    def ask(question, thread, resume=False):
        calls.append((question, resume))
        if len(calls) == 1:
            raise _rate_limit_error()

    cli.chat_loop(ask, lambda: None)  # must not raise
    assert calls == [("Am I eligible?", False), ("Am I eligible?", True)]


def test_gov_api_down_becomes_a_tool_message(monkeypatch):
    class Down:
        def request(self, *a, **k):
            raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(gov_client, "_client", lambda url: Down())
    from workshop.tools import get_scheme_details, list_schemes

    assert "not reachable" in list_schemes.invoke({})
    assert "not reachable" in get_scheme_details.invoke({"scheme": "SMG"})
