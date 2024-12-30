"""Provides all plotting functionality"""

import logging
from io import BytesIO

import discord
import matplotlib as mpl
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.ext import commands
from matplotlib.ticker import MaxNLocator

from constants import FIRE_RANKINGS, DEFAULT_SEASON, MAPS_LIST, OW2_MAPS, Seasons, SEASONS
from db_handler import DatabaseHandler

mpl.use("agg")  # force non-interactive backend
mpl.rcParams['axes.xmargin'] = 0 # tight x axes
# hide top/right spines
mpl.rcParams['axes.spines.right'] = False
mpl.rcParams['axes.spines.top'] = False

class PlotCommands(commands.Cog):
    """Commands related to plotting data"""
    def __init__(self, db_handler: DatabaseHandler) -> None:
        super().__init__()
        self.db_handler = db_handler

    async def get_pandas(self, ctx: ApplicationContext, user: discord.Member | None = None, season: int | None = None):
        # get data for this user
        logging.info("fetching data")
        data = self.db_handler.get_pandas_data(ctx.guild_id, season=season)
        if user is not None:
            data = data[data.author == user.name]

        if data.shape[0] == 0:
            await ctx.respond(
                content=":warning: No matching data found - Cannot create graphs",
                ephemeral=True
            )
            raise ValueError("No data available")
        return data

    @slash_command(description="Winrate over time")
    async def winrate(self, ctx: ApplicationContext,
                      user: Option(discord.Member, description="Limit data to a particular person", required=True),
                      window_size: Option(int, description="Window size", default=20, min_value=1, max_value=100),
                      season: Option(Seasons, description="Overwatch Season", default=DEFAULT_SEASON)):
        # support both forms of ctx
        await ctx.defer(ephemeral=True)

        # make the plot
        data = await self.get_pandas(ctx, user, season.value)
        buffer = self.get_winrate_figure(data, window_size)

        logging.info("sending image")
        await ctx.respond(
            content=f"Rolling winrate for `{user.name}` (n={window_size})",
            files=[discord.File(fp=buffer, filename="winrate.png")],
            ephemeral=True
        )

    def get_winrate_figure(self, data, window_size):
        """rolling winrate history"""
        logging.info("calculating winrate")
        winloss_score = data["winloss"].replace({"win": 1.0, "draw": 0.5, "loss": 0.0})
        winrate = 100 * winloss_score.rolling(window=window_size, min_periods=3, center=True).mean().dropna().to_numpy()

        # make the plot
        logging.info("making plot")
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 4))

        # benchmark: 50% winrate
        ax.axhline(50, color="white", linewidth=1)

        # your current winrate
        ax.plot(winrate, color="white", linewidth=3)

        # fills for that winrate
        ax.fill_between(range(len(winrate)), winrate, 50, where=winrate <= 50, color="tab:red", interpolate=True, alpha=0.3)
        ax.fill_between(range(len(winrate)), winrate, 50, where=winrate >= 50, color="tab:green", interpolate=True, alpha=0.3)

        # axes styling
        ax.set_ylabel("Winrate (%)")
        ax.get_xaxis().set_visible(False)
        ax.spines[["bottom", "top", "right"]].set_visible(False)
        ax.set_ylim(0, 100)
        ax.set_xlim(0, len(winrate) - 1)

        logging.info("making image")
        buffer = self._export_figure(fig)

        return buffer

    @slash_command(description="Per-Map Winrate")
    async def map_winrate(self, ctx: ApplicationContext,
                          user: Option(discord.Member, description="Limit data to a particular person", default=None),
                          rein_colours: Option(bool, description="Colour by map quality for Reinhardt", default=False),
                          season: Option(Seasons, description="Overwatch Season", default=DEFAULT_SEASON)):
        # support both forms of ctx
        await ctx.defer(ephemeral=True)

        data = await self.get_pandas(ctx, user, season.value)
        buffer = self.get_map_winrate_figure(data, rein_colours=rein_colours)

        logging.info("sending image")
        await ctx.respond(            content=f"Normalised Per-Map Winrate for `{user.name}`" if user is not None else "Normalised Per-Map Winrate",
            files=[discord.File(fp=buffer, filename="map_winrate.png")],
            ephemeral=True
        )

    @slash_command(description="Per-Map Play Count")
    async def map_play_count(self, ctx: ApplicationContext,
                             user: Option(discord.Member, description="Limit to a particular person", default=None),
                             win_loss: Option(bool, description="Cumulative wins and losses per-map", default=False),
                             rein_colours: Option(bool, description="Colour by map quality for Reinhardt",
                                                  default=False),
                             season: Option(Seasons, description="Overwatch Season", default=DEFAULT_SEASON)):
        # support both forms of ctx
        await ctx.defer(ephemeral=True)

        data = await self.get_pandas(ctx, user, season.value)
        buffer = self.get_map_winrate_figure(data, count_only=True, win_loss=win_loss, rein_colours=rein_colours)

        logging.info("sending image")
        await ctx.respond(            content=("Per-Map " + "Net Wins" if win_loss else "Play Count") + f" for `{user.name}`" if user is not None else "",
            files=[discord.File(fp=buffer, filename="map_count.png")],
            ephemeral=True
        )

    @slash_command(description="Cumulative Wins")
    async def relative_rank(self, ctx: ApplicationContext,
                            user: Option(discord.Member, description="Limit to a particular person"),
                            real_dates: Option(bool, description="Use real dates", default=False),
                            season: Option(Seasons, description="Overwatch Season", default=DEFAULT_SEASON)):
        # support both forms of ctx
        await ctx.defer(ephemeral=True)

        data = await self.get_pandas(ctx, user, season.value)

        # make the plot
        data["winloss-net"] = data["winloss"].replace({"win": 1.0, "draw": 0.0, "loss": -1.0})
        data["cumulative"] = data["winloss-net"].cumsum()

        logging.info("making plot")
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 4))

        if real_dates:
            sns.lineplot(x=data["time"], y=data["cumulative"], drawstyle='steps-mid', ax=ax, linewidth=2)
            ax.xaxis.set_major_formatter(mdates.ConciseDateFormatter(ax.xaxis.get_major_locator()))
            # todo: show a line for each of the seasons?

            if season is Seasons.All:
                for season in Seasons:
                    if season is Seasons.All:
                        continue

                    index = data[data["time"] < SEASONS[season.value]].shape
                    if index:
                        value = mdates.date2num(np.datetime64(SEASONS[season.value]))
                        ax.axvline(value, color="white", linewidth=1, zorder=0)
        else:
            # add an extra point at t=-1 for clarity
            data = pd.concat([
                pd.DataFrame(index=[-1], data={"cumulative": 0}),
                data,
                pd.DataFrame(index=[9999], data={"cumulative": data["cumulative"].iloc[-1]})
            ], ignore_index=True).reset_index(drop=True)
            sns.lineplot(x=data.index, y=data["cumulative"], drawstyle='steps-post', ax=ax, linewidth=2)
            ax.xaxis.set_major_locator(MaxNLocator(integer=True))
            x_min, x_max = ax.get_xlim()
            ax.set_xlim(x_min, x_max - 0.5)
            ax.grid(axis="x", color="white", alpha=0.5)

            if season is Seasons.All:
                for season in Seasons:
                    if season is Seasons.All:
                        continue

                    index = data[data["time"] < SEASONS[season.value]].shape[0]
                    if index:
                        ax.axvline(index + 0.5, color="white", linewidth=1, zorder=0)

        ax.axhline(0, color="white", linewidth=1, zorder=0, linestyle="dashed")
        ax.axhline(data["cumulative"].min(), color="tab:red", linewidth=1, zorder=0, linestyle="dashed", label="Min")
        ax.axhline(data["cumulative"].max(), color="tab:green", linewidth=1, zorder=0, linestyle="dashed", label="Max")
        ax.axhline(data["cumulative"].mean(), color="tab:pink", linewidth=1, zorder=0, linestyle="dashdot",
                   label="Mean")
        ax.axhline(data["cumulative"].median(), color="tab:olive", linewidth=1, zorder=0, linestyle="dashdot",
                   label="Median")

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
        await ctx.respond(            content="Relative Rank" + f" for `{user.name}`" if user is not None else "",
            files=[discord.File(fp=buffer, filename="map_count.png")],
            ephemeral=True
        )

    @slash_command(description="Win streaks")
    async def streak(self, ctx: ApplicationContext,
                     user: Option(discord.Member, description="Limit to a particular person"),
                     keep_aspect: Option(bool, description="Maintain aspect ratio in plot", default=True),
                     season: Option(Seasons, description="Overwatch Season", default=DEFAULT_SEASON)):
        # support both forms of ctx
        await ctx.defer(ephemeral=True)

        data = await self.get_pandas(ctx, user, season.value)

        # slightly fancy algorithm to make the shape: we want triangles not lines!
        i = 0
        streak_counter = 0
        data_x, data_y = [], []
        for _, row in data.iterrows():
            if row.winloss == "win":
                if streak_counter > 0:
                    streak_counter += 1
                else:
                    data_x.append(i)
                    data_y.append(0)
                    streak_counter = 1
            elif row.winloss == "loss":
                if streak_counter < 0:
                    streak_counter -= 1
                else:
                    data_x.append(i)
                    data_y.append(0)
                    streak_counter = -1
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
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 4))

        ax.plot(data_x, data_y, color="white")
        ax.fill_between(data_x, data_y, 0, where=data_y >= 0, color="tab:green", alpha=0.3)
        ax.fill_between(data_x, data_y, 0, where=data_y <= 0, color="tab:red", alpha=0.3)
        ax.axhline(0, color="white", linewidth=1.5, zorder=2)
        ax.axhline(best_streak, color="tab:green", linestyle="dashed", linewidth=1, zorder=-1)
        ax.axhline(worst_streak, color="tab:red", linestyle="dashed", linewidth=1, zorder=-1)

        ax.set_ylabel("Streak")

        ax.autoscale(enable=True, axis='x', tight=True)
        y_min, y_max = ax.get_ylim()
        y_abs = max(abs(y_min), abs(y_max))
        ax.set_ylim(-y_abs, y_abs)

        if keep_aspect:
            ax.axis("equal")

        buffer = self._export_figure(fig)
        logging.info("sending image")

        await ctx.respond(            content=f"Win-streak for `{user.name}`\n"
                    f"-# 🏆 Longest win streak: **{best_streak} games**\n"
                    f"-# ❌ Longest loss streak: **{abs(worst_streak)} games**",
            files=[discord.File(fp=buffer, filename="streak.png")],
            ephemeral=True
        )

    def get_map_winrate_figure(self, data, count_only: bool = False, win_loss: bool = False, rein_colours: bool = False):
        """per-map winrate plot"""
        logging.info("calculating winrate")
        data["winloss-score"] = data["winloss"].replace({"win": 1.0, "draw": 0.5, "loss": 0.0})
        data["winloss-net"] = data["winloss"].replace({"win": 1.0, "draw": 0.0, "loss": -1.0})

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

        palette = {"OW1": "#991a5b", "OW2": "#f26f4c", "Bad": "tab:red", "Okay": "tab:orange", "Good": "tab:green"}

        logging.info("making plot")
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(12, 4))

        if count_only:
            sns.barplot(x=maps.index, y=maps.values, hue=rein_score if rein_colours else game, palette=palette,
                        dodge=False, ax=ax)
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
            sns.barplot(x=maps.index, y=100 * maps.values, hue=game, palette={"OW1": "#991a5b", "OW2": "#f26f4c"},
                        dodge=False, ax=ax)
            ax.set_ylim(0, 100)
            ax.set_ylabel("Winrate (%)")

        ax.set_xlabel("Map")
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", va="center", rotation_mode="anchor")

        logging.info("making image")
        buffer = self._export_figure(fig)
        return buffer

    # todo: write plotting functions for winstreak, global winrate, map winrate
    # @slash_command(description="Plot the current data")
    # async def plot(self, ctx: ApplicationContext,
    #                mode: Option(str, description="What plotting mode should be used?",
    #                             required=True,
    #                             choices=["normalise", "winloss", "maptype",
    #                                      "maptype_role", "role", "average",
    #                                      "count", "distribution"]),
    #                user: Option(discord.Member, description="Limit data to a particular person",
    #                             required=False, default=None)):
    #     """Creates a plot of the current rating set"""
    #     logging.info("Creating Plot (%s/%s) - Invoked by %s", mode, user, ctx.author)
    #     if ctx.guild_id is None:
    #         await ctx.respond(":warning: This bot does not support DMs")
    #         return
    #
    #     data = self.db_handler.get_pandas_data(ctx.guild_id)
    #
    #     if user is not None:
    #         # filter data to the user specified
    #         data = data[data.author == str(user)]
    #     else:
    #         if mode == "distribution":
    #             mode = "distribution_all"
    #
    #
    #     if (lines := data.shape[0]) < 1:
    #         await ctx.respond(
    #             content=":warning: No matching data found - Cannot create graphs",
    #             ephemeral=True
    #         )
    #         return
    #
    #     await ctx.defer(ephemeral=True)
    #
    #     try:
    #         aggregate = self._process_data(data, mode)
    #         figure = self._plot_data(aggregate, mode)
    #         buffer = self._export_figure(figure)
    #     except:
    #         await ctx.respond(
    #             content=":warning: Error occured while making graph",
    #             ephemeral=True
    #         )
    #         raise
    #
    #     await ctx.respond(
    #         content=f"Results plot for {lines} entries\n*{PLOT_DESCRIPTION[mode]}*",
    #         files=[discord.File(fp=buffer, filename="graph.png")],
    #         ephemeral=True
    #     )
    #
    #     del buffer, figure, aggregate
    #
    # def _process_data(self, data: pd.DataFrame, mode: Optional[str] = None,
    #                   draw_is_loss: bool = False):
    #     """Converts raw Dataframe to Pandas group-by format"""
    #
    #     data["winloss"] = data["winloss"].replace(
    #         to_replace=["win", "draw", "loss"],
    #         value=["Win", "Loss" if draw_is_loss else "Win", "Loss"]
    #     )
    #     data["role"] = data["role"].replace(to_replace=["t", "d", "s"],
    #                                         value=["Tank", "Damage", "Support"])
    #     data["map_type"] = [MAP_TYPES[map] for map in data["map"]]
    #
    #     if mode in ("distribution", "distribution_all"):
    #         return data  # No processing needed - not split by map
    #
    #     if mode == "average":
    #         grouped = data.groupby(["map"])["sentiment"]
    #     elif mode == "maptype":
    #         grouped = data.groupby(["map_type", "winloss"])["sentiment"]
    #     elif mode == "maptype_role":
    #         grouped = data.groupby(["map_type", "role"])["sentiment"]
    #     elif mode == "role":
    #         grouped = data.groupby(["map", "role"])["sentiment"]
    #     else:
    #         grouped = data.groupby(["map", "winloss"])["sentiment"]
    #
    #     if mode == "normalise" or mode is None:
    #         agg = grouped.mean()
    #         agg = agg.unstack()
    #         agg = agg.mean(axis=1)
    #     elif mode in ("winloss", "average", "maptype", "maptype_role", "role"):
    #         agg = grouped.mean()
    #     elif mode == "count":
    #         agg = grouped.count()
    #         agg = agg.fillna(0)
    #     else:
    #         raise ValueError("Incorrect mode")
    #
    #     agg = agg.sort_values()
    #     agg = agg.reset_index()
    #     return agg
    #
    # @staticmethod
    # def _plot_data(agg, mode=None):
    #     """Converts pandas groupby to matplolib plot image buffer"""
    #     # The closest-matching theme for Discord (assuming dark mode)
    #     mpl.style.use("dark_background")
    #
    #     if mode == "maptype":
    #         fig, ax = plt.subplots(figsize=(8, 6))
    #     else:
    #         fig, ax = plt.subplots(figsize=(12, 6))
    #
    #     if mode == "normalise" or mode is None:
    #         sns.barplot(
    #             data=agg,
    #             x="map",
    #             y=0,
    #             ax=ax,
    #             palette="flare_r"
    #         )
    #     elif mode == "winloss":
    #         sns.barplot(
    #             data=agg,
    #             x="map",
    #             y="sentiment",
    #             ax=ax,
    #             hue="winloss",
    #             palette=WINLOSS_PALETTE
    #         )
    #     elif mode == "average":
    #         sns.barplot(
    #             data=agg,
    #             x="map",
    #             y="sentiment",
    #             ax=ax,
    #             palette="flare_r"
    #         )
    #     elif mode == "maptype":
    #         sns.barplot(
    #             data=agg,
    #             x="map_type",
    #             y="sentiment",
    #             ax=ax,
    #             hue="winloss",
    #             palette=WINLOSS_PALETTE
    #         )
    #     elif mode == "role":
    #         sns.barplot(
    #             data=agg,
    #             x="map",
    #             y="sentiment",
    #             ax=ax,
    #             hue="role",
    #             palette=ROLE_PALETTE
    #         )
    #     elif mode == "maptype_role":
    #         sns.barplot(
    #             data=agg,
    #             x="map_type",
    #             y="sentiment",
    #             ax=ax,
    #             hue="role",
    #             palette=ROLE_PALETTE
    #         )
    #     elif mode == "count":
    #         sns.barplot(
    #             data=agg,
    #             x="map",
    #             y="sentiment",
    #             ax=ax,
    #             hue="winloss",
    #             palette=WINLOSS_PALETTE,
    #         )
    #         ax.set_ylabel("Count")
    #     elif mode == "distribution":
    #         sns.kdeplot(
    #             data=agg,
    #             x="sentiment",
    #             ax=ax,
    #             hue="winloss",
    #             palette=WINLOSS_PALETTE,
    #             fill=True,
    #             bw_adjust=1.25
    #         )
    #     elif mode == "distribution_all":
    #         sns.kdeplot(
    #             data=agg,
    #             x="sentiment",
    #             ax=ax,
    #             hue="author",
    #             fill=True,
    #             bw_adjust=1
    #         )
    #     else:
    #         raise ValueError("Incorrect mode")
    #
    #     if mode in ("distribution", "distribution_all"):
    #         ax.set_xlim(-1, 7)
    #         ax.set_xlabel("Quality")
    #     elif mode != "count":
    #         ax.set_ylim(bottom=0, top=6)
    #         ax.set_ylabel("Quality")
    #
    #     if mode in ("winloss", "maptype", "count", "distribution",
    #                 "distribution_all", "role", "maptype_role"):
    #         legend = ax.get_legend()
    #         if legend is not None:
    #             if mode == "distribution_all":
    #                 legend.set_title("Author")
    #             elif mode in ("role", "maptype_role"):
    #                 legend.set_title("Role")
    #             else:
    #                 legend.set_title("Win / Loss")
    #             legend.get_frame().set_alpha(0)
    #
    #     sns.despine(ax=ax)
    #
    #     if mode not in ("distribution", "distribution_all"):
    #         ax.tick_params(axis='x', rotation=45)
    #         if mode in ("maptype", "maptype_role"):
    #             ax.set_xlabel("Map Type")
    #         else:
    #             ax.set_xlabel("Map")
    #
    #     return fig

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
