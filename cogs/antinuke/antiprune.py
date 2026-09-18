from utils.database import connect
import discord
from discord.ext import commands
import datetime
import asyncio
import logging
import pytz
from utils.config import PRIMARY_OWNER_ID

log = logging.getLogger(__name__)


class AntiPrune(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def fetch_audit_logs(self, guild, action):
        try:
            async for entry in guild.audit_logs(action=action, limit=1):
                now = datetime.datetime.now(pytz.utc)
                created_at = entry.created_at
                difference = (now - created_at).total_seconds() * 1000
                    
                if difference >= 3600000:
                    return  None

                return entry
    
        except Exception:
            log.exception("Error fetching prune audit logs for guild %s", guild.id)
        return None

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild = member.guild
        async with connect('anti.db') as db:
            async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild.id,)) as cursor:
                antinuke_status = await cursor.fetchone()

            if not antinuke_status or not antinuke_status[0]:
                return

            log_entry = await self.fetch_audit_logs(guild, discord.AuditLogAction.member_prune)
            if log_entry is None:
                return

            executor = log_entry.user
            

            if executor.id in {guild.owner_id, self.bot.user.id, PRIMARY_OWNER_ID}:
                return

            async with db.execute("SELECT prune FROM whitelisted_users WHERE guild_id = ? AND user_id = ?", (guild.id, executor.id)) as cursor:
                whitelist_status = await cursor.fetchone()

            if whitelist_status and whitelist_status[0]:
                return

            async with db.execute("SELECT owner_id FROM extraowners WHERE guild_id = ? AND owner_id = ?", (guild.id, executor.id)) as cursor:
                extra_owner_status = await cursor.fetchone()

            if extra_owner_status:
                return

            await self.ban_executor(guild, executor)

    async def ban_executor(self, guild, executor):
        retries = 3
        while retries > 0:
            try:
                await guild.ban(executor, reason="Member Prune | Unwhitelisted User")
                return
            except discord.Forbidden:
                log.warning("Failed to ban %s for prune: missing permissions", executor.id)
                return
            except discord.HTTPException as exc:
                if exc.status == 429:
                    retry_after = exc.response.headers.get('Retry-After') if exc.response else None
                    if retry_after:
                        await asyncio.sleep(float(retry_after))
                        retries -= 1
                else:
                    log.warning("Antinuke prune ban failed for %s: %s", executor.id, exc)
                    return
            except discord.errors.RateLimited as exc:
                log.warning("Rate limited while banning %s for prune; retrying in %ss", executor.id, exc.retry_after)
                await asyncio.sleep(exc.retry_after)
                retries -= 1
            except Exception:
                log.exception("Unexpected error while banning %s for prune", executor.id)
                return

        log.warning("Failed to ban %s for prune after multiple attempts", executor.id)
