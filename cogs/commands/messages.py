import discord
from discord.ext import commands
from datetime import datetime

from utils.database import open_connection
from utils.cv2_compat import embed_to_view, embeds_to_view

MESSAGES_SCHEMA = """
    CREATE TABLE IF NOT EXISTS messages (
        guild_id INTEGER,
        user_id INTEGER,
        date TEXT,
        count INTEGER
    )
"""

DB_PATH = "messages.db"


class Messages(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.db = None

    async def cog_load(self) -> None:
        self.db = await open_connection(DB_PATH)
        await self.db.execute(MESSAGES_SCHEMA)
        await self.db.commit()

    async def cog_unload(self) -> None:
        if self.db is not None:
            await self.db.close()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        today = datetime.utcnow().strftime("%Y-%m-%d")
        async with self.db.execute(
            "SELECT count FROM messages WHERE guild_id = ? AND user_id = ? AND date = ?",
            (message.guild.id, message.author.id, today),
        ) as cursor:
            result = await cursor.fetchone()

        if result:
            await self.db.execute(
                "UPDATE messages SET count = count + 1 WHERE guild_id = ? AND user_id = ? AND date = ?",
                (message.guild.id, message.author.id, today),
            )
        else:
            await self.db.execute(
                "INSERT INTO messages (guild_id, user_id, date, count) VALUES (?, ?, ?, 1)",
                (message.guild.id, message.author.id, today),
            )
        await self.db.commit()

    @commands.command(name="messages")
    async def messages(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        today = datetime.utcnow().strftime("%Y-%m-%d")

        async with self.db.execute(
            "SELECT date, count FROM messages WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, member.id),
        ) as cursor:
            data = await cursor.fetchall()

        total = sum(row[1] for row in data)
        today_count = sum(row[1] for row in data if row[0] == today)
        unique_days = set(row[0] for row in data)
        daily_average = round(total / len(unique_days), 2) if unique_days else 0

        embed = discord.Embed(
            description=(
                f"**User** ``:`` {member.mention}\n"
                f"**Daily Messages** ``:`` {daily_average}\n"
                f"**Today Messages** ``:`` {today_count}\n"
                f"**Total Messages** ``:`` {total}"
            ),
            color=discord.Color.blurple()
        )
        embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.display_avatar.url)
        await ctx.send(view=embed_to_view(embed))


async def setup(client):
    await client.add_cog(Messages(client))