from utils.database import connect
import discord
from discord.ext import commands
import asyncio
import datetime
import pytz
from utils.config import NON_RECOVERABLE_CHANNEL_IDS, TRUSTED_TEMP_VOICE_BOT_IDS

class AntiChannelDelete(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.event_limits = {}
        self.cooldowns = {}
        self.intentional_deletions = set()

    def mark_intentional(self, channel_id):
        self.intentional_deletions.add(channel_id)

    def can_fetch_audit(self, guild_id, event_name, max_requests=5, interval=10, cooldown_duration=300):
        now = datetime.datetime.now()
        self.event_limits.setdefault(guild_id, {}).setdefault(event_name, []).append(now)

        timestamps = self.event_limits[guild_id][event_name]
        timestamps = [t for t in timestamps if (now - t).total_seconds() <= interval]
        self.event_limits[guild_id][event_name] = timestamps

        if guild_id in self.cooldowns and event_name in self.cooldowns[guild_id]:
            if (now - self.cooldowns[guild_id][event_name]).total_seconds() < cooldown_duration:
                return False
            del self.cooldowns[guild_id][event_name]

        if len(timestamps) > max_requests:
            self.cooldowns.setdefault(guild_id, {})[event_name] = now
            return False
        return True

    async def fetch_audit_logs(self, guild, action, target_id, retries=5):
        if not guild.me.guild_permissions.view_audit_log:
            return None
        for attempt in range(retries):
            try:
                async for entry in guild.audit_logs(action=action, limit=10):
                    if entry.target.id != target_id:
                        continue
                    now = datetime.datetime.now(pytz.utc)
                    if (now - entry.created_at).total_seconds() * 1000 < 3600000:
                        return entry
            except Exception:
                pass
            if attempt < retries - 1:
                await asyncio.sleep(0.5)
        return None

    @commands.Cog.listener()
    async def on_guild_channel_delete(self, channel):
        guild = channel.guild
        if channel.id in NON_RECOVERABLE_CHANNEL_IDS:
            return
        if channel.id in self.intentional_deletions:
            self.intentional_deletions.discard(channel.id)
            return

        logs = await self.fetch_audit_logs(guild, discord.AuditLogAction.channel_delete, channel.id)
        async with connect('anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()
            if logs is None:
                return

            executor = logs.user
            if executor.id in TRUSTED_TEMP_VOICE_BOT_IDS:
                return

            if executor.id == self.bot.user.id:
                return

            if not antinuke_status or not antinuke_status[0] or executor.id in {guild.owner_id, self.bot.user.id}:
                return

            async with db.execute("SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?", (guild.id, executor.id)) as cursor:
                extra_owner = await cursor.fetchone()

            async with db.execute("SELECT chdl FROM whitelisted_users WHERE guild_id = ? AND user_id = ?", (guild.id, executor.id)) as cursor:
                whitelist_status = await cursor.fetchone()
            if extra_owner or (whitelist_status and whitelist_status[0]):
                return

            await self.ban_executor(guild, executor)

    async def ban_executor(self, guild, executor, retries=3):
        while retries > 0:
            try:
                await guild.ban(executor, reason="Channel Delete | Unwhitelisted User")
                return
            except discord.Forbidden:
                return
            except discord.HTTPException as error:
                if error.status != 429 or not error.response:
                    return
                retry_after = error.response.headers.get('Retry-After')
                if not retry_after:
                    return
                await asyncio.sleep(float(retry_after))
                retries -= 1
            except Exception:
                return
