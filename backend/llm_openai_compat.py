from __future__ import annotations

import json
from typing import Any, AsyncIterator, Dict, Optional

import httpx


def _join_url(base_url: str, path: str) -> str:
    base = (base_url or "").rstrip("/")
    p = path.lstrip("/")
    return f"{base}/{p}"


def _auth_headers(api_key: str) -> Dict[str, str]:
    api_key = (api_key or "").strip()
    if not api_key:
        return {}
    return {"Authorization": f"Bearer {api_key}"}


async def stream_chat_completions(
    *,
    base_url: str,
    api_key: str,
    model: str,
    messages: list[dict[str, Any]],
    temperature: Optional[float] = None,
    top_p: Optional[float] = None,
) -> AsyncIterator[str]:
    """Stream tokens from OpenAI-compatible /v1/chat/completions.

    Yields text deltas.
    """
    url = _join_url(base_url, "/chat/completions")

    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": True,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if top_p is not None:
        payload["top_p"] = top_p

    headers = {
        "Content-Type": "application/json",
        **_auth_headers(api_key),
    }

    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, headers=headers, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                # OpenAI stream is SSE-like but without Content-Type enforcement
                if line.startswith("data:"):
                    data = line[len("data:") :].strip()
                else:
                    data = line.strip()

                if data == "[DONE]":
                    break

                try:
                    obj = json.loads(data)
                except Exception:
                    continue

                try:
                    delta = obj["choices"][0]["delta"]
                    content = delta.get("content")
                    if content:
                        yield content
                except Exception:
                    continue
