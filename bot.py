import discord
import logging

from embed_handler import MapButtons

class MapRater(discord.Bot):
    def __init__(self, file_handler, description="Overwatch Map Rating", *args, **options):
        super().__init__(description, *args, **options)
        self.file_handler = file_handler

    async def on_ready(self):
        """Log and set presence"""
        logging.info("Bot started")
        await self.change_presence(
            activity=discord.Game(name="the worst ow maps")
        )
        # enable persistence for the map buttons
        self.add_view(MapButtons(self.file_handler))

    async def on_connect(self):
        logging.info("Syncing commands")
        await self.sync_commands()
