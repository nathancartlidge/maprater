import os
import logging

from dotenv import load_dotenv

from bot import MapRater
from commands import BaseCommands
from plotting import PlotCommands
from file_handler import FileHandler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Load a discord API key from a .env file
    load_dotenv()
    TOKEN = os.getenv('DISCORD_TOKEN')
    GUILD = os.getenv('DISCORD_GUILD', None)

    file_handler = FileHandler("/data/data.csv")
    bot = MapRater(file_handler=file_handler, debug_guilds=[GUILD])

    @bot.slash_command()
    async def ping(ctx):
        await ctx.respond(f"pong! [{round(bot.latency, 2)}s]", ephemeral=True)

    bot.add_cog(BaseCommands(bot.file_handler))
    bot.add_cog(PlotCommands(bot.file_handler))

    bot.run(TOKEN)
