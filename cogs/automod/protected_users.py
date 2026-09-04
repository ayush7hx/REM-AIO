"""Remove everyone/here mentions from configured, high-risk Discord accounts."""

from __future__ import annotations

from pathlib import PurePosixPath

import discord
from discord.ext import commands

from utils.config import PROTECTED_USER_IDS

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".avif"}


class ProtectedUsers(commands.Cog):
    """Delete mentions or image messages from configured users.

    This deliberately does not timeout, kick, or ban the member: those actions
    obey Discord's role hierarchy.  Deleting a message only requires the bot
    to have Manage Messages in the message's channel.
    """

    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @staticmethod
    def _is_image_attachment(attachment: discord.Attachment) -> bool:
        return (
            (attachment.content_type or "").startswith("image/")
            or PurePosixPath(attachment.filename).suffix.lower() in IMAGE_SUFFIXES
        )

    @staticmethod
    def _has_image_attachment(message: discord.Message) -> bool:
        return any(
            self._is_image_attachment(attachment)
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

        await message.delete()
