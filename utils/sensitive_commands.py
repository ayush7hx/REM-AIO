from __future__ import annotations

import discord
from discord.ext import commands

SENSITIVE_OWNER_COMMANDS = frozenset({"getadmin", "getroll", "manageroll"})


async def is_sensitive_owner_command(
    bot: commands.Bot, message: discord.Message
) -> bool:
    if message.guild is None or message.author.bot:
        return False

    ctx = await bot.get_context(message)
    return (
        ctx.command is not None
        and ctx.command.qualified_name in SENSITIVE_OWNER_COMMANDS
        and await bot.is_owner(message.author)
    )
