from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

import discord
from discord.ext import commands

from utils.cv2_compat import embed_to_view
from utils.config import (
    NON_ADMIN_ROLE_IDS,
    PERMANENT_OWNER_ROLE_IDS,
    PRIMARY_OWNER_ID,
    TEMPORARY_ADMIN_ROLE_ID,
)
from utils.database import connect

log = logging.getLogger(__name__)
_TEMPORARY_ROLE_DATABASE = "owner_protection.db"
_TEMPORARY_ROLE_TABLE = "temporary_roles"


class OwnerRolePicker(discord.ui.View):
    PAGE_SIZE = 25

    def __init__(
        self,
        ctx: commands.Context,
        roles: list[discord.Role],
        member: discord.Member | None = None,
    ) -> None:
        super().__init__(timeout=120)
        self.ctx = ctx
        self.member = member or ctx.author
        self.roles = roles
        self.page = 0
        self.message: discord.Message | None = None

        self.role_select = discord.ui.Select(
            placeholder="Choose a role to manage",
            options=self._options_for_page(),
            min_values=1,
            max_values=min(len(roles), self.PAGE_SIZE),
            row=0,
        )
        self.role_select.callback = self.select_role
        self.add_item(self.role_select)

        self.previous_button = discord.ui.Button(
            label="Previous", style=discord.ButtonStyle.secondary, row=1,
            disabled=True,
        )
        self.previous_button.callback = self.previous_page
        self.add_item(self.previous_button)

        self.next_button = discord.ui.Button(
            label="Next", style=discord.ButtonStyle.secondary, row=1,
            disabled=len(roles) <= self.PAGE_SIZE,
        )
        self.next_button.callback = self.next_page
        self.add_item(self.next_button)

        self.add_button = discord.ui.Button(
            label="Add role", style=discord.ButtonStyle.success, row=1,
        )
        self.add_button.callback = self.add_role
        self.add_item(self.add_button)

        self.remove_button = discord.ui.Button(
            label="Remove role", style=discord.ButtonStyle.danger, row=1,
        )
        self.remove_button.callback = self.remove_role
        self.add_item(self.remove_button)

        self.cancel_button = discord.ui.Button(
            label="Cancel", style=discord.ButtonStyle.secondary, row=1,
        )
        self.cancel_button.callback = self.cancel
        self.add_item(self.cancel_button)

    def _options_for_page(self) -> list[discord.SelectOption]:
        start = self.page * self.PAGE_SIZE
        return [
            discord.SelectOption(
                label=role.name[:100],
                description=(
                    f"Role position {role.position} · "
                    f"{'Assigned' if role in self.member.roles else 'Not assigned'}"
                ),
                value=str(role.id),
            )
            for role in self.roles[start : start + self.PAGE_SIZE]
        ]

    def _embed(self, *, title: str = "Choose a role") -> discord.Embed:
        page_count = (len(self.roles) + self.PAGE_SIZE - 1) // self.PAGE_SIZE
        embed = discord.Embed(
            title=title,
            description=(
                "Select a role, then choose **Add role** or **Remove role**.\n"
                f"Page **{self.page + 1}/{page_count}** · **{len(self.roles)}** roles available."
            ),
        )
        return embed

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id == PRIMARY_OWNER_ID:
            return True
        await interaction.response.send_message(
            "Sirf configured bot owner is role picker ko use kar sakta hai.",
            ephemeral=True,
        )
        return False

    async def _show_page(self, interaction: discord.Interaction) -> None:
        self.role_select._values = []
        self.role_select.options = self._options_for_page()
        self.role_select.max_values = len(self.role_select.options)
        self.previous_button.disabled = self.page == 0
        self.next_button.disabled = (self.page + 1) * self.PAGE_SIZE >= len(self.roles)
        await interaction.response.edit_message(
            view=embed_to_view(self._embed(), self),
        )

    async def previous_page(self, interaction: discord.Interaction) -> None:
        self.page -= 1
        await self._show_page(interaction)

    async def next_page(self, interaction: discord.Interaction) -> None:
        self.page += 1
        await self._show_page(interaction)

    async def cancel(self, interaction: discord.Interaction) -> None:
        self.stop()
        await interaction.response.edit_message(
            view=embed_to_view(discord.Embed(title="Role selection cancelled.")),
        )

    async def select_role(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()

    async def add_role(self, interaction: discord.Interaction) -> None:
        await self._change_role(interaction, add=True)

    async def remove_role(self, interaction: discord.Interaction) -> None:
        await self._change_role(interaction, add=False)

    async def _change_role(
        self, interaction: discord.Interaction, *, add: bool
    ) -> None:
        guild = self.ctx.guild
        selected_values = self.role_select.values
        if not selected_values:
            await interaction.response.send_message(
                "Pehle kam se kam ek role select karo.", ephemeral=True
            )
            return

        roles = [guild.get_role(int(value)) for value in selected_values]
        if any(role is None for role in roles):
            await interaction.response.send_message(
                "Selected roles mein se koi role ab server mein available nahi hai.",
                ephemeral=True,
            )
            return

        roles = [role for role in roles if role is not None]
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "Bot ko **Manage Roles** permission chahiye.", ephemeral=True
            )
            return
        if any(
            role.is_default() or role.managed or role >= me.top_role
            for role in roles
        ):
            await interaction.response.send_message(
                "Selected roles mein se koi role bot manage nahi kar sakta. Role hierarchy check karo.",
                ephemeral=True,
            )
            return

        if (
            not add
            and self.member.id == PRIMARY_OWNER_ID
            and any(role.id in PERMANENT_OWNER_ROLE_IDS for role in roles)
        ):
            await interaction.response.send_message(
                "Configured permanent owner role ko remove nahi kar sakte.",
                ephemeral=True,
            )
            return

        if add:
            changed_roles = [role for role in roles if role not in self.member.roles]
        else:
            changed_roles = [role for role in roles if role in self.member.roles]
        if not changed_roles:
            await interaction.response.send_message(
                f"Selected roles mein koi bhi {'add' if add else 'remove'} karne ke liye available nahi hai.",
                ephemeral=True,
            )
            return

        try:
            if add:
                await self.member.add_roles(
                    *changed_roles,
                    reason=f"Requested by bot owner {PRIMARY_OWNER_ID}",
                )
            else:
                await self.member.remove_roles(
                    *changed_roles,
                    reason=f"Requested by bot owner {PRIMARY_OWNER_ID}",
                )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Discord ne role change karne se mana kiya; bot permissions check karo.",
                ephemeral=True,
            )
            return
        except discord.HTTPException:
            log.exception(
                "Failed to change role %s for member %s in guild %s",
                ", ".join(str(role.id) for role in changed_roles),
                self.member.id,
                guild.id,
            )
            await interaction.response.send_message(
                "Role change nahi ho saka. Thodi der baad dobara try karo.",
                ephemeral=True,
            )
            return

        self.stop()
        action = "de diya" if add else "remove kar diya"
        role_mentions = ", ".join(role.mention for role in changed_roles)
        await interaction.response.edit_message(
            view=embed_to_view(
                discord.Embed(
                    description=(
                        f"{role_mentions} role(s) {self.member.mention} ko {action}."
                    )
                )
            ),
        )

    async def on_timeout(self) -> None:
        if self.message is None:
            return
        for item in self.children:
            item.disabled = True
        try:
            await self.message.edit(
                view=embed_to_view(discord.Embed(title="Role picker expired."), self)
            )
        except discord.HTTPException:
            pass


