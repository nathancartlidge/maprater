"""Implements basic bot commands"""

from io import BytesIO
import logging

import discord
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.ext import commands
import pandas as pd

from embed_handler import QUAL, MapButtons, UndoLast
from db_handler import DatabaseHandler


class BaseCommands(commands.Cog):
    """Basic commands used for bot"""
    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler

    @slash_command(description="Create rating buttons")
    async def make_buttons(self, ctx: ApplicationContext):
        """
        Create map-rating buttons.
        Note that this will only work once per channel?
        """
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        logging.info("Created buttons - Invoked by %s", ctx.author)
        await ctx.respond(
            content="Select a map to vote on:",
            view=MapButtons(self.db_handler)
        )

    @slash_command(description="Get raw data")
    async def data(self, ctx: ApplicationContext,
                   format: Option(str, description="Output Data Format",
                                  default="sqlite", choices=["sqlite", "csv"])):
        """Extracts raw data from the bot"""
        logging.debug("Getting Raw Data - Invoked by %s", ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        lines = await self.db_handler.get_line_count(ctx.guild_id)

        if lines < 1:
            await ctx.respond(content=":warning: No ratings found!", ephemeral=True)
            return

        if format == "sqlite" or format is None:
            path = f"{self.db_handler.root_dir}{ctx.guild_id}.db"
            file = discord.File(fp=path, filename="data.db")
        else:
            pd_data = self.db_handler.get_pandas_data(ctx.guild_id)
            buffer = BytesIO()
            pd_data.to_csv(buffer, index=False)
            buffer.seek(0)
            file = discord.File(fp=buffer, filename="data.csv")

        await ctx.respond(
            content=f"{lines} entries",
            file=file,
            ephemeral=True
        )

    @slash_command(description="Get the last n rows of data")
    async def last(
        self, ctx: ApplicationContext,
        count: Option(int, description="Number of entries to return",
                      min_value=1, max_value=20, default=1)
    ):
        """Prints the last `n` pieces of data to discord, with option to delete"""
        logging.debug("Getting last %s rows - Invoked by %s",
                      count, ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        ids, lines = await self.db_handler.get_last(ctx.guild_id, count)
        if len(lines) == 0:
            await ctx.respond(content=":warning: No ratings found!", ephemeral=True)
        else:
            can_delete = False
            if isinstance(ctx.user, discord.Member) \
                and ctx.user.guild_permissions.manage_messages:
                can_delete = True

            lines = self._format_lines(lines)
            await ctx.respond(
                content="\n".join(lines),
                view=UndoLast(lines, ids, self.db_handler, can_delete),
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
