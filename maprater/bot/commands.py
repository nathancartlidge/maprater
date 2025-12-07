"""Implements basic bot commands"""

from datetime import datetime, timezone
from io import BytesIO
import logging
from statistics import NormalDist

import discord
from discord import app_commands
from discord.interactions import Interaction
import numpy as np
from discord.ext import commands

from maprater.data.constants import (
    FIRE_RANKINGS,
    DEFAULT_SEASON,
    MAP_TYPES,
    MAPS,
    MapType,
    RESULTS_EMOJI,
    Seasons,
)
from maprater.bot.embed_handler import BUTTON_MAPS, PlotButtons, UndoLast
from maprater.data.db_handler import DatabaseHandler


class BaseCommands(commands.Cog):
    """Basic commands used for bot"""

    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler

    @app_commands.command(name="make_buttons", description="Create rating buttons")
    async def make_buttons(self, interaction: Interaction):
        """
        Create map-rating buttons.
        Note that this will only work once per channel?
        """
        if interaction.guild_id is None:
            await interaction.response.send_message(
                ":warning: This bot does not support DMs"
            )
            return

        logging.info("Created buttons - Invoked by %s", interaction.user)
        for map_types, cls in BUTTON_MAPS.items():
            await interaction.response.send_message(
                content=f"### {map_types}", view=cls(self.db_handler)
            )

        await interaction.followup.send(
            content="### Plot Commands", view=PlotButtons(self.db_handler)
        )

    @app_commands.command(name="data", description="Get raw data")
    @app_commands.describe(data_format="Output Data Format")
    @app_commands.choices(
        data_format=[
            app_commands.Choice(name="sqlite", value="sqlite"),
            app_commands.Choice(name="csv", value="csv"),
        ]
    )
    async def data(
        self,
        interaction: Interaction,
        data_format: str,
    ):
        """Extracts raw data from the bot"""
        logging.info("Getting Raw Data - Invoked by %s", interaction.user)
        if interaction.guild_id is None:
            await interaction.response.send_message(
                ":warning: This bot does not support DMs"
            )
            return

        lines = await self.db_handler.get_line_count(interaction.guild_id)

        if lines < 1:
            await interaction.response.send_message(
                content=":warning: No ratings found!", ephemeral=True
            )
            return

        if data_format == "sqlite" or data_format is None:
            path = self.db_handler.get_db_name(interaction.guild_id)
            file = discord.File(fp=path, filename="data.db")
        else:
            pd_data = self.db_handler.get_pandas_data(interaction.guild_id)
            buffer = BytesIO()
            pd_data.to_csv(buffer, index=False)
            buffer.seek(0)
            file = discord.File(fp=buffer, filename="data.csv")

        await interaction.response.send_message(
            content=f"{lines} entries", file=file, ephemeral=True
        )

    @app_commands.command(name="last", description="Get the last n rows of data")
    @app_commands.describe(
        count="Number of entries to return",
        user="Limit to a particular person",
        map_type="Limit to a particular map type",
    )
    @app_commands.choices(
        map_type=[app_commands.Choice(name=mt, value=mt) for mt in MAP_TYPES]
    )
    async def last(
        self,
        interaction: Interaction,
        count: app_commands.Range[int, 1, 100] = 1,
        user: discord.Member | None = None,
        map_type: str | None = None,
    ):
        """Prints the last `n` pieces of data to discord, with option to delete"""
        logging.info("Getting last %s rows - Invoked by %s", count, interaction.user)
        if interaction.guild_id is None:
            await interaction.response.send_message(
                ":warning: This bot does not support DMs"
            )
            return

        username = str(user.name) if user is not None else None

        if map_type is not None:
            # todo: proper map type in database so we don't need to do this
            ids, lines = await self.db_handler.get_last(
                interaction.guild_id, 100, username
            )
        else:
            ids, lines = await self.db_handler.get_last(
                interaction.guild_id, count, username
            )

        # filter map names
        if map_type is not None:
            valid_maps = MAPS[MapType[map_type.upper()]]
            ids = [i for i, l in zip(ids, lines) if l[1] in valid_maps]
            lines = [l for l in lines if l[1] in valid_maps]
            lines = lines[:count]

        if len(lines) == 0:
            await interaction.response.send_message(
                content=":warning: No ratings found!", ephemeral=True
            )
        else:
            can_delete = False
            if (
                isinstance(interaction.user, discord.Member)
                and interaction.user.guild_permissions.manage_messages
                and len(lines) <= 10
            ):
                can_delete = True

            lines = self._format_lines(lines, skip_username=username is not None)
            length = len("\n".join(lines))

            if length >= 2000:
                block = ""
                index = 0
                while index < len(lines) and len(block + "\n" + lines[index]) < 2000:
                    block += "\n" + lines[index]
                    index += 1

                await interaction.response.send_message(content=block, ephemeral=True)

                while index < len(lines):
                    block = "*(continued)*\n"
                    while (
                        index < len(lines) and len(block + "\n" + lines[index]) < 2000
                    ):
                        block += "\n" + lines[index]
                        index += 1

                    await interaction.followup.send(content=block, ephemeral=True)

                return

            elif can_delete:
                # only short responses will need the delete button
                await interaction.response.send_message(
                    content="\n".join(lines),
                    view=UndoLast(lines, ids, self.db_handler, can_delete),
                    ephemeral=True,
                )

            else:
                await interaction.response.send_message(
                    content="\n".join(lines), ephemeral=True
                )

    @app_commands.command(name="today", description="Get a summary of your play today")
    @app_commands.describe(user="Get someone else's stats")
    async def today(
        self,
        interaction: Interaction,
        user: discord.Member | None = None,
    ):
        """Get the last few samples for this user to discord, with an option to delete"""
        logging.info("Getting session - Invoked by %s", interaction.user)
        if interaction.guild_id is None:
            await interaction.response.send_message(
                ":warning: This bot does not support DMs"
            )
            return

        if user is None:
            user = interaction.user

        ids, lines = await self.db_handler.get_last(interaction.guild_id, 25, user.name)
        min_time = (
            datetime.now(tz=timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )
        lines = [l for l in lines if l[3] >= min_time]

        if len(lines) == 0:
            await interaction.response.send_message(
                content=":warning: No ratings found today!", ephemeral=True
            )
        else:
            games_summary = self._format_lines(lines, skip_username=True)
            wins = sum([r == "win" for (_, _, r, _) in lines])
            losses = sum([r == "loss" for (_, _, r, _) in lines])
            games = len(lines)
            emoji = (
                "🥰"
                if wins - losses > 5
                else "🥳"
                if wins > losses
                else "🥲"
                if losses - wins < 2
                else "😭"
            )
            games_summary[0] = (
                f"### Today: {emoji}\n-# Net Wins: **{wins - losses:+}** / Winrate: **{100 * wins / games:.0f}%** (played **{games}**, won **{wins}**)"
            )

            await interaction.response.send_message(
                content="\n".join(games_summary), ephemeral=True
            )

    @app_commands.command(
        name="anti_rein",
        description="How does your map pick-rate compare to Rein maps?",
    )
    @app_commands.describe(
        user="Limit to a particular person",
        season="Overwatch Season",
    )
    async def anti_rein(
        self,
        interaction: Interaction,
        user: discord.Member | None = None,
        season: Seasons = DEFAULT_SEASON,
    ):
        """Prints the last `n` pieces of data to discord, with option to delete"""
        logging.info("Getting anti-rein - Invoked by %s", interaction.user)
        await interaction.response.defer(ephemeral=True)

        if interaction.guild_id is None:
            await interaction.followup.send(":warning: This bot does not support DMs")
            return

        data = self.db_handler.get_pandas_data(interaction.guild_id, season.value)
        if user is not None:
            data = data[data.author == user.name]

        if data.shape[0] == 0:
            await interaction.followup.send(
                content=":warning: No matching data found - Cannot create graphs",
                ephemeral=True,
            )
            raise ValueError("No data available")

        desc = {"Bad": -1, "Okay": 0, "Good": 2}
        all_rankings = [desc[r] for r in FIRE_RANKINGS.values()]
        expected_quality = sum(all_rankings) / len(all_rankings)
        actual_quality = (
            sum([desc[FIRE_RANKINGS[r["map"]]] for _, r in data.iterrows()])
            / data.shape[0]
        )

        # simulate it!
        scores = np.random.choice(all_rankings, size=(50_000, data.shape[0])).mean(
            axis=1
        )
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

        await interaction.followup.send(
            content=f"The Overwatch team {opinion} Reinhardt! (p={2 * (1 - NormalDist().cdf(abs(z_score))):.2f})"
            f"\n-# (assuming a uniform distribution for map selection as the baseline)"
            f"\n> Expected Quality: **{expected_quality:.2f}** *(n={data.shape[0]}, σ={scores.std():.3f})*"
            f"\n> Actual Quality: **{actual_quality:.2f}**"
            f"\n> Z-score: **{z_score:.2f}**",
            ephemeral=True,
        )

    def _format_lines(self, lines: list, skip_username: bool = False):
        """convert lines into pretty strings"""
        output = []
        if skip_username:
            output.append(f"Data for user `{lines[0][0]}`:")
        for username, map_name, result, datetime in lines:
            result_string = RESULTS_EMOJI[result]

            if skip_username:
                output.append(f"{result_string} on *{map_name}* (<t:{datetime}:R>)")
            else:
                output.append(
                    f"`{username}`: {result_string} on *{map_name}* (<t:{datetime}:R>)"
                )

        return output
