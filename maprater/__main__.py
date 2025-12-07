"""Main bot launch file"""

import os
import logging
import argparse
from pathlib import Path

from dotenv import load_dotenv

from maprater.bot.core import MapRater
from maprater.bot.commands import BaseCommands
# from maprater.archive.ocr_utils import OcrCog
from maprater.bot.plotting import PlotCommands
from maprater.archive.rank_update import UpdateCommand
from maprater.data.db_handler import DatabaseHandler

def run_args():
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
        data_loc = Path("../maprater-data/")
        db_handler = DatabaseHandler(root_dir="../maprater-data/")
    else:
        data_loc = Path("/data/")
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

    if args.all_servers and not args.debug:
        logging.warning(
            "starting in single-guild mode - commands may not update on other servers"
        )
        bot = MapRater(db_handler=db_handler, debug_guilds=[GUILD])

    else:
        logging.warning(
            "starting in single-guild mode - commands may not update on other servers"
        )
        bot = MapRater(db_handler=db_handler, debug_guilds=[GUILD])

    logging.info(":)")

    if args.debug:

        @bot.slash_command()
        async def ping(ctx):
            """Show bot latency [debug]"""
            await ctx.respond(f"pong! [{round(bot.latency, 2)}s]", ephemeral=True)

    bot.add_cog(BaseCommands(bot.db_handler))
    bot.add_cog(PlotCommands(bot.db_handler))
    bot.add_cog(UpdateCommand(bot.db_handler))
    # bot.add_cog(OcrCog(data_loc))

    bot.run(TOKEN)

if __name__ == "__main__":
    run_args()