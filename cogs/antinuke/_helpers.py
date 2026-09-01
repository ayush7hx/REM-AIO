from __future__ import annotations

import datetime
import logging
from typing import Any

import discord
import pytz

from utils.database import connect
from utils.config import PRIMARY_OWNER_ID

log = logging.getLogger(__name__)


class AuditRateLimiter:
    def __init__(self, *, max_requests: int = 5, interval: int = 10, cooldown_duration: int = 300) -> None:
        self.max_requests = max_requests
        self.interval = interval
        self.cooldown_duration = cooldown_duration
        self.event_limits: dict[int, dict[str, list[datetime.datetime]]] = {}
        self.cooldowns: dict[int, dict[str, datetime.datetime]] = {}

    def can_fetch(self, guild_id: int, event_name: str) -> bool:
        now = datetime.datetime.now()
        self.event_limits.setdefault(guild_id, {}).setdefault(event_name, []).append(now)

        timestamps = self.event_limits[guild_id][event_name]
        timestamps = [t for t in timestamps if (now - t).total_seconds() <= self.interval]
        self.event_limits[guild_id][event_name] = timestamps

        if guild_id in self.cooldowns and event_name in self.cooldowns[guild_id]:
            if (now - self.cooldowns[guild_id][event_name]).total_seconds() < self.cooldown_duration:
                return False
            del self.cooldowns[guild_id][event_name]

        if len(timestamps) > self.max_requests:
            self.cooldowns.setdefault(guild_id, {})[event_name] = now
            return False
        return True


async def is_antinuke_enabled(guild_id: int) -> bool:
    async with connect("anti.db") as db:
        async with db.execute("SELECT status FROM antinuke WHERE guild_id = ?", (guild_id,)) as cursor:
            row = await cursor.fetchone()
    return bool(row and row[0])


async def is_extra_owner(guild_id: int, user_id: int) -> bool:
    async with connect("anti.db") as db:
        async with db.execute(
            "SELECT 1 FROM extraowners WHERE guild_id = ? AND owner_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
    return row is not None


async def is_whitelisted(guild_id: int, user_id: int, column: str) -> bool:
    allowed = {
        "ban", "kick", "prune", "botadd", "serverup", "memup",
        "chcr", "chdl", "chup", "rlcr", "rlup", "rldl",
        "meneve", "mngweb", "mngstemo",
    }
    if column not in allowed:
        raise ValueError(f"Invalid whitelist column: {column}")
    async with connect("anti.db") as db:
        async with db.execute(
            f"SELECT {column} FROM whitelisted_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        ) as cursor:
            row = await cursor.fetchone()
    return bool(row and row[0])


async def fetch_recent_audit_entry(
    guild: discord.Guild,
    action: discord.AuditLogAction,
    *,
    target_id: int | None = None,
    max_age_seconds: float = 3600,
) -> discord.AuditLogEntry | None:
    if not guild.me.guild_permissions.view_audit_log:
        return None
    try:
        async for entry in guild.audit_logs(action=action, limit=6):
            if target_id is not None and getattr(entry.target, "id", None) != target_id:
                continue
            now = datetime.datetime.now(pytz.utc)
            if (now - entry.created_at).total_seconds() > max_age_seconds:
                continue
            return entry
    except discord.Forbidden:
        return None
    except Exception:
        log.exception("Failed to fetch audit log for guild %s action %s", guild.id, action)
    return None


def is_trusted_actor(guild: discord.Guild, actor_id: int, bot_user_id: int) -> bool:
    return actor_id in {guild.owner_id, bot_user_id, PRIMARY_OWNER_ID}


async def is_guild_blacklisted(guild_id: int) -> bool:
    async with connect("block.db") as db:
        cursor = await db.execute(
            "SELECT 1 FROM guild_blacklist WHERE guild_id = ?",
            (str(guild_id),),
        )
        row = await cursor.fetchone()
    return row is not None


async def should_skip_antinuke_actor(guild: discord.Guild, actor_id: int, bot_user_id: int, column: str) -> bool:
    if is_trusted_actor(guild, actor_id, bot_user_id):
        return True
    if await is_extra_owner(guild.id, actor_id):
        return True
    if await is_whitelisted(guild.id, actor_id, column):
        return True
    return False
