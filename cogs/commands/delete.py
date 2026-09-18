from __future__ import annotations

import discord
from discord.ext import commands

from utils.Tools import blacklist_check, ignore_check


class Delete(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _confirm_and_delete(self, ctx: commands.Context, channel: discord.abc.GuildChannel) -> None:
        if channel.guild != ctx.guild:
            await ctx.send("This channel belongs to another server.", delete_after=8)
            return

        confirm = discord.ui.Button(label="Confirm", style=discord.ButtonStyle.danger)
        cancel = discord.ui.Button(label="Cancel", style=discord.ButtonStyle.secondary)
        view = discord.ui.View(timeout=30)

        async def finish(interaction: discord.Interaction, content: str) -> None:
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("Only the command author can confirm this.", ephemeral=True)
                return
            confirm.disabled = True
            cancel.disabled = True
            await interaction.response.edit_message(content=content, view=view)

        async def confirm_callback(interaction: discord.Interaction) -> None:
            if interaction.user.id != ctx.author.id:
                await interaction.response.send_message("Only the command author can confirm this.", ephemeral=True)
                return
            anti_channel_delete = self.bot.get_cog("AntiChannelDelete")
            if anti_channel_delete is not None:
                anti_channel_delete.mark_intentional(channel.id)
            await finish(interaction, f"Deleting {channel.mention}...")
            try:
                await channel.delete(reason=f"Requested by {ctx.author} ({ctx.author.id})")
            except discord.Forbidden:
                await ctx.send("I need Manage Channels permission to delete this channel.", delete_after=8)
            except discord.HTTPException:
                await ctx.send("Discord rejected the channel deletion. Please try again.", delete_after=8)

        async def cancel_callback(interaction: discord.Interaction) -> None:
            await finish(interaction, "Deletion cancelled.")

        confirm.callback = confirm_callback
        cancel.callback = cancel_callback
        view.add_item(confirm)
        view.add_item(cancel)
        await ctx.send(
            f"Are you sure you want to delete {channel.mention}? This cannot be undone.",
            view=view,
        )

    @commands.group(name="delete", invoke_without_command=True)
    @blacklist_check()
    @ignore_check()
    @commands.guild_only()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def delete(self, ctx: commands.Context) -> None:
        await ctx.send_help(ctx.command)

    @delete.command(name="channel", help="Delete the channel where this command was used.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def delete_channel(self, ctx: commands.Context) -> None:
        await self._confirm_and_delete(ctx, ctx.channel)

    @delete.command(name="vc", aliases=("voice",), help="Delete the voice channel you are connected to.")
    @blacklist_check()
    @ignore_check()
    @commands.has_permissions(manage_channels=True)
    @commands.bot_has_permissions(manage_channels=True)
    async def delete_vc(self, ctx: commands.Context) -> None:
        if ctx.author.voice is None or ctx.author.voice.channel is None:
            await ctx.send("You must be connected to a voice channel first.", delete_after=8)
            return
        await self._confirm_and_delete(ctx, ctx.author.voice.channel)
