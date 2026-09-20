from utils import emojis as emoji_registry

import asyncio
import logging
from pathlib import Path

import discord
from discord.ext import commands
from utils.config import PRIMARY_OWNER_ID

log = logging.getLogger(__name__)


class React(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self._owner_emoji = None
        self._owner_emoji_lock = asyncio.Lock()

    async def _get_owner_emoji(self):
        if self._owner_emoji is not None:
            return self._owner_emoji

        async with self._owner_emoji_lock:
            if self._owner_emoji is not None:
                return self._owner_emoji

            try:
                application_emojis = await self.bot.fetch_application_emojis()
                emoji_registry.apply_application_emojis(application_emojis)
                self._owner_emoji = next(
                    (
                        discord.PartialEmoji(
                            name=emoji.name,
                            id=emoji.id,
                            animated=emoji.animated,
                        )
                        for emoji in application_emojis
                        if emoji.name.lower() == "owner"
                    ),
                    None,
                )
                if self._owner_emoji is None:
                    asset_path = Path("assets/emojis/OWNER.gif")
                    if asset_path.exists():
                        created = await self.bot.create_application_emoji(
                            name="OWNER",
                            image=asset_path.read_bytes(),
                        )
                        self._owner_emoji = discord.PartialEmoji(
                            name=created.name,
                            id=created.id,
                            animated=created.animated,
                        )
            except (discord.HTTPException, OSError):
                log.exception("Could not resolve the application OWNER emoji")

            return self._owner_emoji or emoji_registry.OWNER

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        for owner in self.bot.owner_ids:
            if (
                any(mention.id == owner for mention in message.mentions)
                or f"<@{owner}>" in message.content
                or f"<@!{owner}>" in message.content
            ):
                try:
                    if owner == PRIMARY_OWNER_ID:
                        await message.add_reaction(await self._get_owner_emoji())
                    elif owner == 677952614390038559:
                        
                        reaction_emojis = [
                            f"{emoji_registry.REM_OWNER}",
                            f"{emoji_registry.EMOJI_7CLUB_BAN}",
                            f"{emoji_registry.LAND_YILDIZ}",
                            f"{emoji_registry.ROSE}",
                            f"{emoji_registry.LAND_YILDIZ}",
                            f"{emoji_registry.EMOJI_37496ALERT}",
                            f"{emoji_registry.SQ_HEADMOD}",
                            f"{emoji_registry.DC_REDCROWNESPORTS}",
                            f"{emoji_registry.GIFD}",
                            f"{emoji_registry.GIFN}",
                            f"{emoji_registry.MAX__A}",
                            f"{emoji_registry.HEERIYE}",
                            f"{emoji_registry.HEART_EM}",
                            f"{emoji_registry.STAR}",
                            f"{emoji_registry.KING}",
                            f"{emoji_registry.HEADMOD}",
                            f"{emoji_registry.SG_RD} ",
                            f"{emoji_registry.REDHEART}",
                            f" {emoji_registry.STAR}"
                        ]
                        for emoji in reaction_emojis:
                            await message.add_reaction(emoji)
                    else:
                        
                        await message.add_reaction(f"{emoji_registry.REM_OWNER}")
                except discord.errors.RateLimited:
                    log.warning("Auto reaction rate limited for owner mention")
                except discord.HTTPException as error:
                    if error.status == 429:
                        log.warning("Auto reaction blocked by Discord rate limit")
                    else:
                        log.exception("Auto react owner mention failed")
                except Exception:
                    log.exception("Auto react owner mention failed")
