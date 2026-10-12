"""On-demand, opt-in, read-only VLAN handshake with Dank Shield.

Does not carry user consent or start voice capture. Never logs credentials.
"""
from __future__ import annotations

import os

import aiohttp

from .voice_bridge_wire import BridgeRejected, PATH, request_headers, secret_bytes, verify_response

_PRIVATE_URL = "http://dankbot:8097" + PATH


async def private_bridge_status() -> str:
    if os.getenv("WATCH_YO_MOUF_BRIDGE_ENABLED", "").strip().lower() not in {"true", "1", "yes", "on"}:
        return "disabled"
    key = os.getenv("WATCH_YO_MOUF_BRIDGE_SECRET", "")
    try:
        secret_bytes(key)
        headers = request_headers(key)
        nonce = headers["X-WYM-Nonce"]
        timeout = aiohttp.ClientTimeout(total=1.5, connect=0.75)
        # Private Discloud VLAN address, never a user supplied or public URL.
        async with aiohttp.ClientSession(timeout=timeout) as client:
            async with client.get(_PRIVATE_URL, headers=headers, allow_redirects=False) as response:
                if response.status != 200:
                    return "unavailable"
                if response.content_length is not None and response.content_length > 1024:
                    return "unavailable"
                body = await response.content.read(1025)
                if len(body) > 1024:
                    return "unavailable"
                verified = verify_response(
                    key, nonce, body, response.headers.get("X-WYM-Response-Signature", "")
                )
                return "authenticated (diagnostics only)" if verified else "unavailable"
    except (BridgeRejected, aiohttp.ClientError, TimeoutError, OSError, ValueError):
        return "unavailable"
