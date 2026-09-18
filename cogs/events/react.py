from utils import emojis as emoji_registry

import logging

import discord
from discord.ext import commands

log = logging.getLogger(__name__)


class React(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        for owner in self.bot.owner_ids:
            if f"<@{owner}>" in message.content:
                try:
                    if owner == 677952614390038559:
                        
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
