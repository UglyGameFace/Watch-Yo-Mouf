"""Synthetic-only private RivaL Intelligence moderation probe.

No voice capture, transcript collector or member-speech API is exposed here.
Production speech forwarding must wait for durable receiver leases, explicit
speaker-level consent and immediate revocation.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass

import aiohttp

_URL = "http://rival-llm:8765/v1/moderate"
_ENABLED = frozenset({"true", "yes", "on", "1"})
_MAX_REPLY = 2048
_SAMPLE = {"version": 1, "transcript": "I am discussing my own identity.", "context": []}
_ALLOWED_DECISIONS = frozenset({"allow", "review"})
_ALLOWED_CATEGORIES = frozenset({
    "none", "targeted_harassment", "sexual_harassment",
    "graphic_sexual_content", "threat", "unclear",
})


@dataclass(frozen=True, slots=True)
class AIProbe:
    status: str
    decision: str = ""
    category: str = ""


def _valid_reply(reply: object) -> bool:
    if not isinstance(reply, dict) or set(reply) != {
        "model", "decision", "category", "confidence",
        "advisory_only", "calibrated", "enforcement_authorized"
    }:
        return False
    if not isinstance(reply["model"], str) or not 1 <= len(reply["model"]) <= 120:
        return False
    if reply["decision"] not in _ALLOWED_DECISIONS:
        return False
    if reply["category"] not in _ALLOWED_CATEGORIES:
        return False
    if reply["confidence"] not in ("low", "medium", "high"):
        return False
    if reply["advisory_only"] is not True or reply["calibrated"] is not False:
        return False
    if reply["enforcement_authorized"] is not False:
        return False
    return (
        (reply["decision"] == "allow" and reply["category"] == "none")
        or (reply["decision"] == "review" and reply["category"] != "none")
    )


async def probe_private_ai() -> AIProbe:
    """One explicitly clicked admin probe. Always use known synthetic text."""
    if os.getenv("WATCH_YO_MOUF_LLM_VOICE_ENABLED", "").strip().lower() not in _ENABLED:
        return AIProbe("disabled (Watch Yo Mouf configuration)")
    token = os.getenv("WATCH_YO_MOUF_LLM_VOICE_TOKEN", "")
    if len(token) < 32 or len(token) > 256:
        return AIProbe("configuration error (voice-scoped token missing or invalid)")
    timeout = aiohttp.ClientTimeout(total=75.0, connect=1.5)
    try:
        async with aiohttp.ClientSession(timeout=timeout, trust_env=False) as client:
            async with client.post(
                _URL, json=_SAMPLE,
                headers={"Authorization": "Bearer " + token},
                allow_redirects=False,
            ) as response:
                if response.status == 401:
                    return AIProbe("authentication rejected (voice token mismatch)")
                if response.status == 429:
                    return AIProbe("model busy (request skipped, no queue or retry)")
                if response.status == 503:
                    return AIProbe("LLM unavailable or voice endpoint disabled")
                if response.status == 404:
                    return AIProbe("moderation endpoint missing on deployed LLM")
                if response.status != 200:
                    return AIProbe("LLM HTTP " + str(response.status))
                if response.content_length is not None and response.content_length > _MAX_REPLY:
                    return AIProbe("invalid private AI reply")
                raw = await response.content.read(_MAX_REPLY + 1)
                if len(raw) > _MAX_REPLY:
                    return AIProbe("invalid private AI reply")
                try:
                    reply = __import__("json").loads(raw)
                except (ValueError, UnicodeError):
                    return AIProbe("invalid private AI reply")
                if not _valid_reply(reply):
                    return AIProbe("invalid private AI schema")
                return AIProbe("authenticated (synthetic test only)",
                               reply["decision"], reply["category"])
    except (asyncio.TimeoutError, TimeoutError):
        return AIProbe("LLM inference timed out")
    except aiohttp.ClientConnectorError:
        return AIProbe("private VLAN LLM unreachable")
    except (aiohttp.ClientError, OSError, ValueError):
        return AIProbe("private AI transport unavailable")
