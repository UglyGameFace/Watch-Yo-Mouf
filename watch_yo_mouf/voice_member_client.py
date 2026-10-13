"""Per-request consent/config read from Dank Shield over the authenticated private VLAN.

This read-only API does not run at startup, cache agreements, or admit audio.
A later receiver must additionally have durable fenced ownership and immediate
revocation/withdrawal delivery. Keep capture disabled even on positive checks.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import aiohttp

from .voice_member_wire import (
    CHECK_PATH, MAX_REPLY_BYTES, MemberCheckRejected, check_request_body,
    sign_check_request, verify_check_response,
)

_URL = "http://dankbot:8097" + CHECK_PATH
_ENABLED = {"1", "true", "yes", "on"}


@dataclass(frozen=True, slots=True)
class MemberEligibility:
    consent_current: bool
    policy_matches: bool
    # A positive record check is never permission to connect to a microphone.
    capture_authorized: bool = False


async def read_member_eligibility(
    guild_id: int, member_id: int, channel_id: int,
) -> MemberEligibility | None:
    """Return a fresh, signed diagnostic snapshot or None on any failure."""
    if os.getenv("WATCH_YO_MOUF_BRIDGE_ENABLED", "").strip().lower() not in _ENABLED:
        return None
    secret = os.getenv("WATCH_YO_MOUF_BRIDGE_SECRET", "")
    try:
        body = check_request_body(guild_id, member_id, channel_id)
        headers = sign_check_request(secret, body)
        nonce = headers["X-WYM-Nonce"]
        timeout = aiohttp.ClientTimeout(total=1.5, connect=0.75)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as client:
            async with client.post(
                _URL, data=body,
                headers={**headers, "Content-Type": "application/json"},
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    return None
                if response.content_length is not None and response.content_length > MAX_REPLY_BYTES:
                    return None
                raw = bytearray()
                while len(raw) <= MAX_REPLY_BYTES:
                    # A short StreamReader.read is not EOF; a signed JSON
                    # response can arrive in several network fragments.
                    fragment = await response.content.read(MAX_REPLY_BYTES + 1 - len(raw))
                    if not fragment:
                        break
                    raw.extend(fragment)
                if len(raw) > MAX_REPLY_BYTES:
                    return None
                result = verify_check_response(
                    secret, nonce, body, bytes(raw),
                    response.headers.get("X-WYM-Response-Signature", ""),
                )
                return MemberEligibility(**result)
    except (MemberCheckRejected, asyncio.TimeoutError, TimeoutError,
            aiohttp.ClientError, OSError, ValueError):
        return None
