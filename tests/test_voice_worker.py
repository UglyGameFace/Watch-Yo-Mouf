"""Exercise real private HTTP ingress without downloading a Vosk model."""
from __future__ import annotations

import asyncio
import os
import unittest
from unittest.mock import patch

import aiohttp
from aiohttp import web

from watch_yo_mouf import voice_worker
from watch_yo_mouf.watch_audio_wire import (
    PATH, sign_audio_request, verify_audio_response,
)

KEY = "watch-only-audio-token-with-ample-entropy-for-unit-tests"
GUILD, USER, CHANNEL = 1517985071230095360, 1517985071230095361, 1517985071230095362
PCM = b"\x00\x01" * 10_000


class LocalVoiceWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.environment = patch.dict(os.environ, {
            "WATCH_YO_MOUF_STT_ENABLED": "true",
            "WATCH_YO_MOUF_AUDIO_SECRET": KEY,
        })
        self.environment.start()
        self.worker = voice_worker.VoiceSTTWorker(
            model=object(), state="ready",
        )
        app = web.Application(client_max_size=600_000)
        app.router.add_post(PATH, self.worker.handle_audio)
        self.runner = web.AppRunner(app, access_log=None)
        await self.runner.setup()
        self.site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await self.site.start()
        self.url = f"http://127.0.0.1:{self.site._server.sockets[0].getsockname()[1]}{PATH}"

    async def asyncTearDown(self):
        await self.runner.cleanup()
        self.environment.stop()

    def headers(self, pcm=PCM, nonce="a" * 32):
        return {
            **sign_audio_request(
                KEY, pcm, GUILD, USER, CHANNEL, nonce=nonce,
            ),
            "Content-Type": "application/octet-stream",
        }

    async def post(self, pcm=PCM, headers=None):
        async with aiohttp.ClientSession(trust_env=False) as session:
            async with session.post(self.url, data=pcm, headers=headers or self.headers(pcm)) as response:
                return response.status, await response.read(), dict(response.headers)

    async def test_consent_scoped_authenticated_request_has_signed_transcript(self):
        with patch.object(voice_worker, "_recognize", return_value="hello everyone") as recognize:
            code, body, headers = await self.post()
        self.assertEqual(code, 200)
        self.assertIn("no-store", headers["Cache-Control"])
        self.assertEqual(
            verify_audio_response(
                KEY, "a" * 32, PCM, body, headers["X-WYM-Response-Signature"]
            ), "hello everyone",
        )
        recognize.assert_called_once_with(self.worker.model, PCM)
        self.assertEqual(self.worker.state, "ready")

    async def test_replayed_tampered_unknown_and_disabled_requests(self):
        with patch.object(voice_worker, "_recognize", return_value="welcome"):
            self.assertEqual((await self.post())[0], 200)
            self.assertEqual((await self.post())[0], 409)
        wrong = self.headers(PCM, nonce="b" * 32)
        wrong["X-WYM-Speaker"] = str(USER + 1)
        self.assertEqual((await self.post(headers=wrong))[0], 401)
        self.worker.state = "loading"
        self.assertEqual((await self.post(headers=self.headers(PCM, nonce="c" * 32)))[0], 503)
        os.environ["WATCH_YO_MOUF_STT_ENABLED"] = "false"
        self.assertEqual((await self.post(headers=self.headers(PCM, nonce="d" * 32)))[0], 503)

    async def test_busy_cpu_is_rejected_without_queueing_or_leaking_text(self):
        await self.worker.request_lock.acquire()
        try:
            code, body, _ = await self.post()
            self.assertEqual(code, 429)
            self.assertEqual(body, b"")
        finally:
            self.worker.request_lock.release()

    async def test_model_failures_are_conservative(self):
        with patch.object(voice_worker, "_recognize", side_effect=RuntimeError("audio is secret")):
            code, body, _ = await self.post()
        self.assertEqual(code, 503)
        self.assertNotIn(b"audio is secret", body)

    def test_vosk_recognition_does_not_log_audio(self):
        class FakeRecognizer:
            def __init__(self, _model, sample_rate):
                self.accepted = []
                assert sample_rate == 16000
            def AcceptWaveform(self, frame):
                self.accepted.append(frame)
                return False
            def FinalResult(self):
                return '{"text": "short message"}'
        fake = type("FakeVosk", (), {"KaldiRecognizer": FakeRecognizer})
        real_import = voice_worker.importlib.import_module
        with patch.object(
            voice_worker.importlib, "import_module",
            side_effect=lambda name: fake if name == "vosk" else real_import(name),
        ):
            text = voice_worker._recognize(object(), PCM)
        self.assertEqual(text, "short message")


if __name__ == "__main__":
    unittest.main()
