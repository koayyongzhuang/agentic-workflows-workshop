"""HTTP client for the Mock Gov Service.

If GOV_API_URL is set (docker compose sets it), requests go over the network.
Otherwise the FastAPI app runs in-process, so nothing else needs to be started.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

import httpx

from workshop.config import get_settings


class GovApiError(RuntimeError):
    pass


@lru_cache(maxsize=4)
def _client(base_url: str | None) -> httpx.Client:
    if base_url:
        return httpx.Client(base_url=base_url, timeout=10)
    from fastapi.testclient import TestClient

    from workshop.gov_api.app import app

    return TestClient(app)


def call(method: str, path: str, **kwargs: Any) -> Any:
    url = get_settings().gov_api_url
    client = _client(url)
    try:
        resp = client.request(method, path, **kwargs)
    except httpx.HTTPError as exc:
        raise GovApiError(
            f"The Mock Gov API at {url or 'in-process'} is not reachable ({type(exc).__name__}). "
            "Is the gov-api container running? Try `make up`."
        ) from exc
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail")
        except ValueError:
            detail = resp.text
        raise GovApiError(f"{resp.status_code}: {detail}")
    return resp.json()
