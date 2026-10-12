"""Offline configuration and secure-startup tests."""

import unittest

from watch_yo_mouf.config import ConfigurationError, load_settings


class SettingsTests(unittest.TestCase):
    def test_token_required(self):
        with self.assertRaisesRegex(ConfigurationError, "WATCH_YO_MOUF_TOKEN"):
            load_settings({})

    def test_minimal_has_automatic_sharding_and_no_command_sync(self):
        settings = load_settings({"WATCH_YO_MOUF_TOKEN": "private-placeholder"})
        self.assertIsNone(settings.shard_count)
        self.assertIsNone(settings.shard_ids)
        self.assertFalse(settings.sync_commands)

    def test_explicit_shard_partition(self):
        settings = load_settings({
            "WATCH_YO_MOUF_TOKEN": "secret",
            "WATCH_YO_MOUF_SHARD_COUNT": "8",
            "WATCH_YO_MOUF_SHARD_IDS": "2,3",
            "WATCH_YO_MOUF_SYNC_COMMANDS": "false",
        })
        self.assertEqual(settings.shard_count, 8)
        self.assertEqual(settings.shard_ids, (2, 3))

    def test_reject_invalid_partition(self):
        bad = [
            {"WATCH_YO_MOUF_SHARD_IDS": "1"},
            {"WATCH_YO_MOUF_SHARD_COUNT": "2", "WATCH_YO_MOUF_SHARD_IDS": "0,2"},
            {"WATCH_YO_MOUF_SHARD_COUNT": "2", "WATCH_YO_MOUF_SHARD_IDS": "1,1"},
            {"WATCH_YO_MOUF_SHARD_COUNT": "3", "WATCH_YO_MOUF_SHARD_IDS": "1,no"},
            {"WATCH_YO_MOUF_SHARD_COUNT": "0"},
        ]
        for invalid in bad:
            with self.subTest(invalid=invalid), self.assertRaises(ConfigurationError):
                load_settings({"WATCH_YO_MOUF_TOKEN": "secret", **invalid})

    def test_reject_ambiguous_flag(self):
        with self.assertRaisesRegex(ConfigurationError, "SYNC_COMMANDS"):
            load_settings({"WATCH_YO_MOUF_TOKEN": "secret", "WATCH_YO_MOUF_SYNC_COMMANDS": "maybe"})

    def test_error_messages_never_echo_token(self):
        secret = "do-not-print-my-secret"
        try:
            load_settings({"WATCH_YO_MOUF_TOKEN": secret, "WATCH_YO_MOUF_SHARD_COUNT": "invalid"})
        except ConfigurationError as exc:
            self.assertNotIn(secret, str(exc))
        else:
            self.fail("expected configuration failure")


if __name__ == "__main__":
    unittest.main()
