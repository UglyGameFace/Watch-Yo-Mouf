"""Failure-mode diagnostics for the private Dank Shield bridge.

Tests never open a socket or transmit a credential. The staff status must name
the failing stage instead of hiding all failures behind 'unavailable'.
"""
import asyncio
import socket
import unittest
from unittest.mock import patch

from watch_yo_mouf.voice_bridge_client import private_bridge_status

KEY = "a-standalone-development-test-shared-key-long-enough-123456"
SETTINGS = {
    "WATCH_YO_MOUF_BRIDGE_ENABLED": "true",
    "WATCH_YO_MOUF_BRIDGE_SECRET": KEY,
}


class BridgeErrorTests(unittest.IsolatedAsyncioTestCase):
    async def test_http_errors_are_differentiated(self):
        class Reply:
            def __init__(self, status):
                self.status = status

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

        class Client:
            def __init__(self, status):
                self.status = status

            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                return False

            def get(self, url, *, headers, allow_redirects):
                if url != "http://dankbot:8097/v1/status" or allow_redirects:
                    raise AssertionError("Unsafe bridge URL or redirect")
                return Reply(self.status)

        expected = {
            401: "authentication rejected (check both bridge secrets and host clocks)",
            503: "Dank Shield bridge listener disabled",
            404: "wrong endpoint (check Dank Shield deployed revision)",
            409: "replayed request rejected (check bridge time/nonce)",
            502: "Dank Shield bridge HTTP 502",
        }
        for code, label in expected.items():
            with self.subTest(code=code), patch.dict("os.environ", SETTINGS, clear=True), patch(
                "watch_yo_mouf.voice_bridge_client.aiohttp.ClientSession",
                return_value=Client(code),
            ) as client:
                self.assertEqual(await private_bridge_status(), label)
                self.assertFalse(client.call_args.kwargs["trust_env"])

    async def test_dns_refused_timeout_and_unexpected_errors_are_differentiated(self):
        errors = (
            (socket.gaierror(-2, "no private DNS"), "DNS lookup failed (private hostname dankbot)"),
            (ConnectionRefusedError("not listening"), "connection refused (Dank Shield listener on port 8097)"),
            (asyncio.TimeoutError(), "private connection timed out (VLAN or listener unreachable)"),
            (OSError("other network failure"), "private network connection failed"),
        )
        for error, label in errors:
            with self.subTest(error=type(error).__name__), patch.dict(
                "os.environ", SETTINGS, clear=True
            ), patch(
                "watch_yo_mouf.voice_bridge_client.aiohttp.ClientSession",
                side_effect=error,
            ):
                self.assertEqual(await private_bridge_status(), label)

    async def test_empty_or_weak_key_fails_before_any_request(self):
        with patch.dict("os.environ", {
            "WATCH_YO_MOUF_BRIDGE_ENABLED": "true",
            "WATCH_YO_MOUF_BRIDGE_SECRET": "too-short",
        }, clear=True), patch(
            "watch_yo_mouf.voice_bridge_client.aiohttp.ClientSession"
        ) as client:
            self.assertEqual(
                await private_bridge_status(),
                "configuration error (missing or invalid Watch Yo Mouf bridge secret)"
            )
            client.assert_not_called()


if __name__ == "__main__":
    unittest.main()
