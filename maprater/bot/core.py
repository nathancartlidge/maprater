import discord
from discord import app_commands
from discord.ext import commands
import logging

from maprater.bot.embed_handler import BUTTON_MAPS, PlotButtons


class MapRater(discord.Client):
    def __init__(self, db_handler, debug_guilds=None, *args, **options):
        super().__init__(intents=discord.Intents.default(), *args, **options)
        self.db_handler = db_handler
        self.debug_guilds = debug_guilds or []
        self.tree = app_commands.CommandTree(client=self, fallback_to_global=True)
        self._cogs: list[commands.Cog] = []

    @property
    def cogs(self):
        return self._cogs

    @cogs.setter
    def cogs(self, value):
        # do not allow setting cogs after the bot has been started
        if self.is_ready():
            raise RuntimeError("Cannot set cogs after the bot has been started")
        self._cogs = value

    async def setup_hook(self):
        """Called when the bot is setting up, before connecting to Discord"""
        logging.info("Syncing commands")

        for cog in self.cogs:
            for command in cog.get_commands() + cog.get_app_commands():
                self.tree.add_command(command)

        # Sync commands for debug guilds if specified
        print([c.name for c in await self.tree.fetch_commands()])
        if self.debug_guilds:
            for guild_id in self.debug_guilds:
                logging.info(f"Syncing commands to guild {guild_id}")
                guild = discord.Object(id=int(guild_id))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
        else:
            logging.info("Syncing commands globally")
            await self.tree.sync()

    async def on_ready(self):
        """Log and set presence"""
        logging.info("Bot started")
        await self.change_presence(activity=discord.Game(name="the worst ow2 maps!"))
        # enable persistence for the map buttons
        for cls in BUTTON_MAPS.values():
            self.add_view(cls(self.db_handler))
        self.add_view(PlotButtons(self.db_handler))
