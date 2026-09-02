import discord
import json
import logging
from discord.ext import commands
from discord import app_commands
from utils.config import serverLink
from core import Rem, Cog, Context
from utils.Tools import SecurityAccessDenied, get_ignore_data
from utils.cv2_compat import embed_to_view, embeds_to_view

log = logging.getLogger(__name__)

class Errors(Cog):
  def __init__(self, client: Rem):
    self.client = client

  @commands.Cog.listener()
  async def on_command_error(self, ctx: Context, error):
    if ctx.command is None:
      return

    async def send_command_error():
      embed = discord.Embed(
        title="Command Error",
        description="Something went wrong while running that command. The error was logged.",
        color=0x000000,
      )
      embed.set_author(name="DARK INFINITE", icon_url=self.client.user.display_avatar.url)
      embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
      await ctx.reply(view=embed_to_view(embed), delete_after=10, mention_author=False)
    

    if isinstance(error, commands.CommandNotFound):
      return

    if isinstance(error, commands.MissingRequiredArgument):
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.CheckFailure):
      if isinstance(error, SecurityAccessDenied):
        ctx.command.reset_cooldown(ctx)
        return

      if isinstance(error, commands.MissingPermissions):
        missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_permissions]
        fmt = "{}, and {}".format(", ".join(missing[:-1]), missing[-1]) if len(missing) > 2 else " and ".join(missing)
        embed = discord.Embed(color=0x000000, description=f"You need **{fmt}** to run `{ctx.command.qualified_name}`.")
        embed.set_author(name="Missing Permissions", icon_url=self.client.user.display_avatar.url)
        await ctx.reply(view=embed_to_view(embed), delete_after=8, mention_author=False)
        ctx.command.reset_cooldown(ctx)
        return

      if isinstance(error, commands.BotMissingPermissions):
        missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_permissions]
        fmt = "{}, and {}".format(", ".join(missing[:-1]), missing[-1]) if len(missing) > 2 else " and ".join(missing)
        await ctx.reply(f"I need **{fmt}** to run `{ctx.command.qualified_name}`.", delete_after=8, mention_author=False)
        ctx.command.reset_cooldown(ctx)
        return

      if ctx.guild is None:
        return

      data = await get_ignore_data(ctx.guild.id)
      ch = data["channel"]
      iuser = data["user"]
      cmd = data["command"]
      buser = data["bypassuser"]

      if str(ctx.author.id) in buser:
        return

      if str(ctx.channel.id) in ch:
        await ctx.reply(f"{ctx.author.mention} This **channel** is on the **ignored** list. Please try my commands in another channel.",
                        delete_after=8)
        return

      if str(ctx.author.id) in iuser:
        await ctx.reply(f"{ctx.author.mention} You are set as an **ignored user** for this guild. Please try my commands or modules in a different guild.", delete_after=8)
        return

      if ctx.command.name in cmd or any(alias in cmd for alias in ctx.command.aliases):
        await ctx.reply(f"{ctx.author.mention} This **command is ignored** in this guild. Please use other commands or try this command in a different guild", delete_after=8)
        return

      await ctx.reply("You do not have permission to use this command.", delete_after=8, mention_author=False)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.NoPrivateMessage):
      embed = discord.Embed(color=0x000000, description="You can't use my commands in DMs.")
      embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(view = embed_to_view(embed), delete_after=20)
      return

    if isinstance(error, commands.TooManyArguments):
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.CommandOnCooldown):
      embed = discord.Embed(color=0x000000, description=f"{ctx.author.mention} Whoa, slow down there! You can run the command again in **{error.retry_after:.2f}** seconds.")
      embed.set_author(name="Cooldown", icon_url=self.client.user.display_avatar.url)
      
      embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(view = embed_to_view(embed), delete_after=10)
      return

    if isinstance(error, commands.MaxConcurrencyReached):
      embed = discord.Embed(color=0x000000, description=f"{ctx.author.mention} This command is already in progress. Please let it finish and try again afterward.")
      embed.set_author(name="Command in Progress.", icon_url=self.client.user.display_avatar.url)
      
      embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(view = embed_to_view(embed), delete_after=10)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.MissingPermissions):
      missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_permissions]
      fmt = "{}, and {}".format(", ".join(missing[:-1]), missing[-1]) if len(missing) > 2 else " and ".join(missing)
      embed = discord.Embed(color=0x000000, description=f"You lack the **{fmt}** Permission to run the **{ctx.command.name}** command!")
      embed.set_author(name="Missing Permissions", icon_url=self.client.user.display_avatar.url)
      
      embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(view = embed_to_view(embed), delete_after=7)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.BadArgument):
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.BotMissingPermissions):
      missing = ", ".join(error.missing_permissions)
      await ctx.reply(f' I need **{missing}** Permission to run the **{ctx.command.qualified_name}** command!', delete_after=7)
      return

    if isinstance(error, discord.HTTPException):
      return

    if isinstance(error, commands.CommandInvokeError):
      log.exception("Command %s failed", ctx.command.qualified_name if ctx.command else "unknown", exc_info=error.original)
      try:
        await send_command_error()
      except discord.HTTPException:
        pass
      return

    log.exception("Unhandled command error in %s", ctx.command.qualified_name if ctx.command else "unknown", exc_info=error)
    try:
      await send_command_error()
    except discord.HTTPException:
      pass

  @commands.Cog.listener()
  async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
      message = f"Slow down. Try again in **{error.retry_after:.2f}** seconds."
    elif isinstance(error, app_commands.MissingPermissions):
      missing = ", ".join(perm.replace("_", " ").title() for perm in error.missing_permissions)
      message = f"You need **{missing}** to use this command."
    elif isinstance(error, app_commands.BotMissingPermissions):
      missing = ", ".join(perm.replace("_", " ").title() for perm in error.missing_permissions)
      message = f"I need **{missing}** to use this command."
    elif isinstance(error, app_commands.CheckFailure):
      message = "You do not have permission to use this command."
    else:
      log.exception("App command %s failed", getattr(interaction.command, "qualified_name", "unknown"), exc_info=error)
      message = "Something went wrong while running that command. The error was logged."

    try:
      if message == "Something went wrong while running that command. The error was logged.":
        embed = discord.Embed(title="Command Error", description=message, color=0x000000)
        embed.set_author(name="DARK INFINITE", icon_url=self.client.user.display_avatar.url)
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        if interaction.response.is_done():
          await interaction.followup.send(view=embed_to_view(embed), ephemeral=True)
        else:
          await interaction.response.send_message(view=embed_to_view(embed), ephemeral=True)
        return
      if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
      else:
        await interaction.response.send_message(message, ephemeral=True)
    except discord.HTTPException:
      pass
