"""Remove everyone/here mentions from configured, high-risk Discord accounts."""

from __future__ import annotations

import io
import logging
from pathlib import PurePosixPath

import discord
from discord.ext import commands

from utils.config import PROTECTED_LOG_CHANNEL_ID, PROTECTED_USER_IDS


log = logging.getLogger(__name__)


class ProtectedUsers(commands.Cog):
    """Delete mentions or image messages from configured users.

    This deliberately does not timeout, kick, or ban the member: those actions
    obey Discord's role hierarchy.  Deleting a message only requires the bot
    to have Manage Messages in the message's channel.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def _has_image_attachment(message: discord.Message) -> bool:
        return any(
            (attachment.content_type or "").startswith("image/")
            or PurePosixPath(attachment.filename).suffix.lower()
            in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}
            for attachment in message.attachments
        )

    @commands.Cog.listener("on_message")
    async def remove_protected_user_message(self, message: discord.Message) -> None:
        if (
            message.guild is None
            or message.author.bot
            or message.author.id not in PROTECTED_USER_IDS
            or not (message.mention_everyone or self._has_image_attachment(message))
        ):
            return

        await self._send_deletion_log(message)

        try:
            await message.delete()
        except discord.Forbidden:
            log.warning(
                "Cannot delete message %s in #%s (%s): missing Manage Messages",
                message.id,
                message.channel,
                message.channel.id,
            )
            return
        except discord.HTTPException:
            log.exception("Failed to delete protected user's message %s", message.id)
            return

    async def _send_deletion_log(self, message: discord.Message) -> None:
        if not PROTECTED_LOG_CHANNEL_ID:
            return

        channel = self.bot.get_channel(PROTECTED_LOG_CHANNEL_ID)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(PROTECTED_LOG_CHANNEL_ID)
            except discord.HTTPException:
                log.warning("Protected-user log channel %s is unavailable", PROTECTED_LOG_CHANNEL_ID)
                return

        if not isinstance(channel, (discord.TextChannel, discord.Thread)):
            log.warning("Protected-user log channel %s cannot receive text messages", PROTECTED_LOG_CHANNEL_ID)
            return

        content = message.content.strip() or "(no text; possibly an attachment, embed, or sticker)"
        if len(content) > 1000:
            content = f"{content[:997]}..."

        embed = discord.Embed(
            title="Protected-user message deleted",
            colour=discord.Colour.red(),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="User", value=f"{message.author} (`{message.author.id}`)", inline=False)
        embed.add_field(name="Source", value=f"{message.guild.name} / {message.channel.mention}", inline=False)
        embed.add_field(name="Content", value=content, inline=False)
        if message.attachments:
            embed.add_field(name="Attachments", value=str(len(message.attachments)), inline=True)
        embed.set_footer(text=f"Message ID: {message.id}")

        try:
            files = []
            for attachment in message.attachments:
                if (
                    (attachment.content_type or "").startswith("image/")
                    or PurePosixPath(attachment.filename).suffix.lower()
                    in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}
                ):
                    data = await attachment.read()
                    files.append(
                        discord.File(
                            io.BytesIO(data),
                            filename=f"{attachment.id}-{attachment.filename}",
                        )
                    )

            await channel.send(
                embed=embed,
                files=files,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except discord.HTTPException:
            log.exception("Failed to send protected-user deletion log for message %s", message.id)