class OwnerProtection(commands.Cog):
    """Keeps each guild owner's administrative roles present in their guild."""

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self._locks: dict[int, asyncio.Lock] = {}
        self._temporary_role_task: asyncio.Task | None = None

    def _lock_for(self, guild_id: int) -> asyncio.Lock:
        return self._locks.setdefault(guild_id, asyncio.Lock())

    async def cog_load(self) -> None:
        # Ready is not guaranteed when cogs are loaded, so setup runs after it.
        asyncio.create_task(self._protect_existing_guilds())
        self._temporary_role_task = asyncio.create_task(
            self._process_temporary_role_expirations()
        )

    def cog_unload(self) -> None:
        if self._temporary_role_task is not None:
            self._temporary_role_task.cancel()

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
                await self.ensure_owner_channel_permissions(guild)
            except Exception:
                log.exception("Owner role startup repair failed in %s", guild.id)

    @commands.Cog.listener()
    async def on_guild_available(self, guild: discord.Guild) -> None:
        try:
            await self.ensure_owner_access(guild)
            await self.ensure_owner_channel_permissions(guild)
        except Exception:
            log.exception("Owner role availability repair failed in %s", guild.id)

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild) -> None:
        await self.ensure_non_admin_roles(guild)
        await self.ensure_owner_access(guild)
        await self.ensure_owner_channel_permissions(guild)

    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel: discord.abc.GuildChannel) -> None:
        await self.ensure_owner_channel_permissions(channel.guild, channel)

    @commands.Cog.listener()
    async def on_guild_channel_update(
        self, before: discord.abc.GuildChannel, after: discord.abc.GuildChannel
    ) -> None:
        if before.overwrites != after.overwrites:
            await self.ensure_owner_channel_permissions(after.guild, after)

    @commands.command(name="getadmin")
    @commands.guild_only()
    @commands.is_owner()
    async def getadmin(self, ctx: commands.Context) -> None:
        guild = ctx.guild
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            await ctx.reply("Bot ko **Manage Roles** permission chahiye.")
            return

        role = guild.get_role(TEMPORARY_ADMIN_ROLE_ID)
        if role is None:
            await ctx.reply(
                f"Temporary admin role `{TEMPORARY_ADMIN_ROLE_ID}` server mein nahi mila."
            )
            return
        if role.managed or role >= me.top_role:
            await ctx.reply(
                "Bot ka highest role temporary admin role se upar hona chahiye."
            )
            return

        expires_at = int(
            (discord.utils.utcnow() + timedelta(minutes=10)).timestamp()
        )
        await self._save_temporary_role_expiry(
            guild.id, ctx.author.id, role.id, expires_at
        )

        try:
            if role not in ctx.author.roles:
                await ctx.author.add_roles(
                    role,
                    reason="Temporary owner admin access for 10 minutes",
                )
        except (discord.Forbidden, discord.HTTPException):
            await self._delete_temporary_role_expiry(
                guild.id, ctx.author.id, role.id
            )
            log.exception(
                "Failed to grant temporary admin role %s to owner in guild %s",
                role.id,
                guild.id,
            )
            await ctx.reply("Role nahi lag saka; bot permission aur role hierarchy check karo.")
            return

        await ctx.reply(f"{role.mention} role 10 minutes ke liye mil gaya.")

    async def _ensure_temporary_role_table(self) -> None:
        async with connect(_TEMPORARY_ROLE_DATABASE) as db:
            await db.execute(
                f"""CREATE TABLE IF NOT EXISTS {_TEMPORARY_ROLE_TABLE} (
                    guild_id INTEGER NOT NULL,
                    member_id INTEGER NOT NULL,
                    role_id INTEGER NOT NULL,
                    expires_at INTEGER NOT NULL,
                    PRIMARY KEY (guild_id, member_id, role_id)
                )"""
            )
            await db.commit()

    async def _save_temporary_role_expiry(
        self, guild_id: int, member_id: int, role_id: int, expires_at: int
    ) -> None:
        await self._ensure_temporary_role_table()
        async with connect(_TEMPORARY_ROLE_DATABASE) as db:
            await db.execute(
                f"""INSERT OR REPLACE INTO {_TEMPORARY_ROLE_TABLE}
                    (guild_id, member_id, role_id, expires_at)
                    VALUES (?, ?, ?, ?)""",
                (guild_id, member_id, role_id, expires_at),
            )
            await db.commit()

    async def _delete_temporary_role_expiry(
        self, guild_id: int, member_id: int, role_id: int
    ) -> None:
        async with connect(_TEMPORARY_ROLE_DATABASE) as db:
            await db.execute(
                f"""DELETE FROM {_TEMPORARY_ROLE_TABLE}
                    WHERE guild_id = ? AND member_id = ? AND role_id = ?""",
                (guild_id, member_id, role_id),
            )
            await db.commit()

    async def _process_temporary_role_expirations(self) -> None:
        try:
            await self.bot.wait_until_ready()
        except RuntimeError:
            return

        while not self.bot.is_closed():
            try:
                await self._expire_temporary_roles()
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Temporary owner-role expiry pass failed")
            await asyncio.sleep(15)

    async def _expire_temporary_roles(self) -> None:
        await self._ensure_temporary_role_table()
        now = int(discord.utils.utcnow().timestamp())
        async with connect(_TEMPORARY_ROLE_DATABASE) as db:
            async with db.execute(
                f"""SELECT guild_id, member_id, role_id FROM {_TEMPORARY_ROLE_TABLE}
                    WHERE expires_at <= ?""",
                (now,),
            ) as cursor:
                expired_roles = await cursor.fetchall()

        for guild_id, member_id, role_id in expired_roles:
            guild = self.bot.get_guild(guild_id)
            if guild is None:
                continue

            role = guild.get_role(role_id)
            member = guild.get_member(member_id)
            if role is None:
                await self._delete_temporary_role_expiry(
                    guild_id, member_id, role_id
                )
                continue
            if member is None:
                try:
                    member = await guild.fetch_member(member_id)
                except discord.NotFound:
                    await self._delete_temporary_role_expiry(
                        guild_id, member_id, role_id
                    )
                    continue
                except (discord.Forbidden, discord.HTTPException):
                    await self._retry_temporary_role_expiry(
                        guild_id, member_id, role_id
                    )
                    continue

            me = guild.me
            if me is None or not me.guild_permissions.manage_roles or role >= me.top_role:
                log.warning(
                    "Cannot expire role %s for member %s in guild %s; check bot permissions and role hierarchy",
                    role_id,
                    member_id,
                    guild_id,
                )
                await self._retry_temporary_role_expiry(
                    guild_id, member_id, role_id
                )
                continue

            if role in member.roles:
                try:
                    await member.remove_roles(
                        role,
                        reason="Temporary owner admin access expired after 10 minutes",
                    )
                except (discord.Forbidden, discord.HTTPException):
                    log.exception(
                        "Failed to expire temporary role %s for member %s in guild %s",
                        role_id,
                        member_id,
                        guild_id,
                    )
                    await self._retry_temporary_role_expiry(
                        guild_id, member_id, role_id
                    )
                    continue

            await self._delete_temporary_role_expiry(
                guild_id, member_id, role_id
            )

    async def _retry_temporary_role_expiry(
        self, guild_id: int, member_id: int, role_id: int
    ) -> None:
        retry_at = int((discord.utils.utcnow() + timedelta(minutes=1)).timestamp())
        await self._save_temporary_role_expiry(
            guild_id, member_id, role_id, retry_at
        )

    @commands.command(name="getroll")
    @commands.guild_only()
    @commands.is_owner()
    async def getroll(self, ctx: commands.Context) -> None:
        me = ctx.guild.me
        if me is None or not me.guild_permissions.manage_roles:
            await ctx.reply("Bot ko **Manage Roles** permission chahiye.")
            return

        roles = sorted(
            (
                role for role in ctx.guild.roles
                if not role.is_default()
                and not role.managed
                and role < me.top_role
            ),
            key=lambda role: role.position,
            reverse=True,
        )
        if not roles:
            await ctx.reply("Tumhare liye koi assignable role nahi mila.")
            return

        view = OwnerRolePicker(ctx, roles)
        view.message = await ctx.reply(view=embed_to_view(view._embed(), view))

    @commands.command(name="manageroll")
    @commands.guild_only()
    @commands.is_owner()
    async def manageroll(
        self, ctx: commands.Context, member: discord.Member
    ) -> None:
        me = ctx.guild.me
        if me is None or not me.guild_permissions.manage_roles:
            await ctx.reply("Bot ko **Manage Roles** permission chahiye.")
            return

        roles = sorted(
            (
                role for role in ctx.guild.roles
                if not role.is_default()
                and not role.managed
                and role < me.top_role
            ),
            key=lambda role: role.position,
            reverse=True,
        )
        if not roles:
            await ctx.reply("Koi assignable role nahi mila.")
            return

        view = OwnerRolePicker(ctx, roles, member)
        embed = view._embed()
        embed.description = (
            f"Managing roles for {member.mention}.\n{embed.description}"
        )
        view.message = await ctx.reply(view=embed_to_view(embed, view))

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
        if member.id == PRIMARY_OWNER_ID:
            await self.ensure_owner_access(member.guild, member)
            await self.ensure_owner_channel_permissions(member.guild, member=member)

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
        if after.id != PRIMARY_OWNER_ID or before.roles == after.roles:
            return
        await self.ensure_owner_access(after.guild, after)

    async def ensure_owner_access(
        self, guild: discord.Guild, member: discord.Member | None = None
    ) -> None:
        """Restore the configured permanent roles to the primary bot owner.

        Role assignment is intentionally ID-based.  In particular, this must
        never create, rename, elevate, or assign a role merely because of its
        name (such as ``𖣂``).
        """
        if member is not None and member.id != PRIMARY_OWNER_ID:
            return

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
                try:
                    member = await guild.fetch_member(PRIMARY_OWNER_ID)
                except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                    log.warning(
                        "Cannot find protected owner %s in %s",
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

    async def ensure_owner_channel_permissions(
        self,
        guild: discord.Guild,
        channel: discord.abc.GuildChannel | None = None,
        *,
        member: discord.Member | None = None,
    ) -> None:
        """Grant the configured owner all channel-level permissions."""
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            log.warning(
                "Cannot configure owner channel permissions in %s: Manage Roles is missing",
                guild.id,
            )
            return

        if member is None:
            member = guild.get_member(PRIMARY_OWNER_ID)
        if member is None:
            try:
                member = await guild.fetch_member(PRIMARY_OWNER_ID)
            except (discord.NotFound, discord.Forbidden, discord.HTTPException):
                log.warning(
                    "Cannot configure owner channel permissions in %s: owner %s is unavailable",
                    guild.id,
                    PRIMARY_OWNER_ID,
                )
                return

        overwrite = discord.PermissionOverwrite.from_pair(
            discord.Permissions.all_channel(),
            discord.Permissions.none(),
        )
        channels = [channel] if channel is not None else guild.channels

        async with self._lock_for(guild.id):
            for target_channel in channels:
                if target_channel.overwrites_for(member) == overwrite:
                    continue
                try:
                    await target_channel.set_permissions(
                        member,
                        overwrite=overwrite,
                        reason="Ensure configured bot owner has full channel access",
                    )
                except discord.Forbidden:
                    log.warning(
                        "Cannot configure owner permissions for channel %s in %s",
                        target_channel.id,
                        guild.id,
                    )
                except discord.HTTPException:
                    log.exception(
                        "Failed to configure owner permissions for channel %s in %s",
                        target_channel.id,
                        guild.id,
                    )
