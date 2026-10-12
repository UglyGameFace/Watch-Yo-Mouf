"""Instantiation smoke tests; no token, Discord connection or recording."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from watch_yo_mouf.config import Settings
from watch_yo_mouf.gateway import create_bot


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
            user=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=True)),
            response=response,
        )
        await command.callback(interaction)
        response.send_message.assert_awaited_once()
        args, kwargs = response.send_message.await_args
        self.assertIn("not enabled", args[0])
        self.assertTrue(kwargs["ephemeral"])

    async def test_nonadmin_cannot_read_status(self):
        client = self.make_client()
        command = client.tree.get_commands()[0]
        response = SimpleNamespace(send_message=AsyncMock())
        interaction = SimpleNamespace(
            guild=object(),
            user=SimpleNamespace(guild_permissions=SimpleNamespace(manage_guild=False)),
            response=response,
        )
        await command.callback(interaction)
        args, kwargs = response.send_message.await_args
        self.assertIn("Manage Server", args[0])
        self.assertTrue(kwargs["ephemeral"])


if __name__ == "__main__":
    unittest.main()
