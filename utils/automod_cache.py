from __future__ import annotations

from dataclasses import dataclass

from utils.cache import TTLCache
from utils.config import PRIMARY_OWNER_ID
from utils.database import connect

_automod_cache = TTLCache["AutomodGuildState"](ttl=45.0)


@dataclass(frozen=True, slots=True)
class AutomodGuildState:
    enabled: bool
    events: dict[str, str]
    ignored_channels: frozenset[int]
    ignored_roles: frozenset[int]
    log_channel_id: int | None


_EMPTY = AutomodGuildState(False, {}, frozenset(), frozenset(), None)


async def get_automod_state(guild_id: int) -> AutomodGuildState:
    key = f"automod:{guild_id}"
    cached = await _automod_cache.get(key)
    if cached is not None:
        return cached

    async with connect("automod.db") as db:
        async with db.execute(
            "SELECT enabled FROM automod WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            enabled_row = await cursor.fetchone()
        enabled = enabled_row is not None and enabled_row[0] == 1

        events: dict[str, str] = {}
        async with db.execute(
            "SELECT event, punishment FROM automod_punishments WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            for event, punishment in await cursor.fetchall():
                events[event] = punishment

        ignored_channels: set[int] = set()
        ignored_roles: set[int] = set()
        async with db.execute(
            "SELECT id, type FROM automod_ignored WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            for item_id, item_type in await cursor.fetchall():
                if item_type == "channel":
                    ignored_channels.add(int(item_id))
                elif item_type == "role":
                    ignored_roles.add(int(item_id))

        log_channel_id = None
        async with db.execute(
            "SELECT log_channel FROM automod_logging WHERE guild_id = ?",
            (guild_id,),
        ) as cursor:
            row = await cursor.fetchone()
            if row and row[0]:
                log_channel_id = int(row[0])

    state = AutomodGuildState(
        enabled=enabled,
        events=events,
        ignored_channels=frozenset(ignored_channels),
        ignored_roles=frozenset(ignored_roles),
        log_channel_id=log_channel_id,
    )
    await _automod_cache.set(key, state)
    return state


async def invalidate_automod_state(guild_id: int) -> None:
    await _automod_cache.invalidate(f"automod:{guild_id}")


@dataclass(frozen=True, slots=True)
class AutomodGate:
    punishment: str
    log_channel_id: int | None


async def automod_gate(message, event_name: str) -> AutomodGate | None:
    """Fast cached gate used by automod listeners."""
    if message.author.bot or message.guild is None:
        return None

    guild = message.guild
    user = message.author
    channel = message.channel

    me = guild.me
    if user.id in {PRIMARY_OWNER_ID, guild.owner_id} or (me and user.id == me.id):
        return None

    state = await get_automod_state(guild.id)
    if not state.enabled:
        return None

    punishment = state.events.get(event_name)
    if not punishment:
        return None

    if channel.id in state.ignored_channels:
        return None

    if any(role.id in state.ignored_roles for role in user.roles):
        return None

    return AutomodGate(punishment=punishment, log_channel_id=state.log_channel_id)