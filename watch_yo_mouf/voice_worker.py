"""Private opt-in Vosk speech-recognition worker for Dank Shield's DAVE receiver.

No Discord microphone is opened here. Dank Shield performs consent admission,
speaker mapping and audio segmentation, then sends bounded 16 kHz mono PCM.
Worker reads no content from untrusted URLs, retains no audio or transcripts,
and never sends Discord messages or performs sanctions.
"""
from __future__ import annotations

import asyncio
import importlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any

from aiohttp import web

from .watch_audio_wire import (
    AudioWireRejected, MAX_AUDIO_BYTES, PATH, response_body,
    response_signature, verify_audio_request,
)

LOG = logging.getLogger(__name__)
_TRUE = {"1", "true", "on", "yes"}
_PORT = 8098
_MAX_NONCES = 4096
_ENGLISH_MODEL = "vosk-small-en-us-0.15"


def _enabled() -> bool:
    return os.getenv("WATCH_YO_MOUF_STT_ENABLED", "").strip().lower() in _TRUE


def _secret() -> str:
    return os.getenv("WATCH_YO_MOUF_AUDIO_SECRET", "")


def _recognize(model: Any, pcm: bytes) -> str:
    """Perform bounded inference off the gateway event loop, no persistent WAV."""
    vosk = importlib.import_module("vosk")
    recognizer = vosk.KaldiRecognizer(model, 16000)
    # Only one 16 kHz mono segment arrives, at most 16 seconds in memory.
    # Feed finite chunks to avoid an unbounded recognizer input allocation.
    for offset in range(0, len(pcm), 16_000):
        recognizer.AcceptWaveform(pcm[offset:offset + 16_000])
    result = json.loads(recognizer.FinalResult())
    text = result.get("text", "") if type(result) is dict else ""
    if type(text) is not str:
        raise ValueError("invalid Vosk transcript type")
    return text.strip()[:1200]


def _model_from_settings() -> Any:
    """Use a mounted known model or Vosk's normal official English model cache."""
    vosk = importlib.import_module("vosk")
    vosk.SetLogLevel(-1)
    path = os.getenv("WATCH_YO_MOUF_STT_MODEL_PATH", "").strip()
    if path:
        from pathlib import Path
        directory = Path(path)
        if not directory.is_dir() or directory.is_symlink():
            raise RuntimeError("configured STT model directory is unavailable")
        return vosk.Model(model_path=str(directory))
    # Vosk's built-in en-us model selector downloads the ~40MB small
    # Apache-2.0 model into its cache once, then reuses it on future calls.
    # Readiness remains false if download/init cannot finish.
    return vosk.Model(lang="en-us")


@dataclass(slots=True)
class VoiceSTTWorker:
    runner: web.AppRunner | None = None
    model: Any = None
    state: str = "disabled"
    model_task: asyncio.Task[None] | None = None
    request_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    used_nonces: dict[str, int] = field(default_factory=dict)

    def claim_nonce(self, nonce: str, now: int) -> bool:
        for key, expires in tuple(self.used_nonces.items()):
            if expires < now:
                self.used_nonces.pop(key, None)
        if nonce in self.used_nonces or len(self.used_nonces) >= _MAX_NONCES:
            return False
        self.used_nonces[nonce] = now + 31
        return True

    async def prime(self) -> None:
        if self.model is not None:
            return
        self.state = "loading"
        try:
            self.model = await asyncio.to_thread(_model_from_settings)
        except (ImportError, OSError, RuntimeError, ValueError):
            self.state = "model_unavailable"
            LOG.warning("Watch Yo Mouf STT model unavailable; private audio fails closed")
            return
        self.state = "ready"
        LOG.info("Watch Yo Mouf local STT model ready (no audio capture)")

    async def handle_audio(self, request: web.Request) -> web.Response:
        if not _enabled():
            return web.Response(status=503)
        if request.content_length is None or request.content_length > MAX_AUDIO_BYTES:
            return web.Response(status=413)
        try:
            raw = await request.read()
        except web.HTTPRequestEntityTooLarge:
            return web.Response(status=413)
        if len(raw) > MAX_AUDIO_BYTES:
            return web.Response(status=413)
        try:
            guild_id, speaker_id, channel_id, nonce = verify_audio_request(
                _secret(), request.headers, raw,
            )
        except AudioWireRejected:
            return web.Response(status=401)
        # Identity was authenticated. The worker does not decide consent or
        # infer it from the headers; Dank Shield owns current admission.
        del guild_id, speaker_id, channel_id
        if not self.claim_nonce(nonce, int(time.time())):
            return web.Response(status=409)
        if self.model is None or self.state != "ready":
            return web.Response(status=503)
        if self.request_lock.locked():
            return web.Response(status=429)
        async with self.request_lock:
            try:
                transcript = await asyncio.wait_for(
                    asyncio.to_thread(_recognize, self.model, raw),
                    timeout=15.0,
                )
                body = response_body(transcript)
                signature = response_signature(_secret(), nonce, raw, body)
            except (asyncio.TimeoutError, OSError, ValueError, RuntimeError,
                    AudioWireRejected):
                LOG.warning("Watch Yo Mouf local STT segment failed safely")
                return web.Response(status=503)
            return web.Response(
                body=body, content_type="application/json",
                headers={
                    "X-WYM-Response-Signature": signature,
                    "Cache-Control": "no-store",
                },
            )

    async def start(self) -> bool:
        if not _enabled():
            self.state = "disabled"
            return False
        from .watch_audio_wire import _secret as check_secret
        check_secret(_secret())  # Fail before opening the VLAN port.
        app = web.Application(client_max_size=MAX_AUDIO_BYTES + 1024)
        app.router.add_post(PATH, self.handle_audio)
        runner = web.AppRunner(app, access_log=None)
        await runner.setup()
        try:
            await web.TCPSite(runner, host="0.0.0.0", port=_PORT).start()
        except Exception:
            await runner.cleanup()
            raise
        self.runner = runner
        self.state = "loading"
        self.model_task = asyncio.create_task(self.prime(), name="watchyo-vosk-prewarm")
        return True

    async def stop(self) -> None:
        if self.model_task is not None:
            self.model_task.cancel()
            try:
                await self.model_task
            except asyncio.CancelledError:
                pass
            self.model_task = None
        if self.runner is not None:
            await self.runner.cleanup()
            self.runner = None
        self.model = None
        self.state = "disabled"
        self.used_nonces.clear()
