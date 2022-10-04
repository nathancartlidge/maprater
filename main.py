import os
import logging
import argparse

from dotenv import load_dotenv

from bot import MapRater
from commands import BaseCommands
from plotting import PlotCommands
from file_handler import FileHandler

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true", default=False)
    args = parser.parse_args()

    # Load a discord API key from a .env file
    load_dotenv()
    if args.debug:
        logging.info("Using debug variables")
        TOKEN = os.getenv("DISCORD_TOKEN_TEST")
        GUILD = os.getenv("DISCORD_GUILD_TEST", None)

    else:
        TOKEN = os.getenv("DISCORD_TOKEN")
        GUILD = os.getenv("DISCORD_GUILD", None)

    file_handler = FileHandler("/data/ow2_data.csv")
    bot = MapRater(file_handler=file_handler, debug_guilds=[GUILD])

    @bot.slash_command()
    async def ping(ctx):
        await ctx.respond(f"pong! [{round(bot.latency, 2)}s]", ephemeral=True)

    bot.add_cog(BaseCommands(bot.file_handler))
    bot.add_cog(PlotCommands(bot.file_handler))

    bot.run(TOKEN)
