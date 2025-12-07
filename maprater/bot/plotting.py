"""Provides all plotting functionality"""

import logging
from io import BytesIO

import discord
from discord import app_commands
from discord.interactions import Interaction
import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from discord.ext import commands
from matplotlib.ticker import MaxNLocator

from maprater.data.constants import (
    FIRE_RANKINGS,
    DEFAULT_SEASON,
    MAPS_LIST,
    OW2_MAPS,
    RESULTS_SCORES,
    RESULTS_SCORES_PRIME,
    RESULTS_SCORES_PRIME_0_1,
    Seasons,
    SEASONS,
)
from maprater.data.db_handler import DatabaseHandler

mpl.use("agg")  # force non-interactive backend
mpl.rcParams["axes.xmargin"] = 0  # tight x axes
# hide top/right spines
mpl.rcParams["axes.spines.right"] = False
mpl.rcParams["axes.spines.top"] = False


class PlotCommands(commands.Cog):
    """Commands related to plotting data"""

    def __init__(self, db_handler: DatabaseHandler) -> None:
        super().__init__()
        self.db_handler = db_handler

    async def get_pandas(
        self,
        interaction: Interaction,
        user: discord.Member | None = None,
        season: int | None = None,
    ):
        # get data for this user
        logging.info("fetching data")
        data = self.db_handler.get_pandas_data(interaction.guild_id, season=season)
        if user is not None:
            data = data[data.author == user.name]

        if data.shape[0] == 0:
            await interaction.response.send_message(
                content=":warning: No matching data found - Cannot create graphs",
                ephemeral=True,
            )
            raise ValueError("No data available")
        return data

    @app_commands.command(name="winrate", description="Winrate over time")
    @app_commands.describe(
        user="Limit data to a particular person",
        window_size="Window size",
        season="Overwatch Season",
    )
    async def winrate(
        self,
        interaction: Interaction,
        user: discord.Member,
        window_size: app_commands.Range[int, 1, 100] = 20,
        season: Seasons = DEFAULT_SEASON,
    ):
        # support both forms of ctx
        await interaction.response.defer(ephemeral=True)

        # make the plot
        data = await self.get_pandas(interaction, user, season.value)
        buffer = self.get_winrate_figure(data, window_size)

        logging.info("sending image")
        await interaction.followup.send(
            content=f"Rolling winrate for `{user.name}` (n={window_size})",
            files=[discord.File(fp=buffer, filename="winrate.png")],
            ephemeral=True,
        )

    def get_winrate_figure(self, data, window_size):
        """rolling winrate history"""
        logging.info("calculating winrate")
        winloss_score = data["winloss"].replace(RESULTS_SCORES_PRIME_0_1)
        winrate = (
            100
            * winloss_score.rolling(window=window_size, min_periods=3, center=True)
            .mean()
            .dropna()
            .to_numpy()
        )

        # make the plot
        logging.info("making plot")
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(12, 4))

        # benchmark: 50% winrate
        ax.axhline(50, color="white", linewidth=1)

        # your current winrate
        ax.plot(winrate, color="white", linewidth=3)

        # fills for that winrate
        ax.fill_between(
            range(len(winrate)),
            winrate,
            50,
            where=winrate <= 50,
            color="tab:red",
            interpolate=True,
            alpha=0.3,
        )
        ax.fill_between(
            range(len(winrate)),
            winrate,
            50,
            where=winrate >= 50,
            color="tab:green",
            interpolate=True,
            alpha=0.3,
        )

        # axes styling
        ax.set_ylabel("Winrate (%)")
        ax.get_xaxis().set_visible(False)
        ax.spines[["bottom", "top", "right"]].set_visible(False)
        ax.set_ylim(0, 100)
        ax.set_xlim(0, len(winrate) - 1)

        logging.info("making image")
        buffer = self._export_figure(fig)

        return buffer

    @app_commands.command(name="map_winrate", description="Per-Map Winrate")
    @app_commands.describe(
        user="Limit data to a particular person",
        rein_colours="Colour by map quality for Reinhardt",
        season="Overwatch Season",
    )
    async def map_winrate(
        self,
        interaction: Interaction,
        user: discord.Member | None = None,
        rein_colours: bool = False,
        season: Seasons = DEFAULT_SEASON,
    ):
        # support both forms of ctx
        await interaction.response.defer(ephemeral=True)

        data = await self.get_pandas(interaction, user, season.value)
        buffer = self.get_map_winrate_figure(data, rein_colours=rein_colours)

        logging.info("sending image")
        await interaction.followup.send(
            content=f"Normalised Per-Map Winrate for `{user.name}`"
            if user is not None
            else "Normalised Per-Map Winrate",
            files=[discord.File(fp=buffer, filename="map_winrate.png")],
            ephemeral=True,
        )

    @app_commands.command(name="map_play_count", description="Per-Map Play Count")
    @app_commands.describe(
        user="Limit to a particular person",
        win_loss="Cumulative wins and losses per-map",
        rein_colours="Colour by map quality for Reinhardt",
        season="Overwatch Season",
    )
    async def map_play_count(
        self,
        interaction: Interaction,
        user: discord.Member | None = None,
        win_loss: bool = False,
        rein_colours: bool = False,
        season: Seasons = DEFAULT_SEASON,
    ):
        # support both forms of ctx
        await interaction.response.defer(ephemeral=True)

        data = await self.get_pandas(interaction, user, season.value)
        buffer = self.get_map_winrate_figure(
            data, count_only=True, win_loss=win_loss, rein_colours=rein_colours
        )

        logging.info("sending image")
        await interaction.followup.send(
            content=("Per-Map " + "Net Wins" if win_loss else "Play Count")
            + f" for `{user.name}`"
            if user is not None
            else "",
            files=[discord.File(fp=buffer, filename="map_count.png")],
            ephemeral=True,
        )

    @app_commands.command(name="relative_rank", description="Cumulative Wins")
    @app_commands.describe(
        user="Limit to a particular person",
        real_dates="Use real dates",
        season="Overwatch Season",
    )
    async def relative_rank(
        self,
        interaction: Interaction,
        user: discord.Member,
        real_dates: bool = False,
        season: Seasons = DEFAULT_SEASON,
    ):
        # support both forms of ctx
        await interaction.response.defer(ephemeral=True)

        data = await self.get_pandas(interaction, user, season.value)

        # make the plot
        data["winloss-net"] = data["winloss"].replace(RESULTS_SCORES)
        data["cumulative"] = data["winloss-net"].cumsum()

        logging.info("making plot")
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(18 if data.shape[0] > 50 else 12, 4))

        if real_dates:
            sns.lineplot(
                x=data["time"],
                y=data["cumulative"],
                drawstyle="steps-mid",
                ax=ax,
                linewidth=2,
            )
            ax.xaxis.set_major_formatter(
                mdates.ConciseDateFormatter(ax.xaxis.get_major_locator())
            )
            # todo: show a line for each of the seasons?

            if season is Seasons.All:
                self._add_season_lines(data, ax, real_dates=True)
        else:
            # add an extra point at t=-1 for clarity
            data = pd.concat(
                [
                    pd.DataFrame(index=[-1], data={"cumulative": 0}),
                    data,
                    pd.DataFrame(
                        index=[99999], data={"cumulative": data["cumulative"].iloc[-1]}
                    ),
                ],
                ignore_index=True,
            ).reset_index(drop=True)
            sns.lineplot(
                x=data.index,
                y=data["cumulative"],
                drawstyle="steps-post",
                ax=ax,
                linewidth=2,
            )
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            x_min, x_max = ax.get_xlim()
            ax.set_xlim(x_min, x_max - 0.5)
            ax.grid(axis="x", color="white", alpha=0.5)

            if season is Seasons.All:
                self._add_season_lines(data, ax)

        ax.axhline(0, color="white", linewidth=1, zorder=0, linestyle="dashed")
        ax.axhline(
            data["cumulative"].min(),
            color="tab:red",
            linewidth=1,
            zorder=0,
            linestyle="dashed",
            label="Min",
        )
        ax.axhline(
            data["cumulative"].max(),
            color="tab:green",
            linewidth=1,
            zorder=0,
            linestyle="dashed",
            label="Max",
        )
        ax.axhline(
            data["cumulative"].mean(),
            color="tab:pink",
            linewidth=1,
            zorder=0,
            linestyle="dashdot",
            label="Mean",
        )
        ax.axhline(
            data["cumulative"].median(),
            color="tab:olive",
            linewidth=1,
            zorder=0,
            linestyle="dashdot",
            label="Median",
        )

        ax.set_ylabel("Net Wins")
        legend = ax.legend()

        # fancy legend
        legend.get_frame().set_alpha(0.3)
        legend.get_frame().set_edgecolor("white")
        legend.get_frame().set_linewidth(1)
        legend.get_frame().set_boxstyle("round,pad=0.4,rounding_size=0.3")

        logging.info("making image")
        buffer = self._export_figure(fig)

        logging.info("sending image")
        await interaction.followup.send(
            content="Relative Rank" + f" for `{user.name}`" if user is not None else "",
            files=[discord.File(fp=buffer, filename="map_count.png")],
            ephemeral=True,
        )

    @app_commands.command(name="streak", description="Win streaks")
    @app_commands.describe(
        user="Limit to a particular person",
        keep_aspect="Maintain aspect ratio in plot",
        season="Overwatch Season",
    )
    async def streak(
        self,
        interaction: Interaction,
        user: discord.Member,
        keep_aspect: bool = True,
        season: Seasons = DEFAULT_SEASON,
    ):
        # support both forms of ctx
        await interaction.response.defer(ephemeral=True)

        data = await self.get_pandas(interaction, user, season.value)

        # slightly fancy algorithm to make the shape: we want triangles not lines!
        i = 0
        streak_counter = 0
        data_x, data_y = [], []
        for _, row in data.iterrows():
            if row.winloss in ("wide-win", "win"):
                if streak_counter > 0:
                    streak_counter += RESULTS_SCORES[row.winloss]
                else:
                    data_x.append(i)
                    data_y.append(0)
                    streak_counter = RESULTS_SCORES[row.winloss]
            elif row.winloss in ("wide-loss", "loss"):
                if streak_counter < 0:
                    streak_counter += RESULTS_SCORES[row.winloss]
                else:
                    data_x.append(i)
                    data_y.append(0)
                    streak_counter = RESULTS_SCORES[row.winloss]
            else:
                data_x.append(i)
                data_y.append(0)
                streak_counter = 0

            i += 1
            data_x.append(i)
            data_y.append(streak_counter)

        data_x = np.array(data_x)
        data_y = np.array(data_y)
        best_streak = data_y.max()
        worst_streak = data_y.min()

        logging.info("making plot")
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(18 if data.shape[0] > 50 else 12, 4))

        if season is Seasons.All:
            self._add_season_lines(data, ax)

        ax.plot(data_x, data_y, color="white")
        ax.fill_between(
            data_x, data_y, 0, where=data_y >= 0, color="tab:green", alpha=0.3
        )
        ax.fill_between(
            data_x, data_y, 0, where=data_y <= 0, color="tab:red", alpha=0.3
        )
        ax.axhline(0, color="white", linewidth=1.5, zorder=2)
        ax.axhline(
            best_streak, color="tab:green", linestyle="dashed", linewidth=1, zorder=-1
        )
        ax.axhline(
            worst_streak, color="tab:red", linestyle="dashed", linewidth=1, zorder=-1
        )

        ax.set_ylabel("Streak")

        # ax.autoscale(enable=True, axis='x', tight=True)
        ax.set_xlim(-1, i + 1)
        y_min, y_max = ax.get_ylim()
        y_abs = max(abs(y_min), abs(y_max))
        ax.set_ylim(-y_abs, y_abs)

        if keep_aspect:
            ax.axis("equal")

        buffer = self._export_figure(fig)
        logging.info("sending image")

        await interaction.followup.send(
            content=f"Win-streak for `{user.name}`\n"
            f"-# 🏆 Longest win streak: **{best_streak} games**\n"
            f"-# ❌ Longest loss streak: **{abs(worst_streak)} games**",
            files=[discord.File(fp=buffer, filename="streak.png")],
            ephemeral=True,
        )

    def get_map_winrate_figure(
        self,
        data,
        count_only: bool = False,
        win_loss: bool = False,
        rein_colours: bool = False,
    ):
        """per-map winrate plot"""
        logging.info("calculating winrate")
        data["winloss-score"] = data["winloss"].replace(RESULTS_SCORES_PRIME_0_1)
        data["winloss-net"] = data["winloss"].replace(RESULTS_SCORES_PRIME)

        if count_only:
            all_maps = pd.Series(index=MAPS_LIST, data=0)
            if win_loss:
                grouped = data.groupby("map")["winloss-net"]
                maps = (grouped.sum() + all_maps).fillna(0).sort_values()
            else:
                grouped = data.groupby("map")["winloss-score"]
                maps = (grouped.count() + all_maps).fillna(0).sort_values()
        else:
            grouped = data.groupby("map")["winloss-score"]
            count = grouped.count()
            sum = grouped.sum()

            # normalisation factor: add one win and one loss to every map
            maps = ((sum + 1) / (count + 2)).sort_values()

        game = np.array(["OW2" if i in OW2_MAPS else "OW1" for i in maps.index])
        rein_score = np.array([FIRE_RANKINGS[i] for i in maps.index])

        palette = {
            "OW1": "#991a5b",
            "OW2": "#f26f4c",
            "Bad": "tab:red",
            "Okay": "tab:orange",
            "Good": "tab:green",
        }

        logging.info("making plot")
        plt.style.use("dark_background")
        fig, ax = plt.subplots(figsize=(12, 4))

        if count_only:
            sns.barplot(
                x=maps.index,
                y=maps.values,
                hue=rein_score if rein_colours else game,
                palette=palette,
                dodge=False,
                ax=ax,
            )
            if win_loss:
                ax.axhline(0, color="white", linewidth=1, zorder=2)
                ax.set_ylabel("Net Wins")
                y_min, y_max = ax.get_ylim()
                y_abs = max(abs(y_min), abs(y_max))
                ax.set_ylim(-y_abs, y_abs)
            else:
                ax.set_ylabel("Play Count")
        else:
            ax.axhline(50, color="white", linewidth=1, zorder=-1)
            sns.barplot(
                x=maps.index,
                y=100 * maps.values,
                hue=game,
                palette={"OW1": "#991a5b", "OW2": "#f26f4c"},
                dodge=False,
                ax=ax,
            )
            ax.set_ylim(0, 100)
            ax.set_ylabel("Winrate (%)")

        ax.set_xlabel("Map")
        plt.setp(
            ax.get_xticklabels(),
            rotation=45,
            ha="right",
            va="center",
            rotation_mode="anchor",
        )

        logging.info("making image")
        buffer = self._export_figure(fig)
        return buffer

    @staticmethod
    def _add_season_lines(data: pd.DataFrame, ax: plt.Axes, real_dates: bool = False):
        for season in Seasons:
            if season is Seasons.All:
                continue

            else:
                index = data[data["time"] < SEASONS[season.value]].shape[0]
                if index:
                    if real_dates:
                        value = mdates.date2num(np.datetime64(SEASONS[season.value]))
                        ax.axvline(value, color="white", linewidth=1, zorder=0)
                    else:
                        ax.axvline(index + 0.5, color="white", linewidth=1, zorder=0)

    @staticmethod
    def _export_figure(fig):
        fig.set_dpi(500)
        fig.tight_layout()

        buffer = BytesIO()
        fig.savefig(buffer, transparent=True)
        buffer.seek(0)

        plt.close(fig)
        return buffer


# TODO: live-updating plot
