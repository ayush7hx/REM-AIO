from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from utils.cv2_compat import embed_to_view
from utils.config import (
    NON_ADMIN_ROLE_IDS,
    PERMANENT_OWNER_ROLE_IDS,
    PRIMARY_OWNER_ID,
)

log = logging.getLogger(__name__)


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
        self.role_select.options = self._options_for_page()
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
                "Pehle ek role select karo.", ephemeral=True
            )
            return

        role = guild.get_role(int(selected_values[0]))
        me = guild.me
        if role is None:
            await interaction.response.send_message(
                "Ye role ab server mein available nahi hai.", ephemeral=True
            )
            return
        if me is None or not me.guild_permissions.manage_roles:
            await interaction.response.send_message(
                "Bot ko **Manage Roles** permission chahiye.", ephemeral=True
            )
            return
        if role.is_default() or role.managed or role >= me.top_role:
            await interaction.response.send_message(
                "Bot is role ko manage nahi kar sakta. Role hierarchy check karo.",
                ephemeral=True,
            )
            return

        if add and role in self.member.roles:
            await interaction.response.send_message(
                f"{self.member.mention} ke paas pehle se {role.mention} role hai.",
                ephemeral=True,
            )
            return
        if (
            not add
            and self.member.id == PRIMARY_OWNER_ID
            and role.id in PERMANENT_OWNER_ROLE_IDS
        ):
            await interaction.response.send_message(
                f"{role.mention} configured permanent owner role hai; ise remove nahi kar sakte.",
                ephemeral=True,
            )
            return
        if not add and role not in self.member.roles:
            await interaction.response.send_message(
                f"{self.member.mention} ke paas {role.mention} role nahi hai.",
                ephemeral=True,
            )
            return

        try:
            if add:
                await self.member.add_roles(
                    role, reason=f"Requested by bot owner {PRIMARY_OWNER_ID}"
                )
            else:
                await self.member.remove_roles(
                    role, reason=f"Requested by bot owner {PRIMARY_OWNER_ID}"
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
                role.id,
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
        await interaction.response.edit_message(
            view=embed_to_view(
                discord.Embed(
                    description=f"{role.mention} role {self.member.mention} ko {action}."
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
