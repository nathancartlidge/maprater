import logging

import discord
from discord.commands import Option, slash_command
from discord.ext import commands

from embed_handler import QUAL, MapButtons, UndoLast
from db_handler import DatabaseHandler


class BaseCommands(commands.Cog):
    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler

    @slash_command(description="Create rating buttons")
    async def make_buttons(self, ctx: discord.context.ApplicationContext):
        """
        Create map-rating buttons.
        Note that this will only work once per channel?
        """
        logging.info("Created buttons - Invoked by %s", ctx.author)
        await ctx.respond(
            content="Select a map to vote on:",
            view=MapButtons(self.db_handler)
        )

    @slash_command(description="Get raw data")
    async def data(self, ctx: discord.context.ApplicationContext):
        """Extracts raw data from the bot"""
        logging.debug("Getting Raw Data - Invoked by %s", ctx.author)
        lines = await self.db_handler.get_line_count(ctx.guild_id)
        if lines != -1:
            await ctx.respond(
                content=f"{lines} entries",
                file=discord.File(f"{self.db_handler.root_dir}{ctx.guild_id}.db"),
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
        """Prints the last `n` pieces of data to discord, with option to delete"""
        logging.debug("Getting last %s rows - Invoked by %s",
                      count, ctx.author)
        ids, lines = await self.db_handler.get_last(ctx.guild_id, count)
        if len(lines) == 0:
            await ctx.respond(content="No ratings found!", ephemeral=True)
        else:
            lines = self._format_lines(lines)
            await ctx.respond(
                content="\n".join(lines),
                view=UndoLast(lines, ids, self.db_handler),
                ephemeral=True
            )

    def _format_lines(self, lines):
        """convert lines into pretty strings"""
        output = []
        for (username, map_name, result, role, sentiment, datetime) in lines:
            result_string = {"w": "Win", "l": "Loss", "x": "Draw"}[result]
            role_string = {"t": ":shield:", "d": ":gun:", "s": ":stethoscope:"}[role]
            sent_string = QUAL[sentiment]

            output.append(f"{username} <t:{datetime}:R>: {result_string} on "
                          + f"*{map_name}* ({role_string}) - *'{sent_string}'*")

        return output
