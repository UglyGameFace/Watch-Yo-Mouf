"""Independent Discord gateway. Voice capture is intentionally not active yet.

Do not add voice connection or moderation logic here before the DAVE receive,
consent/revocation, and single-owner migration contracts are implemented.
"""

from __future__ import annotations

import logging

import discord
from discord import app_commands

from .config import Settings
from .voice_readiness import probe_voice_stack
from .voice_bridge_client import private_bridge_status
from .voice_member_client import probe_member_eligibility

log = logging.getLogger(__name__)


class MyConsentCanaryView(discord.ui.View):
    """A private staff-initiated probe of only the caller's existing agreement.

    No guild-wide scans, member enumeration, persistent views, or audio capture.
    A member's voice state is used only to choose the configured channel for
    this single explicitly clicked request.
    """

    def __init__(self, owner_id: int):
        super().__init__(timeout=180)
        self.owner_id = int(owner_id)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        permitted = bool(
            interaction.guild is not None
            and interaction.user.id == self.owner_id
            and getattr(interaction.user.guild_permissions, "manage_guild", False)
        )
        if not permitted:
            await interaction.response.send_message(
                "Only the staff member who opened this private status can run the consent test.",
                ephemeral=True,
            )
        return permitted

    @discord.ui.button(label="Test My Consent", emoji="🔎", style=discord.ButtonStyle.secondary)
    async def check_my_consent(
        self, interaction: discord.Interaction, button: discord.ui.Button,
    ) -> None:
        """Explicit read-only network canary; does not join or inspect audio."""
        voice_channel = getattr(getattr(interaction.user, "voice", None), "channel", None)
        channel_id = int(getattr(voice_channel, "id", 0) or 0)
        if not channel_id or getattr(getattr(voice_channel, "guild", None), "id", None) != interaction.guild.id:
            await interaction.response.send_message(
                "Join the voice channel configured for Voice Safety, then tap this button again. "
                "This test reads settings only and does not listen or record.",
                ephemeral=True,
            )
            return

        await interaction.response.defer(ephemeral=True, thinking=True)
        probe = await probe_member_eligibility(
            int(interaction.guild.id), int(interaction.user.id), channel_id,
        )
        eligibility = probe.eligibility
        if eligibility is None:
            message = (
                "⚠️ **Member consent check failed.** "
                f"Stage: **{probe.stage}**.\n"
                "The private status GET and member eligibility POST are separate checks. "
                "No audio was authorized."
            )
        else:
            consent = "recorded" if eligibility.consent_current else "not recorded"
            policy = "matches this VC" if eligibility.policy_matches else "not enabled for this VC"
            message = (
                "🔎 **Read-only Voice Safety test for your own account**\n"
                f"Voice-specific agreement: **{consent}**.\n"
                f"Dank Shield monitored-room configuration: **{policy}**.\n"
                "Voice capture: **OFF**. This is a point-in-time check only, not "
                "continuous revocation synchronization or a receiver lease."
            )
        await interaction.followup.send(message, ephemeral=True)


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
        readiness = probe_voice_stack()
        private_bridge = await private_bridge_status()
        prerequisite_label = "ready for live testing" if readiness.ready else "blocked"
        await interaction.response.send_message(
            "🛡️ **Watch Yo Mouf**\n"
            "Gateway: online.\n"
            f"Voice decoder prerequisites: **{prerequisite_label}** ({readiness.reason}).\n"
            f"Private Dank Shield bridge: **{private_bridge}**.\n"
            "Voice safety: **not enabled**. No recording, transcription or AI reviews are running.\n"
            "Read-only member consent test is available below. Durable receiver ownership, "
            "immediate opt-out synchronization and live DAVE validation remain pending.",
            ephemeral=True,
            view=MyConsentCanaryView(int(interaction.user.id)),
        )

    return bot
