"""Main bot launch file"""

import os
import logging
import argparse

from dotenv import load_dotenv

from bot import MapRater
from commands import BaseCommands
from rank_update import UpdateCommand
from data.handler import DatabaseHandler

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--debug", action="store_true", default=False)
    parser.add_argument("-v", "--verbose", action="store_true", default=False)
    parser.add_argument("-a", "--all-servers", action="store_false", default=True)
    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    if args.debug:
        db_handler = DatabaseHandler(root_dir="../maprater-data/")
    else:
        db_handler = DatabaseHandler(root_dir="/data/")

    # Load a discord API key from a .env file
    load_dotenv()
    if args.debug:
        logging.info("Using debug variables")
        TOKEN = os.getenv("DISCORD_TOKEN_TEST")
        GUILD = os.getenv("DISCORD_GUILD_TEST", None)

    else:
        TOKEN = os.getenv("DISCORD_TOKEN")
        GUILD = os.getenv("DISCORD_GUILD", None)

    if args.all_servers:
        bot = MapRater(db_handler=db_handler, debug_guilds=[GUILD])

    else:
        bot = MapRater(db_handler=db_handler)

    if args.debug:
        @bot.slash_command()
        async def ping(ctx):
            """Show bot latency [debug]"""
            await ctx.respond(f"pong! [{round(bot.latency, 2)}s]", ephemeral=True)

    bot.add_cog(BaseCommands(bot.db_handler))
    bot.add_cog(UpdateCommand(bot.db_handler))

    bot.run(TOKEN)
