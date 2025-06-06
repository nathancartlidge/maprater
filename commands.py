"""Implements basic bot commands"""
import time
from datetime import datetime
from io import BytesIO
import logging
from zoneinfo import ZoneInfo
from statistics import NormalDist

import discord
import numpy as np
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.ext import commands

from constants import FIRE_RANKINGS, DEFAULT_SEASON, MAP_TYPES, MAPS, MapType, RESULTS_EMOJI, Seasons
from embed_handler import BUTTON_MAPS, PlotButtons, UndoLast
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
            await ctx.respond(content=f"### {map_types}", view=cls(self.db_handler))

        await ctx.respond(content=f"### Plot Commands", view=PlotButtons(self.db_handler))

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
            path = self.db_handler.get_db_name(ctx.guild_id)
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
        count: Option(int, description="Number of entries to return", min_value=1, default=1, max_value=100,
                      required=True),
        user: Option(discord.Member, description="Limit to a particular person", required=False, default=None),
        map_type: Option(str, description="Limit to a particular map type", choices=MAP_TYPES, required=False,
                         default=None)
    ):
        """Prints the last `n` pieces of data to discord, with option to delete"""
        logging.info("Getting last %s rows - Invoked by %s", count, ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        username = str(user.name) if user is not None else None

        if map_type is not None:
            # todo: proper map type in database so we don't need to do this
            ids, lines = await self.db_handler.get_last(ctx.guild_id, 100, username)
        else:
            ids, lines = await self.db_handler.get_last(ctx.guild_id, count, username)

        # filter map names
        if map_type is not None:
            valid_maps = MAPS[MapType[map_type.upper()]]
            ids = [i for i, l in zip(ids, lines) if l[1] in valid_maps]
            lines = [l for l in lines if l[1] in valid_maps]
            lines = lines[:count]

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

    @slash_command(description="Get a summary of your play today")
    async def today(self, ctx: ApplicationContext,
                    user: Option(discord.Member, description="Get someone else's stats", required=False, default=None)):
        """Get the last few samples for this user to discord, with option to delete"""
        logging.info("Getting session - Invoked by %s", ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        if user is None:
            user = ctx.user

        ids, lines = await self.db_handler.get_last(ctx.guild_id, 25, user.name)
        min_time = datetime.now(tz=ZoneInfo("localtime")).replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        lines = [l for l in lines if l[3] >= min_time]

        if len(lines) == 0:
            await ctx.respond(content=":warning: No ratings found today!", ephemeral=True)
        else:
            games_summary = self._format_lines(lines, skip_username=True)
            wins = sum([r == "win" for (_, _, r, _) in lines])
            losses = sum([r == "loss" for (_, _, r, _) in lines])
            games = len(lines)
            emoji = '🥰' if wins - losses > 5 else '🥳' if wins > losses else '🥲' if losses - wins < 2 else '😭'
            games_summary[0] = f"### Today: {emoji}\n-# Net Wins: **{wins - losses:+}** / Winrate: **{100 * wins / games:.0f}%** (played **{games}**, won **{wins}**)"

            await ctx.respond(
                content="\n".join(games_summary),
                ephemeral=True
            )

    @slash_command(description="How does your map pick-rate compare to Rein maps?")
    async def anti_rein(self, ctx: ApplicationContext,
                        user: Option(discord.Member, description="Limit to a particular person", default=None),
                        season: Option(Seasons, description="Overwatch Season", default=DEFAULT_SEASON)):
        """Prints the last `n` pieces of data to discord, with option to delete"""
        logging.info("Getting anti-rein - Invoked by %s", ctx.author)
        await ctx.defer(ephemeral=True)

        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        data = self.db_handler.get_pandas_data(ctx.guild_id, season.value)
        if user is not None:
            data = data[data.author == user.name]

        if data.shape[0] == 0:
            await ctx.respond(
                content=":warning: No matching data found - Cannot create graphs",
                ephemeral=True
            )
            raise ValueError("No data available")

        desc = {"Bad": -1, "Okay": 0, "Good": 2}
        all_rankings = [desc[r] for r in FIRE_RANKINGS.values()]
        expected_quality = sum(all_rankings) / len(all_rankings)
        actual_quality = sum([desc[FIRE_RANKINGS[r["map"]]] for _, r in data.iterrows()]) / data.shape[0]

        # simulate it!
        scores = np.random.choice(all_rankings, size=(50_000, data.shape[0])).mean(axis=1)
        scores.sort()

        z_score = (actual_quality - expected_quality) / scores.std()

        if z_score < -2:
            opinion = "**hates**"
        elif z_score < -1:
            opinion = "_might_ dislike"
        elif z_score < 1:
            opinion = "is _probably_ neutral about"
        elif z_score < 2:
            opinion = "_might_ like"
        else:
            opinion = "**loves**"

        await ctx.respond(
            content=f"The Overwatch team {opinion} Reinhardt! (p={2 * (1 - NormalDist().cdf(abs(z_score))):.2f})"
                    f"\n-# (assuming a uniform distribution for map selection as the baseline)"
                    f"\n> Expected Quality: **{expected_quality:.2f}** *(n={data.shape[0]}, σ={scores.std():.3f})*"
                    f"\n> Actual Quality: **{actual_quality:.2f}**"
                    f"\n> Z-score: **{z_score:.2f}**",
            ephemeral=True
        )

    def _format_lines(self, lines: list, skip_username: bool = False):
        """convert lines into pretty strings"""
        output = []
        if skip_username:
            output.append(f"Data for user `{lines[0][0]}`:")
        for (username, map_name, result, datetime) in lines:
            result_string = RESULTS_EMOJI[result]

            if skip_username:
                output.append(f"{result_string} on *{map_name}* (<t:{datetime}:R>)")
            else:
                output.append(f"`{username}`: {result_string} on *{map_name}* (<t:{datetime}:R>)")

        return output
