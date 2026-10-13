"""Cross-host read-only consent check: no Discord or voice activity."""
from __future__ import annotations

import json
import unittest
from unittest.mock import AsyncMock, patch

from watch_yo_mouf.voice_member_client import read_member_eligibility
from watch_yo_mouf.voice_member_wire import (
    MemberCheckRejected, check_request_body, check_response_body,
    sign_check_request, sign_check_response, verify_check_request, verify_check_response,
)

KEY = "a-standalone-development-test-shared-key-long-enough-123456"
GUILD, MEMBER, CHANNEL = 123456789123456789, 222222222222222222, 333333333333333333
NOW, NONCE = 1800000000, "c" * 32


class WireTests(unittest.TestCase):
    def test_exact_wire_contract_and_false_audio_authority(self):
        raw = check_request_body(GUILD, MEMBER, CHANNEL)
        headers = sign_check_request(KEY, raw, now=NOW, nonce=NONCE)
        self.assertEqual(verify_check_request(headers, KEY, raw, now=NOW),
                         (GUILD, MEMBER, CHANNEL, NONCE))
        response = check_response_body(consent_current=True, policy_matches=True)
        self.assertEqual(verify_check_response(
            KEY, NONCE, raw, response, sign_check_response(KEY, NONCE, raw, response)),
            {"consent_current": True, "policy_matches": True})
        self.assertFalse(json.loads(response)["voice_capture_authorized"])
        self.assertNotIn(b"member_id", response)

    def test_replay_binding_and_tampering(self):
        raw = check_request_body(GUILD, MEMBER, CHANNEL)
        headers = sign_check_request(KEY, raw, now=NOW, nonce=NONCE)
        for tampered in (
            check_request_body(GUILD, MEMBER + 1, CHANNEL),
            check_request_body(GUILD, MEMBER, CHANNEL + 1),
            raw + b" ",
        ):
            with self.assertRaises(MemberCheckRejected):
                verify_check_request(headers, KEY, tampered, now=NOW)
        with self.assertRaises(MemberCheckRejected):
            verify_check_request(headers, KEY, raw, now=NOW + 31)
        response = check_response_body(consent_current=True, policy_matches=True)
        bad_response = json.dumps(dict(json.loads(response), voice_capture_authorized=True)).encode()
        with self.assertRaises(MemberCheckRejected):
            verify_check_response(KEY, NONCE, raw, bad_response,
                                  sign_check_response(KEY, NONCE, raw, bad_response))


class ClientTests(unittest.IsolatedAsyncioTestCase):
    async def test_disabled_or_invalid_does_not_dial(self):
        with patch.dict("os.environ", {}, clear=True), patch(
            "watch_yo_mouf.voice_member_client.aiohttp.ClientSession"
        ) as session:
            self.assertIsNone(await read_member_eligibility(GUILD, MEMBER, CHANNEL))
            session.assert_not_called()
        with patch.dict("os.environ", {"WATCH_YO_MOUF_BRIDGE_ENABLED": "true"}, clear=True), patch(
            "watch_yo_mouf.voice_member_client.aiohttp.ClientSession"
        ) as session:
            self.assertIsNone(await read_member_eligibility(GUILD, MEMBER, CHANNEL))
            session.assert_not_called()

    async def test_signed_reply_and_wrong_signature(self):
        class Response:
            status = 200

            def __init__(self, secret, nonce, request_body, valid=True):
                body = check_response_body(consent_current=True, policy_matches=True)
                self.content_length = len(body)
                self.content = type("Content", (), {
                    "read": AsyncMock(side_effect=[body[:17], body[17:], b""])
                })()
                self.headers = {"X-WYM-Response-Signature":
                    sign_check_response(secret, nonce, request_body, body) if valid else "0" * 64}
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False

        class Session:
            def __init__(self, valid, outer):
                self.valid, self.outer = valid, outer
            async def __aenter__(self):
                return self
            async def __aexit__(self, *args):
                return False
            def post(self, url, *, data, headers, allow_redirects):
                self.outer.assertEqual(url, "http://dankbot:8097/v1/member-eligibility")
                self.outer.assertFalse(allow_redirects)
                self.outer.assertEqual(data, check_request_body(GUILD, MEMBER, CHANNEL))
                self.outer.assertIn("X-WYM-Signature", headers)
                return Response(KEY, headers["X-WYM-Nonce"], data, self.valid)

        for valid in (True, False):
            with self.subTest(valid=valid), patch.dict("os.environ", {
                "WATCH_YO_MOUF_BRIDGE_ENABLED": "true", "WATCH_YO_MOUF_BRIDGE_SECRET": KEY,
            }, clear=True), patch(
                "watch_yo_mouf.voice_member_client.aiohttp.ClientSession",
                return_value=Session(valid, self),
            ):
                eligibility = await read_member_eligibility(GUILD, MEMBER, CHANNEL)
                if valid:
                    self.assertTrue(eligibility.consent_current)
                    self.assertTrue(eligibility.policy_matches)
                    self.assertFalse(eligibility.capture_authorized)
                else:
                    self.assertIsNone(eligibility)

    async def test_network_or_invalid_identifiers_fail_closed(self):
        with patch.dict("os.environ", {
            "WATCH_YO_MOUF_BRIDGE_ENABLED": "true", "WATCH_YO_MOUF_BRIDGE_SECRET": KEY,
        }, clear=True), patch(
            "watch_yo_mouf.voice_member_client.aiohttp.ClientSession",
            side_effect=OSError("connection down")
        ):
            self.assertIsNone(await read_member_eligibility(GUILD, MEMBER, CHANNEL))
            self.assertIsNone(await read_member_eligibility(-1, MEMBER, CHANNEL))


if __name__ == "__main__":
    unittest.main()
