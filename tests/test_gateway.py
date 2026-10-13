"""Instantiation smoke tests; no token, Discord connection or recording."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord

from watch_yo_mouf.config import Settings
from watch_yo_mouf.gateway import MyConsentCanaryView, create_bot
from watch_yo_mouf.voice_member_client import MemberEligibilityProbe


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self):
        # A constructed, never-connected AutoShardedClient has no queue to shut down.
        # Do not call close(): no network connection or shard worker was ever opened.
        return create_bot(Settings("dummy-token", None, None, False))

    async def test_gateway_registers_only_admin_status_and_no_message_content(self):
        client = self.make_client()
        self.assertIsInstance(client, discord.AutoShardedClient)
        self.assertTrue(client.intents.guilds)
        self.assertTrue(client.intents.voice_states)
        self.assertFalse(client.intents.message_content)
        self.assertFalse(client.intents.members)
        self.assertEqual([command.name for command in client.tree.get_commands()], ["watchyo"])

    async def test_admin_only_status_reports_monitoring_disabled(self):
        client = self.make_client()
        command = client.tree.get_commands()[0]
        response = SimpleNamespace(send_message=AsyncMock())
        interaction = SimpleNamespace(
            guild=object(),
            user=SimpleNamespace(id=24, guild_permissions=SimpleNamespace(manage_guild=True)),
            response=response,
        )
        await command.callback(interaction)
        response.send_message.assert_awaited_once()
        args, kwargs = response.send_message.await_args
        self.assertIn("not enabled", args[0])
        self.assertTrue(kwargs["ephemeral"])
        self.assertIsInstance(kwargs["view"], MyConsentCanaryView)
        self.assertEqual(kwargs["view"].owner_id, 24)
        self.assertEqual([button.label for button in kwargs["view"].children], ["Test My Consent"])

    async def test_nonadmin_cannot_read_status(self):
        client = self.make_client()
        command = client.tree.get_commands()[0]
        response = SimpleNamespace(send_message=AsyncMock())
        interaction = SimpleNamespace(
            guild=object(),
            user=SimpleNamespace(id=24, guild_permissions=SimpleNamespace(manage_guild=False)),
            response=response,
        )
        await command.callback(interaction)
        args, kwargs = response.send_message.await_args
        self.assertIn("Manage Server", args[0])
        self.assertTrue(kwargs["ephemeral"])


    @staticmethod
    def consent_interaction(*, user_id=24, guild_id=71, voice_id=88, staff=True):
        channel = (
            SimpleNamespace(id=voice_id, guild=SimpleNamespace(id=guild_id))
            if voice_id is not None else None
        )
        return SimpleNamespace(
            guild=SimpleNamespace(id=guild_id),
            user=SimpleNamespace(
                id=user_id,
                guild_permissions=SimpleNamespace(manage_guild=staff),
                voice=SimpleNamespace(channel=channel),
            ),
            response=SimpleNamespace(send_message=AsyncMock(), defer=AsyncMock()),
            followup=SimpleNamespace(send=AsyncMock()),
        )

    async def test_consent_check_only_available_to_owning_staff(self):
        view = MyConsentCanaryView(24)
        for interaction in (
            self.consent_interaction(user_id=25),
            self.consent_interaction(staff=False),
        ):
            self.assertFalse(await view.interaction_check(interaction))
            interaction.response.send_message.assert_awaited_once()
            self.assertTrue(interaction.response.send_message.await_args.kwargs["ephemeral"])
        self.assertTrue(await view.interaction_check(self.consent_interaction()))

    async def test_consent_button_requires_a_detectable_voice_channel(self):
        view = MyConsentCanaryView(24)
        button = view.children[0]
        interaction = self.consent_interaction(voice_id=None)
        with patch("watch_yo_mouf.gateway.probe_member_eligibility", new_callable=AsyncMock) as check:
            await button.callback(interaction)
            check.assert_not_awaited()
            interaction.response.defer.assert_not_awaited()
            interaction.response.send_message.assert_awaited_once()
            self.assertIn("Join the voice channel", interaction.response.send_message.await_args.args[0])
            self.assertTrue(interaction.response.send_message.await_args.kwargs["ephemeral"])

    async def test_consent_button_checks_only_requesters_own_agreement_without_capture(self):
        view = MyConsentCanaryView(24)
        button = view.children[0]
        for eligibility, markers in (
            (SimpleNamespace(consent_current=True, policy_matches=True, capture_authorized=False),
             ("recorded", "matches this VC")),
            (SimpleNamespace(consent_current=False, policy_matches=False, capture_authorized=False),
             ("not recorded", "not enabled for this VC")),
            (None, ("Member consent check failed", "No audio was authorized")),
        ):
            with self.subTest(eligibility=eligibility):
                interaction = self.consent_interaction()
                with patch(
                    "watch_yo_mouf.gateway.probe_member_eligibility",
                    new_callable=AsyncMock, return_value=MemberEligibilityProbe(
                        eligibility, "POST authenticated" if eligibility else "POST timed out (private service or consent storage)"
                    ),
                ) as check:
                    await button.callback(interaction)
                    check.assert_awaited_once_with(71, 24, 88)
                interaction.response.defer.assert_awaited_once_with(ephemeral=True, thinking=True)
                interaction.followup.send.assert_awaited_once()
                message = interaction.followup.send.await_args.args[0]
                for marker in markers:
                    self.assertIn(marker, message)
                self.assertTrue(interaction.followup.send.await_args.kwargs["ephemeral"])
                self.assertNotIn("voice_capture_authorized=true", message)
                self.assertNotIn("connected to voice", message)


    async def test_failed_post_stage_is_reported_without_user_details(self):
        view = MyConsentCanaryView(24)
        interaction = self.consent_interaction()
        with patch(
            "watch_yo_mouf.gateway.probe_member_eligibility",
            new_callable=AsyncMock,
            return_value=MemberEligibilityProbe(None, "POST server returned HTTP 500"),
        ):
            await view.children[0].callback(interaction)
        text = interaction.followup.send.await_args.args[0]
        self.assertIn("POST server returned HTTP 500", text)
        self.assertIn("No audio was authorized", text)
        self.assertNotIn("24", text)
        self.assertNotIn("71", text)
        self.assertTrue(interaction.followup.send.await_args.kwargs["ephemeral"])


if __name__ == "__main__":
    unittest.main()
