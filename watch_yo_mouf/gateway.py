"""Independent Discord gateway. Voice capture is intentionally not active yet.

Do not add voice connection or moderation logic here before the DAVE receive,
consent/revocation, and single-owner migration contracts are implemented.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from .config import Settings

log = logging.getLogger(__name__)


def create_bot(settings: Settings) -> discord.AutoShardedClient:
    intents = discord.Intents.none()
    intents.guilds = True
    intents.voice_states = True

    options: dict[str, object] = {}
    if settings.shard_count is not None:
        options["shard_count"] = settings.shard_count
    if settings.shard_ids is not None:
        options["shard_ids"] = settings.shard_ids

    class WatchYoMoufBot(discord.AutoShardedClient):
        def __init__(self) -> None:
            super().__init__(intents=intents, **options)
            self.tree = app_commands.CommandTree(self)

        async def setup_hook(self) -> None:
            if settings.sync_commands:
                synced = await self.tree.sync()
                log.info("Registered application commands count=%s", len(synced))

        async def on_ready(self) -> None:
            log.info(
                "Watch Yo Mouf gateway online guilds=%s shards=%s voice_safety=disabled",
                len(self.guilds),
                self.shard_count,
            )

    bot = WatchYoMoufBot()

    @bot.tree.command(name="watchyo", description="Check Watch Yo Mouf's independent gateway status")
    @app_commands.guild_only()
    @app_commands.default_permissions(manage_guild=True)
    async def watchyo(interaction: discord.Interaction) -> None:
        if not interaction.guild or not getattr(interaction.user.guild_permissions, "manage_guild", False):
            await interaction.response.send_message("Manage Server permission is required.", ephemeral=True)
            return
        await interaction.response.send_message(
            "🛡️ **Watch Yo Mouf**\n"
            "Gateway: online.\n"
            "Voice safety: **not enabled**. No recording, transcription or AI reviews are running.\n"
            "Dank Shield integration and DAVE receive validation are still pending.",
            ephemeral=True,
        )

    return bot
