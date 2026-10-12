"""Read-only voice decode prerequisite probe.

This verifies pinned library availability without opening a Discord voice
connection, accepting audio, or acquiring any monitoring authority. Passing it
does not prove that live DAVE sessions can decode real Discord speech.
"""

from __future__ import annotations

import importlib
import importlib.util
import platform
from dataclasses import dataclass
from pathlib import Path

import discord


@dataclass(frozen=True, slots=True)
class VoiceStackReadiness:
    ready: bool
    reason: str
    davey: bool
    receive_extension: bool
    inbound_dave_decoder: bool
    native_opus_decoder: bool


def _native_opus_decoder_ready() -> bool:
    """Load the pinned bundled libopus and construct a real PCM decoder."""
    if not discord.opus.is_loaded():
        try:
            spec = importlib.util.find_spec("opuslib_next")
            origin = getattr(spec, "origin", None)
            library = {
                "Linux": "libopus.so",
                "Darwin": "libopus.dylib",
                "Windows": "opus.dll",
            }.get(platform.system())
            if not origin or not library:
                return False
            path = Path(origin).resolve().parent / "_native" / library
            if not path.is_file():
                return False
            discord.opus.load_opus(str(path))
        except (ImportError, OSError, RuntimeError, ValueError):
            return False
    if not discord.opus.is_loaded():
        return False
    try:
        decoder = discord.opus.Decoder()
        return decoder is not None
    except (OSError, RuntimeError, TypeError, discord.opus.OpusError):
        return False


def probe_voice_stack() -> VoiceStackReadiness:
    """Check real imports and decoder ABI; never inspect/join voice channels."""
    davey = False
    extension = False
    inbound = False
    try:
        importlib.import_module("davey")
        davey = True
    except (ImportError, OSError):
        pass

    try:
        importlib.import_module("discord.ext.voice_recv")
        extension = True
    except (ImportError, OSError):
        pass

    if extension:
        try:
            opus_module = importlib.import_module("discord.ext.voice_recv.opus")
            decoder = getattr(opus_module, "PacketDecoder", None)
            inbound = decoder is not None and callable(getattr(decoder, "_dave_decrypt", None))
        except (ImportError, OSError):
            pass

    native_opus = _native_opus_decoder_ready()
    if not davey:
        reason = "davey dependency unavailable"
    elif not extension:
        reason = "voice receive extension unavailable"
    elif not inbound:
        reason = "pinned inbound DAVE decoder unavailable"
    elif not native_opus:
        reason = "native Opus PCM decoder unavailable"
    else:
        reason = "dependency and PCM decoder preflight passed; live DAVE unverified"
    return VoiceStackReadiness(
        ready=davey and extension and inbound and native_opus,
        reason=reason,
        davey=davey,
        receive_extension=extension,
        inbound_dave_decoder=inbound,
        native_opus_decoder=native_opus,
    )
