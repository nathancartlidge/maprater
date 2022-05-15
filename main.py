from asyncio.tasks import sleep
import random
import re
from tkinter import Button
import discord
import os

from discord.ext import commands
from discord_slash import SlashCommand, SlashContext, ComponentContext
from discord_slash.model import ButtonStyle
from discord_slash.utils.manage_commands import create_option
from discord_slash.utils.manage_components import create_button, create_actionrow

from dotenv import load_dotenv

from api_query import QueryRequest, execute_request, TEMPERATURE, TOP_P

# Load in the Discord API key from your .env
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD = os.getenv("DISCORD_GUILD")

# Initialise a bot object with a command prefix
bot = commands.Bot(command_prefix='!', intents=discord.Intents.all())
slash = SlashCommand(bot, sync_commands=True)
guild_ids = [GUILD]

@bot.event
async def on_ready():
    print('Bot running')
    await bot.change_presence(activity=discord.Game(name="with a knife"))

# Start the bot using the API key
bot.run(TOKEN)
