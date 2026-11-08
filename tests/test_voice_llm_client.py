"""No-network tests for the synthetic-only Intelligence diagnostics."""
from __future__ import annotations

import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from watch_yo_mouf.gateway import MyConsentCanaryView
from watch_yo_mouf.voice_llm_client import AIProbe, probe_private_ai


class FakeReply:
    def __init__(self, code=200, body=None):
        self.status = code
        self.payload = json.dumps(body or {}).encode("utf-8")
        self.content_length = len(self.payload)
        self.content = SimpleNamespace(read=AsyncMock(side_effect=[self.payload, b""]))

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False


class FakeSession:
    def __init__(self, reply):
        self.reply = reply
        self.calls = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        return False

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.reply


GOOD = {
    "model": "LiquidAI/LFM3-1.7B-GGUF:Q4_K_M",
    "decision": "allow", "category": "none", "confidence": "medium",
    "advisory_only": True, "calibrated": False, "enforcement_authorized": False,
}


class VoiceLLMClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_disabled_does_not_touch_network(self):
        with patch.dict(os.environ, {}, clear=True):
            with patch("watch_yo_mouf.voice_llm_client.aiohttp.ClientSession") as network:
                result = await probe_private_ai()
                self.assertIn("disabled", result.status)
                network.assert_not_called()

    async def test_bad_key_fails_closed(self):
        with patch.dict(os.environ, {
            "WATCH_YO_MOUF_LLM_VOICE_ENABLED": "true",
            "WATCH_YO_MOUF_LLM_VOICE_TOKEN": "short",
        }, clear=True):
            with patch("watch_yo_mouf.voice_llm_client.aiohttp.ClientSession") as network:
                result = await probe_private_ai()
                self.assertIn("configuration error", result.status)
                network.assert_not_called()

    async def simulate(self, code, body=None):
        session = FakeSession(FakeReply(code, body))
        config = {
            "WATCH_YO_MOUF_LLM_VOICE_ENABLED": "true",
            "WATCH_YO_MOUF_LLM_VOICE_TOKEN": "v" * 48,
        }
        with patch.dict(os.environ, config, clear=True):
            with patch(
                "watch_yo_mouf.voice_llm_client.aiohttp.ClientSession",
                return_value=session,
            ):
                outcome = await probe_private_ai()
        return outcome, session.calls

    async def test_authenticated_private_synthetic_probe(self):
        outcome, calls = await self.simulate(200, GOOD)
        self.assertEqual(outcome.status, "authenticated (synthetic test only)")
        self.assertEqual(outcome.decision, "allow")
        self.assertEqual(len(calls), 1)
        url, options = calls[0]
        self.assertEqual(url, "http://rival-llm:8765/v1/moderate")
        self.assertFalse(options["allow_redirects"])
        self.assertEqual(options["json"], {
            "version": 1,
            "transcript": "I am discussing my own identity.",
            "context": [],
        })
        self.assertEqual(options["headers"], {"Authorization": "Bearer " + "v" * 48})

    async def test_wrong_scopes_busy_and_invalid_outputs_are_not_success(self):
        for code, body, fragment in (
            (401, {}, "authentication rejected"),
            (429, {}, "model busy"),
            (503, {}, "unavailable"),
            (404, {}, "endpoint missing"),
            (200, {**GOOD, "enforcement_authorized": True}, "invalid private AI schema"),
            (200, {**GOOD, "decision": "review"}, "invalid private AI schema"),
            (200, {"transcript": "private"}, "invalid private AI schema"),
        ):
            with self.subTest(code=code, body=body):
                outcome, _ = await self.simulate(code, body)
                self.assertIn(fragment, outcome.status)
                self.assertFalse(outcome.decision)
                self.assertFalse(outcome.category)

    async def test_bounded_timeout_without_retries(self):
        class TimeoutSession(FakeSession):
            def post(self, url, **kwargs):
                self.calls.append((url, kwargs))
                raise asyncio.TimeoutError()
        session = TimeoutSession(FakeReply())
        with patch.dict(os.environ, {
            "WATCH_YO_MOUF_LLM_VOICE_ENABLED": "true",
            "WATCH_YO_MOUF_LLM_VOICE_TOKEN": "v" * 48,
        }, clear=True):
            with patch("watch_yo_mouf.voice_llm_client.aiohttp.ClientSession", return_value=session):
                result = await probe_private_ai()
        self.assertIn("timed out", result.status)
        self.assertEqual(len(session.calls), 1)


class VoiceLLMUIRegressionTests(unittest.IsolatedAsyncioTestCase):
    async def test_staff_button_only_uses_synthetic_probe(self):
        view = MyConsentCanaryView(42)
        labels = [button.label for button in view.children]
        self.assertEqual(labels, ["Test My Consent", "Test Private AI"])
        button = view.children[1]
        interaction = SimpleNamespace(
            guild=SimpleNamespace(id=70),
            user=SimpleNamespace(id=42, guild_permissions=SimpleNamespace(manage_guild=True)),
            response=SimpleNamespace(defer=AsyncMock(), send_message=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )
        self.assertTrue(await view.interaction_check(interaction))
        with patch("watch_yo_mouf.gateway.probe_private_ai", new_callable=AsyncMock,
                   return_value=AIProbe("model busy (no queue)")) as probe:
            await button.callback(interaction)
            probe.assert_awaited_once_with()
        interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
        message = interaction.followup.send.await_args.args[0]
        self.assertIn("model busy", message)
        self.assertIn("synthetic", message)
        self.assertTrue(interaction.followup.send.await_args.kwargs["ephemeral"])

        interaction.user.id = 999
        self.assertFalse(await view.interaction_check(interaction))
        self.assertTrue(interaction.response.send_message.await_args.kwargs["ephemeral"])


if __name__ == "__main__":
    unittest.main()
