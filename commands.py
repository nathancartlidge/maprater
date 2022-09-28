import logging

import discord
from discord.commands import Option, slash_command
from discord.ext import commands

from embed_handler import MapButtons, UndoLast
from file_handler import FileHandler


class BaseCommands(commands.Cog):
    def __init__(self, file_handler: FileHandler):
        self.file_handler = file_handler

    @slash_command(description="Create rating buttons")
    async def make_buttons(self, ctx: discord.context.ApplicationContext):
        """
        Create map-rating buttons.
        Note that this will only work once per channel?
        """
        logging.info("Created buttons - Invoked by %s", ctx.author)
        await ctx.respond(
            content="Select a map to vote on:",
            view=MapButtons()
        )

    @slash_command(description="Get raw data")
    async def data(self, ctx: discord.context.ApplicationContext):
        """Extracts raw data from the bot"""
        logging.debug("Getting Raw Data - Invoked by %s", ctx.author)
        lines = await self.file_handler.get_line_count()
        if lines != -1:
            await ctx.respond(
                content=f"{lines} entries",
                file=discord.File(self.file_handler.filename),
                ephemeral=True
            )
        else:
            await ctx.respond(content="Error - No data found?", ephemeral=True)

    @slash_command(description="Get the last n rows of data")
    async def last(
        self, ctx: discord.context.ApplicationContext,
        count: Option(int, description="Number of entries to return",
                      min_value=1, max_value=20, default=1)
    ):
        logging.debug("Getting last %s rows - Invoked by %s",
                      count, ctx.author)
        lines = await self.file_handler.get_last(count)
        await ctx.respond(
            content=f"```{''.join(lines)}```",
            view=UndoLast(lines, count, self.file_handler),
            ephemeral=True
        )
