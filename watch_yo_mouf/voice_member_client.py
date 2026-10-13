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


@dataclass(frozen=True, slots=True)
class MemberEligibilityProbe:
    """Sanitized outcome for a staff-initiated private network canary."""
    eligibility: MemberEligibility | None
    stage: str


def _status_stage(code: int) -> str:
    """HTTP stages have fixed labels; never reflect a server body or exception."""
    return {
        401: "POST rejected (HTTP 401: credentials or clock)",
        403: "POST refused (HTTP 403)",
        404: "POST endpoint missing (HTTP 404: deployed Dank Shield revision)",
        409: "POST nonce replay rejected (HTTP 409)",
        413: "POST request oversized (HTTP 413)",
        503: "POST service disabled (HTTP 503)",
    }.get(code, f"POST server returned HTTP {code}")


async def probe_member_eligibility(
    guild_id: int, member_id: int, channel_id: int,
) -> MemberEligibilityProbe:
    """Bounded on-demand self-check only; never gives receiver authorization.

    The signed GET /v1/status handshake is intentionally separate and faster.
    This POST may read current guild config and member agreement from Supabase,
    so its capped 6s timeout is different from the GET's 1.5s. The caller
    already deferred the Discord interaction. No member data is logged.
    """
    if os.getenv("WATCH_YO_MOUF_BRIDGE_ENABLED", "").strip().lower() not in _ENABLED:
        return MemberEligibilityProbe(None, "POST disabled in Watch Yo Mouf")

    secret = os.getenv("WATCH_YO_MOUF_BRIDGE_SECRET", "")
    try:
        body = check_request_body(guild_id, member_id, channel_id)
        headers = sign_check_request(secret, body)
        nonce = headers["X-WYM-Nonce"]
    except MemberCheckRejected:
        return MemberEligibilityProbe(None, "POST invalid local request or secret")

    try:
        timeout = aiohttp.ClientTimeout(total=6.0, connect=1.5)
        async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as client:
            async with client.post(
                _URL, data=body,
                headers={**headers, "Content-Type": "application/json"},
                allow_redirects=False,
            ) as response:
                if response.status != 200:
                    return MemberEligibilityProbe(None, _status_stage(response.status))
                if response.content_length is not None and response.content_length > MAX_REPLY_BYTES:
                    return MemberEligibilityProbe(None, "POST signed reply oversized")
                raw = bytearray()
                while len(raw) <= MAX_REPLY_BYTES:
                    # A short StreamReader.read is not EOF; JSON can be fragmented.
                    fragment = await response.content.read(MAX_REPLY_BYTES + 1 - len(raw))
                    if not fragment:
                        break
                    raw.extend(fragment)
                if len(raw) > MAX_REPLY_BYTES:
                    return MemberEligibilityProbe(None, "POST signed reply oversized")
                try:
                    result = verify_check_response(
                        secret, nonce, body, bytes(raw),
                        response.headers.get("X-WYM-Response-Signature", ""),
                    )
                except MemberCheckRejected:
                    return MemberEligibilityProbe(None, "POST signed reply invalid (signature or schema)")
                return MemberEligibilityProbe(MemberEligibility(**result), "POST authenticated")
    except (asyncio.TimeoutError, TimeoutError):
        return MemberEligibilityProbe(None, "POST timed out (private service or consent storage)")
    except aiohttp.ClientConnectorError as exc:
        # The error is never surfaced, only a bounded stage without host/secret.
        if isinstance(exc.os_error, OSError) and getattr(exc.os_error, "errno", None) == 111:
            return MemberEligibilityProbe(None, "POST connection refused (private port 8097)")
        return MemberEligibilityProbe(None, "POST VLAN connection failed")
    except (aiohttp.ClientError, OSError):
        return MemberEligibilityProbe(None, "POST private transport failed")


async def read_member_eligibility(
    guild_id: int, member_id: int, channel_id: int,
) -> MemberEligibility | None:
    """Compatibility wrapper for future audio safety gates, still fail closed."""
    return (await probe_member_eligibility(guild_id, member_id, channel_id)).eligibility
