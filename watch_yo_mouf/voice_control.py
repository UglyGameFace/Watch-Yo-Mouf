"""Signed, fail-closed control messages for a future Dank Shield handoff.

This is a transport-neutral wire contract, NOT a network listener or authority
to capture audio. Dank Shield remains the only writer of policy and agreement.
A monitoring worker must separately prove exclusive receiver ownership,
current voice-specific consent, notification, and DAVE readiness before audio.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import time
from dataclasses import dataclass
from typing import Any, Mapping

VERSION = 1
MAX_MESSAGE_BYTES = 4096
MAX_TTL_SECONDS = 30
MAX_CLOCK_SKEW_SECONDS = 5
MAX_GUILDS = 20000
_MAX_SNOWFLAKE = (1 << 64) - 1

_COMMON = frozenset({"version", "action", "guild_id", "sequence", "issued_at", "expires_at", "nonce"})
_FIELDS = {
    "policy": _COMMON | {"channel_id", "enabled"},
    "stop": _COMMON,
    "revoke": _COMMON | {"member_id"},
}


class ControlMessageRejected(ValueError):
    """Malformed, unauthenticated, stale, or out-of-order control message."""


@dataclass(frozen=True, slots=True)
class ControlMessage:
    action: str
    guild_id: int
    sequence: int
    expires_at: int
    channel_id: int = 0
    enabled: bool = False
    member_id: int = 0


@dataclass(frozen=True, slots=True)
class GuildControlStatus:
    last_sequence: int
    desired_enabled: bool
    channel_id: int
    halted: bool
    last_expires_at: int


def _positive_int(value: Any, name: str, maximum: int) -> int:
    if type(value) is not int or value <= 0 or value > maximum:
        raise ControlMessageRejected(f"invalid {name}")
    return value


def _validated_payload(payload: Any, now: int) -> ControlMessage:
    if not isinstance(payload, dict):
        raise ControlMessageRejected("invalid payload")
    action = payload.get("action")
    if type(action) is not str or action not in _FIELDS or set(payload) != _FIELDS[action]:
        raise ControlMessageRejected("invalid action or fields")
    if type(payload["version"]) is not int or payload["version"] != VERSION:
        raise ControlMessageRejected("unsupported control version")

    guild_id = _positive_int(payload["guild_id"], "guild_id", _MAX_SNOWFLAKE)
    sequence = _positive_int(payload["sequence"], "sequence", (1 << 63) - 1)
    issued_at = _positive_int(payload["issued_at"], "issued_at", (1 << 63) - 1)
    expires_at = _positive_int(payload["expires_at"], "expires_at", (1 << 63) - 1)
    if not (issued_at <= now + MAX_CLOCK_SKEW_SECONDS and
            issued_at < expires_at <= issued_at + MAX_TTL_SECONDS and
            now < expires_at):
        raise ControlMessageRejected("expired or invalid control lifetime")
    nonce = payload["nonce"]
    if (type(nonce) is not str or len(nonce) != 32 or
            any(c not in "0123456789abcdef" for c in nonce)):
        raise ControlMessageRejected("invalid control nonce")

    channel_id = 0
    enabled = False
    member_id = 0
    if action == "policy":
        channel_id = _positive_int(payload["channel_id"], "channel_id", _MAX_SNOWFLAKE)
        if type(payload["enabled"]) is not bool:
            raise ControlMessageRejected("invalid enabled flag")
        enabled = payload["enabled"]
    if action == "revoke":
        member_id = _positive_int(payload["member_id"], "member_id", _MAX_SNOWFLAKE)
    return ControlMessage(
        action=action,
        guild_id=guild_id,
        sequence=sequence,
        expires_at=expires_at,
        channel_id=channel_id,
        enabled=enabled,
        member_id=member_id,
    )


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(dict(payload), sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _secret(key: bytes) -> bytes:
    if type(key) is not bytes or len(key) < 32:
        raise ControlMessageRejected("control secret unavailable")
    return key


def new_control_payload(
    *, action: str, guild_id: int, sequence: int, now: int | None = None,
    ttl_seconds: int = 15, channel_id: int = 0, enabled: bool = False,
    member_id: int = 0,
) -> dict[str, Any]:
    """Create a correctly shaped event; call from the authoritative writer only."""
    at = int(time.time()) if now is None else now
    if type(at) is not int or type(ttl_seconds) is not int or not 1 <= ttl_seconds <= MAX_TTL_SECONDS:
        raise ControlMessageRejected("invalid control lifetime")
    payload: dict[str, Any] = {
        "version": VERSION, "action": action, "guild_id": guild_id,
        "sequence": sequence, "issued_at": at, "expires_at": at + ttl_seconds,
        "nonce": secrets.token_hex(16),
    }
    if action == "policy":
        payload.update({"channel_id": channel_id, "enabled": enabled})
    elif action == "revoke":
        payload["member_id"] = member_id
    _validated_payload(payload, at)
    return payload


def sign_control(payload: Mapping[str, Any], key: bytes, *, now: int | None = None) -> bytes:
    """Produce canonical authenticated JSON; no transcript or audio fields allowed."""
    at = int(time.time()) if now is None else now
    _validated_payload(dict(payload), at)
    signature = hmac.new(_secret(key), _canonical(payload), hashlib.sha256).hexdigest()
    raw = _canonical({"payload": dict(payload), "signature": signature})
    if len(raw) > MAX_MESSAGE_BYTES:
        raise ControlMessageRejected("control envelope too large")
    return raw


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    obj: dict[str, Any] = {}
    for key, value in pairs:
        if key in obj:
            raise ControlMessageRejected("duplicate control field")
        obj[key] = value
    return obj


def verify_control(raw: bytes, key: bytes, *, now: int | None = None) -> ControlMessage:
    """Authenticate before returning any executable control-state transition."""
    secret = _secret(key)
    if type(raw) is not bytes or not 0 < len(raw) <= MAX_MESSAGE_BYTES:
        raise ControlMessageRejected("invalid control envelope")
    try:
        envelope = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise ControlMessageRejected("invalid control encoding") from exc
    if not isinstance(envelope, dict) or set(envelope) != {"payload", "signature"}:
        raise ControlMessageRejected("invalid control envelope fields")
    payload, signature = envelope["payload"], envelope["signature"]
    if (not isinstance(payload, dict) or type(signature) is not str or len(signature) != 64 or
            any(char not in "0123456789abcdef" for char in signature)):
        raise ControlMessageRejected("invalid control signature")
    expected = hmac.new(secret, _canonical(payload), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise ControlMessageRejected("invalid control signature")
    at = int(time.time()) if now is None else now
    return _validated_payload(payload, at)


class ControlGate:
    """In-memory ordered state, not a distributed lease and not audio admission.

    A stop or revocation latches the guild closed. Re-enablement requires a
    future explicit authoritative reconciliation protocol and is unsupported.
    Restart resets to disabled and demands newly authenticated control state.
    """

    def __init__(self) -> None:
        self._guilds: dict[int, GuildControlStatus] = {}

    def apply_signed(
        self, raw: bytes, key: bytes, *, now: int | None = None,
    ) -> GuildControlStatus:
        """Verify the HMAC, lifetime and schema before changing any state."""
        message = verify_control(raw, key, now=now)
        current = self._guilds.get(message.guild_id)
        if current and message.sequence <= current.last_sequence:
            raise ControlMessageRejected("stale or replayed control sequence")
        if current is None and len(self._guilds) >= MAX_GUILDS:
            raise ControlMessageRejected("control state capacity reached")
        if message.action == "policy":
            # This is only the desired policy. It cannot activate a receiver.
            halted = current.halted if current is not None else False
            status = GuildControlStatus(
                last_sequence=message.sequence,
                desired_enabled=message.enabled and not halted,
                channel_id=message.channel_id,
                halted=halted or not message.enabled,
                last_expires_at=message.expires_at,
            )
        else:
            # Even one member withdrawing closes the entire room until a fresh
            # reconciled authorization protocol exists. No stale consent grant.
            status = GuildControlStatus(
                last_sequence=message.sequence,
                desired_enabled=False,
                channel_id=current.channel_id if current else 0,
                halted=True,
                last_expires_at=message.expires_at,
            )
        self._guilds[message.guild_id] = status
        return status

    def status(self, guild_id: int, *, now: int | None = None) -> GuildControlStatus | None:
        status = self._guilds.get(guild_id)
        at = int(time.time()) if now is None else now
        if status is None or at >= status.last_expires_at:
            return None
        return status

    @staticmethod
    def admits_audio(*_: object, **__: object) -> bool:
        """No microphone is authorized until real consent+distributed lease exist."""
        return False
