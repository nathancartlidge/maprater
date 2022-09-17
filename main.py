from heapq import heapify
import os
from re import sub
import time
import asyncio
import logging
import discord

from discord.ext import commands
from discord_slash import SlashCommand, SlashContext, ComponentContext
from discord_slash.utils.manage_commands import create_option

from dotenv import load_dotenv
from datetime import datetime as dt

from embed_handler import make_map_buttons, write_line, make_quality_buttons, make_role_buttons
from embed_handler import make_submit_button, make_winloss_buttons, remove_last_line, get_line_count

# Initialise a bot object with a command prefix
bot = commands.Bot()
slash = SlashCommand(bot, sync_commands=True)

MAPS = [
    'Busan', 'Ilios', 'Lijang', 'Nepal', 'Oasis',
    'Hanamura', 'Volskaya', 'Anubis',
    'WPG', 'Junkertown', 'Route66', 'Dorado', 'Havana', 'Rialto',
    'Blizzard', 'Eich', 'Kings', 'Hollywood', 'Numbani'
]

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="the worst ow maps"))
    logging.info('Bot started')


@slash.slash(name="make_buttons",
             description="Create map rating buttons")
async def make_buttons(ctx: SlashContext):
    logging.info("Created Buttons")

    action_row, _ = make_map_buttons()
    await ctx.send("Select a map to vote on:", components=action_row)

@slash.slash(name="get_data",
             description="Get raw data")
async def get_data(ctx: SlashContext):
    if (lines := await get_line_count()) != -1:
        await ctx.send(f"{lines - 1} entries", file=discord.File("data.csv"), hidden=True)
    else:
        await ctx.send(":/ No file found?")

@slash.slash(name="undo",
             description="Remove the last line from the file")
async def undo(ctx: ComponentContext):
    logging.info("removing last line")
    line = await remove_last_line()
    if line is None:
        await ctx.reply(":/ No file found, unable to delete", hidden=True)
    else:
        await ctx.reply(f"Removed line: `{repr(line)}`", hidden=True)
        logging.info("removed line: %s", repr(line))

@slash.component_callback(components=MAPS)
async def button_press(ctx: ComponentContext, ttl=60):
    ow_map = ctx.component_id
    logging.info(f"posted {ow_map} options")

    prefix = str(time.monotonic()) + "_"

    ar1, bi1 = make_winloss_buttons(prefix=prefix)
    ar2, bi2 = make_role_buttons(prefix=prefix)
    ar3, ar4, bi3 = make_quality_buttons(prefix=prefix)
    ar5, bi4 = make_submit_button(prefix=prefix)

    deltime = round(time.time() + ttl)
    line = f"rating for **{ctx.component_id}**: (deletes <t:{deltime}:R>)"

    await ctx.reply(line, components=[ar1, ar2, ar3, ar4, ar5], delete_after=ttl)

    has_voted = []
    data = {}

    @slash.component_callback(components=bi1)
    async def winloss_press(subctx: ComponentContext):
        winloss = subctx.component_id[-1]
        logging.info(f"{ow_map} - {subctx.author} - {winloss}")

        if str(subctx.author) not in data:
            data[str(subctx.author)] = {}
        data[str(subctx.author)]["winloss"] = winloss

        await subctx.defer(ignore=True, hidden=True)

    @slash.component_callback(components=bi2)
    async def role_press(subctx: ComponentContext):
        role = subctx.component_id[-1]
        logging.info(f"{ow_map} - {subctx.author} - {role}")

        if str(subctx.author) not in data:
            data[str(subctx.author)] = {}
        data[str(subctx.author)]["role"] = role

        await subctx.defer(ignore=True, hidden=True)

    @slash.component_callback(components=bi3)
    async def quality_press(subctx: ComponentContext):
        sentiment = subctx.component_id[-1]
        logging.info(f"{ow_map} - {subctx.author} - {sentiment}")

        if str(subctx.author) not in data:
            data[str(subctx.author)] = {}
        data[str(subctx.author)]["quality"] = sentiment

        await subctx.defer(ignore=True, hidden=True)

    @slash.component_callback(components=bi4)
    async def submit(subctx: ComponentContext):
        if str(subctx.author) in has_voted:
            await subctx.reply(":/ you have already voted!", hidden=True)
            await subctx.defer(ignore=True, hidden=True)
            return

        winloss = data[str(subctx.author)].get("winloss", None)
        role = data[str(subctx.author)].get("role", None)
        sentiment = data[str(subctx.author)].get("quality", None)

        if winloss is None or role is None or sentiment is None:
            await subctx.reply(":/ fill in all the details!", hidden=True)
            await subctx.defer(ignore=True, hidden=True)
            return

        await write_line(subctx.author, ow_map, winloss, role, sentiment, dt.now().isoformat())
        
        has_voted.append(str(subctx.author))
        voters_line = ", ".join(map(lambda f: f.split("#")[0], has_voted))

        await subctx.origin_message.edit(content=line + "\nVoters: *"
                                                 + voters_line + "*")

        await subctx.defer(ignore=True, hidden=True)

    await asyncio.sleep(ttl+10)
    del quality_press, winloss_press, role_press, submit
    del ar1, ar2, ar3, ar4, bi1, bi2, bi3, bi4
    del has_voted, data


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    # Load in the Discord API key from your .env
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")

    # Start the bot using the API key
    slash.sync_all_commands()
    bot.run(TOKEN)
