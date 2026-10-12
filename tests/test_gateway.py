"""Instantiation smoke tests; no token, Discord connection or recording."""

import unittest

import discord

from watch_yo_mouf.config import Settings
from watch_yo_mouf.gateway import create_bot


class GatewayTests(unittest.IsolatedAsyncioTestCase):
    async def test_gateway_registers_only_admin_status_and_no_message_content(self):
        client = create_bot(Settings("dummy-token", None, None, False))
        try:
            self.assertIsInstance(client, discord.AutoShardedClient)
            self.assertTrue(client.intents.guilds)
            self.assertTrue(client.intents.voice_states)
            self.assertFalse(client.intents.message_content)
            self.assertFalse(client.intents.members)
            self.assertEqual([command.name for command in client.tree.get_commands()], ["watchyo"])
        finally:
            await client.close()


if __name__ == "__main__":
    unittest.main()
