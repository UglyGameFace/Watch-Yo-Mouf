"""Voice prerequisite tests: never establish a Discord connection."""

import unittest
from types import SimpleNamespace
from unittest.mock import patch

from watch_yo_mouf import voice_readiness


class VoiceReadinessTests(unittest.TestCase):
    def test_real_pinned_voice_stack_can_construct_pcm_decoder(self):
        # This is a real native ABI/import check in GitHub Actions, not a mock.
        # Successful decoding of encrypted live speech still needs a consented canary.
        status = voice_readiness.probe_voice_stack()
        self.assertTrue(status.ready, status.reason)
        self.assertTrue(status.davey)
        self.assertTrue(status.receive_extension)
        self.assertTrue(status.inbound_dave_decoder)
        self.assertTrue(status.native_opus_decoder)
        self.assertIn("live DAVE unverified", status.reason)

    def test_missing_dave_fails_closed(self):
        original = voice_readiness.importlib.import_module

        def import_module(name):
            if name == "davey":
                raise ImportError("missing")
            return original(name)

        with patch.object(voice_readiness.importlib, "import_module", side_effect=import_module), patch.object(
            voice_readiness, "_native_opus_decoder_ready", return_value=True
        ):
            status = voice_readiness.probe_voice_stack()
        self.assertFalse(status.ready)
        self.assertEqual(status.reason, "davey dependency unavailable")

    def test_extension_without_inbound_dave_hook_fails_closed(self):
        original = voice_readiness.importlib.import_module

        def import_module(name):
            if name == "discord.ext.voice_recv.opus":
                return SimpleNamespace(PacketDecoder=object)
            return original(name)

        with patch.object(voice_readiness.importlib, "import_module", side_effect=import_module), patch.object(
            voice_readiness, "_native_opus_decoder_ready", return_value=True
        ):
            status = voice_readiness.probe_voice_stack()
        self.assertFalse(status.ready)
        self.assertFalse(status.inbound_dave_decoder)
        self.assertEqual(status.reason, "pinned inbound DAVE decoder unavailable")

    def test_missing_native_opus_fails_closed(self):
        with patch.object(voice_readiness, "_native_opus_decoder_ready", return_value=False):
            status = voice_readiness.probe_voice_stack()
        self.assertFalse(status.ready)
        self.assertEqual(status.reason, "native Opus PCM decoder unavailable")

    def test_probe_contains_no_voice_admission(self):
        # A library capability check must never become an implicit opt-in or receiver.
        import inspect

        source = inspect.getsource(voice_readiness)
        self.assertNotIn(".connect(", source)
        self.assertNotIn(".listen(", source)
        self.assertNotIn("VoiceRecvClient(", source)


if __name__ == "__main__":
    unittest.main()
