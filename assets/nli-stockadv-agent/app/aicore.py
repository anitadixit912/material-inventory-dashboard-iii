"""Resolve SAP AI Core credentials from a BTP destination and create an LLM.

Single helper: init_llm_from_destination(). Reads the destination named
AICORE_DESTINATION_NAME (default aicore) via the destination service binding,
pushes AICORE_* env vars that gen_ai_hub reads, and returns a LangChain
BaseChatModel via init_llm.
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

import httpx
from gen_ai_hub.proxy import set_proxy_version
from gen_ai_hub.proxy.langchain.init_models import init_llm

logger = logging.getLogger(__name__)

set_proxy_version("gen-ai-hub")

AICORE_DESTINATION_ENV = "AICORE_DESTINATION_NAME"
DEFAULT_AICORE_DESTINATION = "aicore"

TOKEN_TTL = float(os.environ.get("DESTINATION_TOKEN_TTL", "600"))


def _vcap() -> dict[str, Any]:
    raw = os.environ.get("VCAP_SERVICES")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        logger.warning("VCAP_SERVICES is set but not valid JSON")
        return {}


def _first_binding(label: str) -> dict[str, Any] | None:
    bindings = _vcap().get(label) or []
    if not bindings:
        return None
    return (bindings[0] or {}).get("credentials") or {}


@dataclass
class _CachedToken:
    value: str
    expires_at: float

    def expired(self) -> bool:
        return time.monotonic() >= self.expires_at


_xsuaa_token_cache: _CachedToken | None = None


async def _client_credentials_token(
    token_url: str, client_id: str, client_secret: str, timeout: float = 20.0
) -> str:
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            token_url.rstrip("/") + "/oauth/token",
            data={"grant_type": "client_credentials"},
            auth=(client_id, client_secret),
            headers={"Accept": "application/json"},
        )
    r.raise_for_status()
    return r.json()["access_token"]


async def _xsuaa_access_token() -> str:
    global _xsuaa_token_cache
    if _xsuaa_token_cache and not _xsuaa_token_cache.expired():
        return _xsuaa_token_cache.value
    creds = _first_binding("destination") or {}
    if not creds:
        raise RuntimeError(
            "No 'destination' service binding found in VCAP_SERVICES. "
            "Bind a destination service instance to the app."
        )
    token = await _client_credentials_token(
        creds["url"], creds["clientid"], creds["clientsecret"]
    )
    _xsuaa_token_cache = _CachedToken(token, time.monotonic() + TOKEN_TTL)
    return token


async def _fetch_destination_raw(name: str) -> dict[str, Any]:
    creds = _first_binding("destination") or {}
    if not creds:
        raise RuntimeError("No 'destination' service binding found in VCAP_SERVICES.")
    token = await _xsuaa_access_token()
    uri = creds["uri"].rstrip("/")
    url = f"{uri}/destination-configuration/v1/destinations/{name}"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(
            url,
            headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        )
    if r.status_code >= 400:
        raise RuntimeError(
            f"Destination service returned {r.status_code} for '{name}': {r.text}"
        )
    return r.json()


async def init_llm_from_destination(
    model_name: str,
    *,
    temperature: float = 0.0,
    max_tokens: int | None = None,
    destination_name: str | None = None,
) -> Any:
    """Resolve AI Core credentials from a BTP destination and return a LangChain LLM.

    Idempotent — skips the destination GET when AICORE_BASE_URL is already set
    (e.g. injected via CF env vars directly in the BTP cockpit or manifest.yml).
    """
    name = destination_name or os.environ.get(AICORE_DESTINATION_ENV, DEFAULT_AICORE_DESTINATION)

    if not os.environ.get("AICORE_BASE_URL"):
        payload = await _fetch_destination_raw(name)
        cfg = payload.get("destinationConfiguration") or {}

        base_url = (cfg.get("URL") or "").rstrip("/")
        client_id = cfg.get("clientId") or ""
        client_secret = cfg.get("clientSecret") or ""
        token_url = cfg.get("tokenServiceURL") or ""
        resource_group = (
            cfg.get("URL.headers.AI-Resource-Group")
            or cfg.get("AI_RESOURCE_GROUP")
            or "default"
        )

        if not (base_url and client_id and client_secret and token_url):
            raise RuntimeError(
                f"Destination '{name}' is missing one of URL / clientId / "
                f"clientSecret / tokenServiceURL. Got keys: {sorted(cfg.keys())}"
            )

        os.environ["AICORE_BASE_URL"] = base_url
        os.environ["AICORE_AUTH_URL"] = token_url
        os.environ["AICORE_CLIENT_ID"] = client_id
        os.environ["AICORE_CLIENT_SECRET"] = client_secret
        os.environ["AICORE_RESOURCE_GROUP"] = resource_group
        logger.info(
            "aicore destination '%s' resolved (base=%s, group=%s)",
            name, base_url, resource_group,
        )

    kwargs: dict[str, Any] = {"temperature": temperature}
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens
    return init_llm(model_name, **kwargs)
