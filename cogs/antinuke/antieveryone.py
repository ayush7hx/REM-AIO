from utils.database import connect
import discord
from discord.ext import commands
import asyncio
import datetime
import logging
from datetime import timedelta
from utils.config import PRIMARY_OWNER_ID

log = logging.getLogger(__name__)


class AntiEveryone(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_limits = {}

    async def can_message_delete(self, guild_id, event_name, max_requests=5, interval=10, cooldown_duration=300):
        now = datetime.datetime.now()
        self.event_limits.setdefault(guild_id, {}).setdefault(event_name, []).append(now)

        timestamps = self.event_limits[guild_id][event_name]
        timestamps = [t for t in timestamps if (now - t).total_seconds() <= interval]
        self.event_limits[guild_id][event_name] = timestamps

        if len(timestamps) > max_requests:
            return False

        return True

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.guild is None or not message.mention_everyone:
            return

        guild = message.guild

        async with connect('anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()

            if not antinuke_status or not antinuke_status[0]:
                return

            if message.author.id in {
                PRIMARY_OWNER_ID,
                guild.owner_id,
                self.bot.user.id,
            }:
                return

            async with db.execute("SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?", (guild.id, message.author.id)) as cursor:
                extraowner_status = await cursor.fetchone()

            if extraowner_status:
                return

            async with db.execute("SELECT meneve FROM whitelisted_users WHERE guild_id = ? AND user_id = ?", (guild.id, message.author.id)) as cursor:
                whitelist_status = await cursor.fetchone()

            if whitelist_status and whitelist_status[0]:
                return

            
            if not await self.can_message_delete(guild.id, 'mention_everyone'):
                return

            try:
                await self.timeout_user(message.author)
                await self.delete_everyone_messages(message.channel)
            except Exception:
                log.exception("Antinuke everyone handler failed for user %s", message.author.id)

    async def timeout_user(self, user):
        if user.id == PRIMARY_OWNER_ID:
            return

        retries = 3
        duration = 60 * 60  
        while retries > 0:
            try:
                await user.edit(timed_out_until=discord.utils.utcnow() + timedelta(seconds=duration), reason="Mentioned Everyone/Here | Unwhitelisted User")
                return  
            except discord.Forbidden:
                return
            except discord.HTTPException as exc:
                log.warning("Failed to timeout %s: %s", user.id, exc)
                if exc.status == 429:
                    retry_after = exc.response.headers.get('Retry-After') if exc.response else None
                    if retry_after:
                        await asyncio.sleep(float(retry_after))
                        retries -= 1
                else:
                    return
            except discord.errors.RateLimited as exc:
                log.warning("Rate limited while timing out %s; retrying in %ss", user.id, exc.retry_after)
                await asyncio.sleep(exc.retry_after)
                retries -= 1
            except Exception:
                log.exception("Unexpected error while timing out %s", user.id)
                return

        log.warning("Failed to timeout %s after multiple attempts", user.id)

    async def delete_everyone_messages(self, channel):
        retries = 3
        while retries > 0:
            try:
                async for msg in channel.history(limit=100):
                    if msg.mention_everyone:
                        await msg.delete()
                        await asyncio.sleep(3)  
                return  
            except discord.Forbidden:
                return
            except discord.HTTPException as exc:
                log.warning("Failed to delete everyone messages: %s", exc)
                if exc.status == 429:
                    retry_after = exc.response.headers.get('Retry-After') if exc.response else None
                    if retry_after:
                        await asyncio.sleep(float(retry_after))
                        retries -= 1
                else:
                    return
            except discord.errors.RateLimited as exc:
                log.warning("Rate limited while deleting everyone messages; retrying in %ss", exc.retry_after)
                await asyncio.sleep(exc.retry_after)
                retries -= 1
            except Exception:
                log.exception("Unexpected error while deleting everyone messages")
                return

        log.warning("Failed to delete everyone messages after multiple attempts")
