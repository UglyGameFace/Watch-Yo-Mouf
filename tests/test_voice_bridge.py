"""Private VLAN handshake tests: no Discord connection or voice activity."""
import json
import unittest
from unittest.mock import AsyncMock, patch

from watch_yo_mouf.voice_bridge_wire import (
    BridgeRejected, request_headers, response_body, response_signature,
    verify_request, verify_response,
)
from watch_yo_mouf.voice_bridge_client import private_bridge_status

KEY = "a-standalone-development-test-shared-key-long-enough-123456"
OTHER = "another-development-key-which-should-not-authenticate"
NONCE = "a" * 32
NOW = 1800000000


class BridgeWireTests(unittest.TestCase):
    def test_auth_valid_and_private_fixed_response(self):
        headers = request_headers(KEY, now=NOW, nonce=NONCE)
        self.assertEqual(verify_request(headers, KEY, now=NOW), NONCE)
        self.assertEqual(
            headers["X-WYM-Signature"],
            "911c9fe8caf90f58c0a90ee6cb42b3a534c3435b29d4e998c46a30bdc3b14850",
            "Cross-repo wire fixture changed; coordinate both bots before deploying",
        )
        body = response_body()
        self.assertTrue(verify_response(KEY, NONCE, body, response_signature(KEY, NONCE, body)))
        self.assertFalse(json.loads(body)["voice_capture_authorized"])
        self.assertNotIn(b"guild_id", body)
        self.assertNotIn(b"member_id", body)

    def test_forgery_expiry_wrong_nonce_and_wrong_key(self):
        h = request_headers(KEY, now=NOW, nonce=NONCE)
        for changed in (
            dict(h, **{"X-WYM-Nonce": "b" * 32}),
            dict(h, **{"X-WYM-Signature": "0" * 64}),
        ):
            with self.assertRaises(BridgeRejected):
                verify_request(changed, KEY, now=NOW)
        for at in (NOW - 31, NOW + 31):
            with self.assertRaises(BridgeRejected):
                verify_request(h, KEY, now=at)
        with self.assertRaises(BridgeRejected):
            verify_request(h, OTHER, now=NOW)
        with self.assertRaises(BridgeRejected):
            request_headers("short", now=NOW)

    def test_response_mutation_and_authority_change_rejected(self):
        body = response_body()
        signature = response_signature(KEY, NONCE, body)
        self.assertFalse(verify_response(OTHER, NONCE, body, signature))
        self.assertFalse(verify_response(KEY, "b" * 32, body, signature))
        mutated = dict(json.loads(body), voice_capture_authorized=True)
        forged_body = json.dumps(mutated).encode()
        self.assertFalse(verify_response(KEY, NONCE, forged_body, signature))
        self.assertFalse(verify_response(KEY, NONCE, forged_body, response_signature(KEY, NONCE, forged_body)))


class BridgeClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_default_disabled_makes_no_outbound_connection(self):
        with patch.dict("os.environ", {}, clear=True), patch(
            "watch_yo_mouf.voice_bridge_client.aiohttp.ClientSession"
        ) as client:
            self.assertEqual(await private_bridge_status(), "disabled")
            client.assert_not_called()

    async def test_enabled_missing_key_fails_closed_without_dial(self):
        with patch.dict("os.environ", {"WATCH_YO_MOUF_BRIDGE_ENABLED": "true"}, clear=True), patch(
            "watch_yo_mouf.voice_bridge_client.aiohttp.ClientSession"
        ) as client:
            self.assertEqual(await private_bridge_status(), "unavailable")
            client.assert_not_called()

    async def test_nonresponsive_vlan_returns_unavailable_without_leaking_credentials(self):
        with patch.dict("os.environ", {
            "WATCH_YO_MOUF_BRIDGE_ENABLED": "true",
            "WATCH_YO_MOUF_BRIDGE_SECRET": KEY,
        }, clear=True), patch(
            "watch_yo_mouf.voice_bridge_client.aiohttp.ClientSession",
            side_effect=OSError("simulated vlan down")
        ):
            self.assertEqual(await private_bridge_status(), "unavailable")


if __name__ == "__main__":
    unittest.main()
