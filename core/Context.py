from __future__ import annotations

from discord.ext import commands
import discord
import functools
from typing import Optional, Any
import asyncio
import logging
import time

from utils.components_v2 import error_panel, warning_panel

__all__ = ("Context", )

log = logging.getLogger(__name__)
_CLOUDFLARE_RATE_LIMIT_PAUSE = 15 * 60


class CloudflareRateLimitActive(commands.CommandError):
    def __init__(self, retry_after: float) -> None:
        self.retry_after = retry_after
        super().__init__(
            f"Discord Cloudflare rate limit is active for {retry_after:.0f} seconds"
        )


def pause_for_cloudflare_rate_limit(
    bot: commands.Bot, error: discord.HTTPException
) -> bool:
    response_text = str(getattr(error, "text", "")).lower()
    if error.status != 429 or not (
        "error 1015" in response_text
        or ("cloudflare" in response_text and "rate limited" in response_text)
    ):
        return False

    headers = getattr(getattr(error, "response", None), "headers", {}) or {}
    retry_after = headers.get("Retry-After")
    try:
        delay = (
            max(float(retry_after), 1.0)
            if retry_after is not None
            else _CLOUDFLARE_RATE_LIMIT_PAUSE
        )
    except (TypeError, ValueError, OverflowError):
        delay = _CLOUDFLARE_RATE_LIMIT_PAUSE

    setattr(
        bot,
        "_discord_cloudflare_pause_until",
        max(
            getattr(bot, "_discord_cloudflare_pause_until", 0.0),
            time.monotonic() + delay,
        ),
    )
    log.warning(
        "Discord Cloudflare 1015 detected; pausing Context sends for %.0f seconds.",
        delay,
    )
    return True


def _ensure_discord_send_allowed(bot: commands.Bot) -> None:
    now = time.monotonic()
    pause_until = getattr(bot, "_discord_cloudflare_pause_until", 0.0)
    if pause_until > now:
        raise CloudflareRateLimitActive(pause_until - now)
    if pause_until:
        setattr(bot, "_discord_cloudflare_pause_until", 0.0)


class Context(commands.Context):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return "<core.Context>"

    @property
    async def session(self):
        return self.bot.session

    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.Message]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    def with_type(func):

        @functools.wraps(func)
        async def wrapped(self, *args, **kwargs):
            context = args[0] if isinstance(args[0],
                                            commands.Context) else args[1]
            try:
                async with context.typing():
                    await func(*args, **kwargs)
            except discord.Forbidden:  
                await func(*args, **kwargs)

        return wrapped

    async def show_help(self, command: str = None) -> Any:
        cmd = self.bot.get_command('help')
        command = command or self.command.qualified_name
        await self.invoke(cmd, command=command)

    async def send(self,
                   content: Optional[str] = None,
                   **kwargs) -> Optional[discord.Message]:
        _ensure_discord_send_allowed(self.bot)
        if not self.channel.permissions_for(self.me).send_messages:
            try:
                await self.author.send(
                    view=warning_panel(
                        "I don't have permission to send messages in that channel.",
                        title="Missing Permission",
                    )
                )
            except discord.Forbidden:
                pass
            except discord.HTTPException as error:
                pause_for_cloudflare_rate_limit(self.bot, error)
                raise
            return
        try:
            return await super().send(content, **kwargs)
        except discord.HTTPException as error:
            pause_for_cloudflare_rate_limit(self.bot, error)
            raise

    async def reply(self,
                    content: Optional[str] = None,
                    **kwargs) -> Optional[discord.Message]:
        _ensure_discord_send_allowed(self.bot)
        if not self.channel.permissions_for(self.me).send_messages:
            try:
                await self.author.send(
                    view=warning_panel(
                        "I don't have permission to send messages in that channel.",
                        title="Missing Permission",
                    )
                )
            except discord.Forbidden:
                pass
            except discord.HTTPException as error:
                pause_for_cloudflare_rate_limit(self.bot, error)
                raise
            return
        return await super().reply(content, **kwargs)

    async def error(self, content: str, *, title: str = "Error", **kwargs) -> Optional[discord.Message]:
        return await self.reply(
            view=error_panel(content, title=title),
            mention_author=False,
            **kwargs,
        )

    async def release(self, delay: Optional[int] = None) -> None:
        delay = delay or 0
        await asyncio.sleep(delay)
