"""Implements basic bot commands"""

from io import BytesIO
import logging

import discord
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.ext import commands
import pandas as pd

from embed_handler import BUTTON_MAPS, MapType, MapButtons, UndoLast
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
        for map_types, cls in BUTTON_MAPS.items():
            await ctx.respond(content=f"## {map_types}", view=cls(self.db_handler))

    @slash_command(description="Get raw data")
    async def data(self, ctx: ApplicationContext,
                   data_format: Option(str, description="Output Data Format",
                                       required=True, choices=["sqlite", "csv"])):
        """Extracts raw data from the bot"""
        logging.info("Getting Raw Data - Invoked by %s", ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        lines = await self.db_handler.get_line_count(ctx.guild_id)

        if lines < 1:
            await ctx.respond(content=":warning: No ratings found!", ephemeral=True)
            return

        if data_format == "sqlite" or data_format is None:
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

    @slash_command(description="Describe dataset (summary statistics)")
    async def describe(self, ctx: ApplicationContext,
                       user: Option(discord.Member,
                                    description="Limit data to a particular person",
                                    required=False, default=None)):
        """Prints a text description of the data"""
        logging.info("Describing file - invoked by %s", ctx.author)
        lines = await self.db_handler.get_line_count(ctx.guild_id)

        if lines < 1:
            await ctx.respond(content=":warning: No ratings found!", ephemeral=True)
            return

        data = self.db_handler.get_pandas_data(ctx.guild_id)

        if user is not None:
            data = data[data.author == str(user)]

        if data.shape[0] == 0:
            await ctx.respond(content=":warning: No ratings found for that user!", ephemeral=True)
            return

        data.replace(to_replace={"l": "Loss", "w": "Win", "x": "Draw"}, inplace=True)

        def _process(data: pd.DataFrame, column: pd.Series):
            grouped = data.groupby([column]).describe()["sentiment"]
            grouped = grouped[["count", "mean", "std"]]
            grouped["count"] = grouped["count"].astype(int)
            grouped.index.rename("result", inplace=True)
            grouped.rename(columns={"count": "count", "mean": "mean",
                                    "std": "stdev"}, inplace=True)
            grouped = grouped.round(decimals=3)
            return grouped

        def _prettytable(data: pd.Series):
            string = str(data).splitlines()
            spaces = len(string[0]) - len(string[0].lstrip(" ")) - 1
            string.insert(2, "─"*len(string[0]))
            for i, line in enumerate(string):
                char = "│" if i != 2 else "┼"
                string[i] = line[0:spaces] + char + line[spaces:]
            return "\n".join(string)

        grouped_winloss = _prettytable(_process(data, data.winloss))
        line = f"```c\n{grouped_winloss}```"
        if user is None:
            grouped_author = _prettytable(_process(data, data.author))
            line += f"```c\n{grouped_author}```"

        await ctx.respond(content=line, ephemeral=True)

    @slash_command(description="Get the last n rows of data")
    async def last(
        self, ctx: ApplicationContext,
        count: Option(int, description="Number of entries to return",
                      min_value=1, default=2, max_value=100, required=False),
        user: Option(discord.Member, description="Limit to a particular person",
                     required=False, default=None)):
        """Prints the last `n` pieces of data to discord, with option to delete"""
        logging.info("Getting last %s rows - Invoked by %s", count, ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        username = str(user.name) if user is not None else None

        ids, lines = await self.db_handler.get_last(ctx.guild_id, count, username)
        if len(lines) == 0:
            await ctx.respond(content=":warning: No ratings found!", ephemeral=True)
        else:
            can_delete = False
            if isinstance(ctx.user, discord.Member) \
                and ctx.user.guild_permissions.manage_messages \
                    and len(lines) <= 10:
                can_delete = True

            lines = self._format_lines(lines, skip_username=username is not None)
            length = len("\n".join(lines))

            if length >= 2000:
                block = ""
                index = 0
                while index < len(lines) \
                    and len(block + "\n" + lines[index]) < 2000:
                    block += "\n" + lines[index]
                    index += 1

                await ctx.respond(content=block, ephemeral=True)

                while index < len(lines):
                    block = "*(continued)*\n"
                    while index < len(lines) \
                        and len(block + "\n" + lines[index]) < 2000:
                        block += "\n" + lines[index]
                        index += 1

                    await ctx.followup.send(content=block, ephemeral=True)

                return

            elif can_delete:
                # only short responses will need the delete button
                await ctx.respond(
                    content="\n".join(lines),
                    view=UndoLast(lines, ids, self.db_handler, can_delete),
                    ephemeral=True
                )

            else:
                await ctx.respond(
                    content="\n".join(lines),
                    ephemeral=True
                )

    def _format_lines(self, lines: list, skip_username: bool = False):
        """convert lines into pretty strings"""
        output = []
        if skip_username:
            output.append(f"Data for user `{lines[0][0]}`:")
        for (username, map_name, result, datetime) in lines:
            result_string = {"win": "🏆", "loss": "❌", "draw": "🤝"}[result]

            if skip_username:
                output.append(f"{result_string} on *{map_name}* (<t:{datetime}:R>)")
            else:
                output.append(f"`{username}`: {result_string} on *{map_name}* (<t:{datetime}:R>)")

        return output
