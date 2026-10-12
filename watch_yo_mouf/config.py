"""Strict, side-effect-free runtime settings for the standalone Discord bot."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping


class ConfigurationError(ValueError):
    """A required setting is absent or invalid (without revealing credentials)."""


@dataclass(frozen=True, slots=True)
class Settings:
    token: str
    shard_count: int | None
    shard_ids: tuple[int, ...] | None
    sync_commands: bool


def _positive_int(value: str, name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ConfigurationError(f"{name} must be an integer") from exc
    if parsed <= 0:
        raise ConfigurationError(f"{name} must be positive")
    return parsed


def _bool(value: str | None, name: str) -> bool:
    cleaned = str(value or "").strip().lower()
    if cleaned in {"", "0", "false", "no", "off"}:
        return False
    if cleaned in {"1", "true", "yes", "on"}:
        return True
    raise ConfigurationError(f"{name} must be true or false")


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    env = environ if environ is not None else os.environ
    token = str(env.get("WATCH_YO_MOUF_TOKEN", "")).strip()
    if not token:
        raise ConfigurationError("WATCH_YO_MOUF_TOKEN is required")

    count_raw = str(env.get("WATCH_YO_MOUF_SHARD_COUNT", "")).strip()
    ids_raw = str(env.get("WATCH_YO_MOUF_SHARD_IDS", "")).strip()
    shard_count = _positive_int(count_raw, "WATCH_YO_MOUF_SHARD_COUNT") if count_raw else None
    shard_ids = None
    if ids_raw:
        if shard_count is None:
            raise ConfigurationError("WATCH_YO_MOUF_SHARD_COUNT is required with SHARD_IDS")
        try:
            shard_ids = tuple(int(entry.strip()) for entry in ids_raw.split(","))
        except ValueError as exc:
            raise ConfigurationError("WATCH_YO_MOUF_SHARD_IDS must be comma-separated integers") from exc
        if len(shard_ids) != len(set(shard_ids)) or any(i < 0 or i >= shard_count for i in shard_ids):
            raise ConfigurationError("WATCH_YO_MOUF_SHARD_IDS must be unique and in shard range")

    return Settings(
        token=token,
        shard_count=shard_count,
        shard_ids=shard_ids,
        sync_commands=_bool(env.get("WATCH_YO_MOUF_SYNC_COMMANDS"), "WATCH_YO_MOUF_SYNC_COMMANDS"),
    )
