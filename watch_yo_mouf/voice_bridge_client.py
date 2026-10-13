"""On-demand, private Discloud VLAN handshake with actionable, non-secret diagnostics.

This read-only probe cannot authorize voice capture, reveal credentials, or
accept a caller-selected URL. Errors are reduced to known operational stages.
"""

from __future__ import annotations

import asyncio
import errno
import os
import socket

import aiohttp

from .voice_bridge_wire import BridgeRejected, PATH, request_headers, secret_bytes, verify_response

_PRIVATE_URL = "http://dankbot:8097" + PATH
_ENABLED = frozenset({"true", "1", "yes", "on"})
_MAX_RESPONSE_BYTES = 1024


def _connection_error_stage(error: BaseException) -> str:
    """Never echo exception strings: they can contain URLs or internal metadata."""
    underlying = error.os_error if isinstance(error, aiohttp.ClientConnectorError) else error
    if isinstance(underlying, socket.gaierror):
        return "DNS lookup failed (private hostname dankbot)"
    if isinstance(underlying, ConnectionRefusedError) or getattr(underlying, "errno", None) == errno.ECONNREFUSED:
        return "connection refused (Dank Shield listener on port 8097)"
    if getattr(underlying, "errno", None) in {errno.ENETUNREACH, errno.EHOSTUNREACH}:
        return "private VLAN network unreachable"
    return "private network connection failed"


async def private_bridge_status() -> str:
    """Admin-only status string for /watchyo; no voice or durable state is touched."""
    if os.getenv("WATCH_YO_MOUF_BRIDGE_ENABLED", "").strip().lower() not in _ENABLED:
        return "disabled"

    key = os.getenv("WATCH_YO_MOUF_BRIDGE_SECRET", "")
    try:
        secret_bytes(key)
    except BridgeRejected:
        return "configuration error (missing or invalid Watch Yo Mouf bridge secret)"

    try:
        headers = request_headers(key)
        nonce = headers["X-WYM-Nonce"]
        timeout = aiohttp.ClientTimeout(total=1.5, connect=0.75)
        # Never use user-provided hosts, redirects, HTTP proxies, or public endpoints.
        async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as client:
            async with client.get(_PRIVATE_URL, headers=headers, allow_redirects=False) as response:
                if response.status == 401:
                    return "authentication rejected (check both bridge secrets and host clocks)"
                if response.status == 503:
                    return "Dank Shield bridge listener disabled"
                if response.status == 404:
                    return "wrong endpoint (check Dank Shield deployed revision)"
                if response.status == 409:
                    return "replayed request rejected (check bridge time/nonce)"
                if response.status != 200:
                    return f"Dank Shield bridge HTTP {response.status}"

                if response.content_length is not None and response.content_length > _MAX_RESPONSE_BYTES:
                    return "invalid bridge response (oversized)"
                body = await response.content.read(_MAX_RESPONSE_BYTES + 1)
                if len(body) > _MAX_RESPONSE_BYTES:
                    return "invalid bridge response (oversized)"
                signature = response.headers.get("X-WYM-Response-Signature", "")
                if not verify_response(key, nonce, body, signature):
                    return "invalid authenticated bridge response (signature or version)"
                return "authenticated (diagnostics only)"
    except (asyncio.TimeoutError, TimeoutError):
        return "private connection timed out (VLAN or listener unreachable)"
    except aiohttp.ClientConnectorError as exc:
        return _connection_error_stage(exc)
    except (aiohttp.ClientError, OSError) as exc:
        if isinstance(exc, OSError):
            return _connection_error_stage(exc)
        return "private bridge transport error"
    except (BridgeRejected, ValueError):
        return "invalid bridge request"
