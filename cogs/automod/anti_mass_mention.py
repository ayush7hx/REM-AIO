import logging
import re

from utils.database import connect
from utils import emojis

import discord
from discord.ext import commands
from datetime import timedelta
import asyncio
from utils.cv2_compat import embed_to_view, embeds_to_view
from utils.automod_helpers import automod_gate, log_automod_action

log = logging.getLogger(__name__)

class AntiMassMention(commands.Cog):
    LINK_PATTERN = re.compile(
        r"(?:https?://|www\.)[^\s<>()]+|\b(?:discord\.gg|discord(?:app)?\.com)/\S+",
        re.IGNORECASE,
    )
    MASS_MENTION_PATTERN = re.compile(r"(?<!\w)@(everyone|here)\b", re.IGNORECASE)

    def __init__(self, bot):
        self.bot = bot
        self.mass_mention_threshold = 5

    @classmethod
    def _is_mass_mention_link(cls, message):
        if not (
            message.mention_everyone
            or cls.MASS_MENTION_PATTERN.search(message.content)
        ):
            return False

        if cls.LINK_PATTERN.search(message.content):
            return True

        for embed in message.embeds:
            values = [embed.url, embed.title, embed.description]
            for field in embed.fields:
                values.extend((field.name, field.value))
            if any(value and cls.LINK_PATTERN.search(value) for value in values):
                return True
        return False

    async def is_automod_enabled(self, guild_id):
        async with connect('automod.db') as db:
            cursor = await db.execute("SELECT enabled FROM automod WHERE guild_id = ?", (guild_id,))
            result = await cursor.fetchone()
            return result is not None and result[0] == 1

    async def is_anti_mass_mention_enabled(self, guild_id):
        async with connect('automod.db') as db:
            cursor = await db.execute("SELECT punishment FROM automod_punishments WHERE guild_id = ? AND event = 'Anti mass mention'", (guild_id,))
            result = await cursor.fetchone()
            return result is not None

    async def get_ignored_channels(self, guild_id):
        async with connect('automod.db') as db:
            cursor = await db.execute("SELECT id FROM automod_ignored WHERE guild_id = ? AND type = 'channel'", (guild_id,))
            return [row[0] for row in await cursor.fetchall()]

    async def get_ignored_roles(self, guild_id):
        async with connect('automod.db') as db:
            cursor = await db.execute("SELECT id FROM automod_ignored WHERE guild_id = ? AND type = 'role'", (guild_id,))
            return [row[0] for row in await cursor.fetchall()]

    async def get_punishment(self, guild_id):
        async with connect('automod.db') as db:
            cursor = await db.execute("SELECT punishment FROM automod_punishments WHERE guild_id = ? AND event = 'Anti mass mention'", (guild_id,))
            result = await cursor.fetchone()
            return result[0] if result else None


    async def log_action(self, guild, user, channel, action, reason):
        async with connect('automod.db') as db:
            cursor = await db.execute("SELECT log_channel FROM automod_logging WHERE guild_id = ?", (guild.id,))
            log_channel_id = await cursor.fetchone()

        if log_channel_id and log_channel_id[0]:
            log_channel = guild.get_channel(log_channel_id[0])
            if log_channel:
                embed = discord.Embed(title="Automod Log: Anti Mass Mention", color=0xff0000)
                embed.add_field(name="User", value=user.mention, inline=False)
                embed.add_field(name="Action", value=action, inline=False)
                embed.add_field(name="Channel", value=channel.mention, inline=False)
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.set_footer(text=f"User ID: {user.id}")
                avatar_url = user.avatar.url if user.avatar else user.default_avatar.url
                embed.set_thumbnail(url=avatar_url)
                embed.timestamp=discord.utils.utcnow()
                await log_channel.send(view = embed_to_view(embed))

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or message.guild is None:
            return

        if self._is_mass_mention_link(message):
            try:
                await message.delete(reason="Mass mention with link; possible scam spam")
            except discord.NotFound:
                return
            except discord.Forbidden:
                log.warning(
                    "Cannot delete mass-mention link from %s in channel %s; Manage Messages is missing",
                    message.author.id,
                    message.channel.id,
                )
            except discord.HTTPException:
                log.exception(
                    "Failed to delete mass-mention link from %s in channel %s",
                    message.author.id,
                    message.channel.id,
                )
            return

        gate = await automod_gate(message, 'Anti mass mention')
        if gate is None:
            return

        guild = message.guild
        user = message.author
        channel = message.channel



        mention_count = message.content.count("<@")
        if mention_count >= self.mass_mention_threshold:
            punishment = gate.punishment
            action_taken = None
            reason = f"Mass Mention ({mention_count} mentions)"

            try:
                if punishment == "Mute":
                    timeout_duration = discord.utils.utcnow() + timedelta(minutes=3)
                    await user.edit(timed_out_until=timeout_duration, reason=reason)
                    action_taken = "Muted for 3 minutes"
                elif punishment == "Kick":
                    await user.kick(reason=reason)
                    action_taken = "Kicked"
                elif punishment == "Ban":
                    await user.ban(reason=reason)
                    action_taken = "Banned"
                await message.delete()
                    
                simple_embed = discord.Embed(title="Automod Anti Mass-Mention", color=0xff0000)
                simple_embed.description = f"{emojis.TICK} | {user.mention} has been successfully **{action_taken}** for **mass mentioning.**"
                
                simple_embed.set_footer(text="Use the “automod logging” command to get automod logs if it is not enabled.", icon_url=self.bot.user.display_avatar.url)
                await channel.send(view = embed_to_view(simple_embed), delete_after=30)

                await log_automod_action(
                    guild, user, channel, action_taken, reason,
                    title='Automod Log: Anti mass mention',
                    log_channel_id=gate.log_channel_id,
                )

            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass
            except Exception:
                pass

    @commands.Cog.listener()
    async def on_rate_limit(self, message):
        await asyncio.sleep(10)

