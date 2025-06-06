import discord
import logging

from embed_handler import BUTTON_MAPS, MapButtons, PlotButtons


class MapRater(discord.Bot):
    def __init__(self, db_handler, description="Overwatch Map Rating", *args, **options):
        super().__init__(description, *args, **options)
        self.db_handler = db_handler

    async def on_ready(self):
        """Log and set presence"""
        logging.info("Bot started")
        await self.change_presence(
            activity=discord.Game(name="the worst ow2 maps!")
        )
        # enable persistence for the map buttons
        for cls in BUTTON_MAPS.values():
            self.add_view(cls(self.db_handler))
        self.add_view(PlotButtons(self.db_handler))

    async def on_connect(self):
        logging.info("Syncing commands")
        await self.sync_commands()
