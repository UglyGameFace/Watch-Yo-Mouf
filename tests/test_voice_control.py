"""Security contract for future cross-host Voice Safety instructions.

No test joins a channel, opens a socket, or authorizes audio admission.
"""

import json
import unittest

from watch_yo_mouf.voice_control import (
    ControlGate,
    ControlMessageRejected,
    new_control_payload,
    sign_control,
    verify_control,
)

KEY = b"separate-voice-control-unit-test-secret-of-sufficient-length"
WRONG_KEY = b"unauthorized-voice-control-unit-test-secret-not-matching"
NOW = 1_800_000_000
GUILD = 1517985071230095360
CHANNEL = 1551000000000000001
MEMBER = 1551000000000000002


def packet(action="policy", *, sequence=1, guild_id=GUILD, **kwargs):
    payload = new_control_payload(
        action=action, guild_id=guild_id, sequence=sequence, now=NOW, **kwargs
    )
    return sign_control(payload, KEY, now=NOW)


class SignedControlTests(unittest.TestCase):
    def test_authenticated_policy_has_short_lifetime_and_no_audio_admission(self):
        raw = packet(channel_id=CHANNEL, enabled=True)
        verified = verify_control(raw, KEY, now=NOW)
        self.assertEqual(verified.guild_id, GUILD)
        self.assertEqual(verified.channel_id, CHANNEL)
        gate = ControlGate()
        status = gate.apply_signed(raw, KEY, now=NOW)
        self.assertTrue(status.desired_enabled)
        self.assertFalse(status.halted)
        self.assertFalse(gate.admits_audio(GUILD, MEMBER))
        self.assertIsNotNone(gate.status(GUILD, now=NOW))
        self.assertIsNone(gate.status(GUILD, now=NOW + 15))
        self.assertFalse(gate.admits_audio(GUILD, MEMBER))

    def test_wrong_key_and_modified_message_are_rejected(self):
        raw = packet(channel_id=CHANNEL, enabled=True)
        gate = ControlGate()
        with self.assertRaises(ControlMessageRejected):
            gate.apply_signed(raw, WRONG_KEY, now=NOW)
        tampered = json.loads(raw)
        tampered["payload"]["channel_id"] = CHANNEL + 1
        with self.assertRaises(ControlMessageRejected):
            gate.apply_signed(json.dumps(tampered).encode(), KEY, now=NOW)
        self.assertIsNone(gate.status(GUILD, now=NOW))

    def test_wrong_guild_cannot_be_substituted_by_transport(self):
        raw = packet(channel_id=CHANNEL, enabled=True)
        tampered = json.loads(raw)
        tampered["payload"]["guild_id"] = 42
        with self.assertRaises(ControlMessageRejected):
            verify_control(json.dumps(tampered).encode(), KEY, now=NOW)

    def test_replay_lower_sequence_and_out_of_order_events_fail_closed(self):
        gate = ControlGate()
        policy = packet(sequence=3, channel_id=CHANNEL, enabled=True)
        gate.apply_signed(policy, KEY, now=NOW)
        with self.assertRaises(ControlMessageRejected):
            gate.apply_signed(policy, KEY, now=NOW)
        with self.assertRaises(ControlMessageRejected):
            gate.apply_signed(packet(sequence=2, channel_id=CHANNEL, enabled=True), KEY, now=NOW)
        self.assertFalse(gate.admits_audio(GUILD, MEMBER))

    def test_revocation_closes_entire_guild_and_policy_cannot_reopen(self):
        gate = ControlGate()
        gate.apply_signed(packet(sequence=1, channel_id=CHANNEL, enabled=True), KEY, now=NOW)
        revoked = gate.apply_signed(
            packet("revoke", sequence=2, member_id=MEMBER), KEY, now=NOW
        )
        self.assertTrue(revoked.halted)
        self.assertFalse(revoked.desired_enabled)
        subsequent = gate.apply_signed(
            packet(sequence=3, channel_id=CHANNEL, enabled=True), KEY, now=NOW
        )
        self.assertTrue(subsequent.halted)
        self.assertFalse(subsequent.desired_enabled)
        self.assertFalse(gate.admits_audio(GUILD, MEMBER))
        with self.assertRaises(ControlMessageRejected):
            gate.apply_signed(packet("revoke", sequence=2, member_id=MEMBER), KEY, now=NOW)

    def test_owner_stop_and_false_policy_never_rearm(self):
        gate = ControlGate()
        gate.apply_signed(packet(sequence=1, channel_id=CHANNEL, enabled=False), KEY, now=NOW)
        blocked = gate.apply_signed(packet(sequence=2, channel_id=CHANNEL, enabled=True), KEY, now=NOW)
        self.assertTrue(blocked.halted)
        stop = gate.apply_signed(packet("stop", sequence=3), KEY, now=NOW)
        self.assertFalse(stop.desired_enabled)
        self.assertTrue(stop.halted)

    def test_expired_future_or_overlong_instructions_fail(self):
        raw = packet(channel_id=CHANNEL, enabled=True)
        for now in (NOW + 15, NOW - 6):
            with self.subTest(now=now):
                with self.assertRaises(ControlMessageRejected):
                    verify_control(raw, KEY, now=now)
        with self.assertRaises(ControlMessageRejected):
            new_control_payload(
                action="policy", guild_id=GUILD, sequence=1,
                now=NOW, ttl_seconds=31, channel_id=CHANNEL, enabled=True
            )

    def test_malformed_version_types_unknown_fields_are_refused(self):
        base = new_control_payload(
            action="policy", guild_id=GUILD, sequence=1,
            now=NOW, channel_id=CHANNEL, enabled=True
        )
        variants = (
            {"version": 2}, {"enabled": 1}, {"guild_id": True},
            {"sequence": 0}, {"expires_at": NOW}, {"nonce": "oops"},
            {"member_id": MEMBER}, {"action": "record"},
        )
        for change in variants:
            with self.subTest(change=change):
                altered = dict(base, **change)
                with self.assertRaises(ControlMessageRejected):
                    sign_control(altered, KEY, now=NOW)

    def test_duplicate_json_properties_are_refused(self):
        raw = packet(channel_id=CHANNEL, enabled=True)
        envelope = json.loads(raw)
        # Duplicate top-level fields must not be interpreted differently by peers.
        doubled = ('{"payload":' + json.dumps(envelope["payload"]) +
                   ',"payload":' + json.dumps(envelope["payload"]) +
                   ',"signature":"' + envelope["signature"] + '"}').encode()
        with self.assertRaises(ControlMessageRejected):
            verify_control(doubled, KEY, now=NOW)

    def test_oversized_envelope_and_weak_secrets_fail(self):
        raw = packet(channel_id=CHANNEL, enabled=True)
        with self.assertRaises(ControlMessageRejected):
            verify_control(raw + b" " * 4096, KEY, now=NOW)
        with self.assertRaises(ControlMessageRejected):
            verify_control(raw, b"weak", now=NOW)
        with self.assertRaises(ControlMessageRejected):
            sign_control(json.loads(raw)["payload"], b"weak", now=NOW)

    def test_guild_isolation_no_cross_guild_sequence_collision(self):
        gate = ControlGate()
        gate.apply_signed(packet(sequence=5, channel_id=CHANNEL, enabled=True), KEY, now=NOW)
        other = gate.apply_signed(
            packet(sequence=1, guild_id=GUILD + 1, channel_id=CHANNEL + 1, enabled=True),
            KEY, now=NOW,
        )
        self.assertEqual(other.last_sequence, 1)
        self.assertEqual(gate.status(GUILD, now=NOW).last_sequence, 5)
        self.assertFalse(gate.admits_audio(GUILD + 1, MEMBER))


if __name__ == "__main__":
    unittest.main()
