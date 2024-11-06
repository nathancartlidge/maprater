"""Provides all plotting functionality"""

from io import BytesIO
import logging

import discord
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from discord import ApplicationContext
from discord.ext import commands
from discord.commands import Option, slash_command

from db_handler import DatabaseHandler
from constants import MAPS, OW2_MAPS

mpl.use("agg")  # force non-interactive backend

class PlotCommands(commands.Cog):
    """Commands related to plotting data"""
    def __init__(self, db_handler: DatabaseHandler) -> None:
        super().__init__()
        self.db_handler = db_handler

    @slash_command(description="Win/Loss Streak")
    async def winrate(self, ctx: ApplicationContext,
                      user: Option(discord.Member, description="Limit data to a particular person", required=True),
                      window_size: Option(int, description="Window size", default=20, min_value=1, max_value=100)):
        # get data for this user
        logging.info("fetching data")
        data = self.db_handler.get_pandas_data(ctx.guild_id)
        data = data[data.author == user.name]

        if data.shape[0] == 0:
            await ctx.respond(
                content=":warning: No matching data found - Cannot create graphs",
                ephemeral=True
            )

        # make the plot
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
        fig, ax = plt.subplots(figsize=(10, 4))

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
    async def map_winrate(self,
                          ctx: ApplicationContext,
                          user: Option(discord.Member, description="Limit data to a particular person", default=None)):
        # get data for this user
        logging.info("fetching data")
        data = self.db_handler.get_pandas_data(ctx.guild_id)
        if user is not None:
            data = data[data.author == user.name]

        if data.shape[0] == 0:
            await ctx.respond(
                content=":warning: No matching data found - Cannot create graphs",
                ephemeral=True
            )

        # make the plot
        buffer = self.get_map_winrate_figure(data)

        logging.info("sending image")
        await ctx.respond(
            content=f"Normalised Per-Map Winrate for `{user.name}`" if user is not None else "Normalised Per-Map Winrate",
            files=[discord.File(fp=buffer, filename="map_winrate.png")],
            ephemeral=True
        )

    @slash_command(description="Per-Map Play Count")
    async def map_play_count(self, ctx: ApplicationContext,
                             user: Option(discord.Member, description="Limit data to a particular person", default=None)):
        # get data for this user
        logging.info("fetching data")
        data = self.db_handler.get_pandas_data(ctx.guild_id)
        if user is not None:
            data = data[data.author == user.name]

        if data.shape[0] == 0:
            await ctx.respond(
                content=":warning: No matching data found - Cannot create graphs",
                ephemeral=True
            )

        # make the plot
        buffer = self.get_map_winrate_figure(data, count_only=True)

        logging.info("sending image")
        await ctx.respond(
            content=f"Per-Map Play Count for `{user.name}`" if user is not None else "Per-Map Play Count",
            files=[discord.File(fp=buffer, filename="map_count.png")],
            ephemeral=True
        )

    def get_map_winrate_figure(self, data, count_only: bool = False):
        """per-map winrate plot"""
        logging.info("calculating winrate")
        data["winloss-score"] = data["winloss"].replace({"win": 1.0, "draw": 0.5, "loss": 0.0})

        grouped = data.groupby("map")["winloss-score"]
        if count_only:
            all_maps = pd.Series(index=[map_name for map_set in MAPS.values() for map_name in map_set], data=0)
            maps = (grouped.count() + all_maps).fillna(0).sort_values()
        else:
            count = grouped.count()
            sum = grouped.sum()

            # normalisation factor: add one win and one loss to every map
            maps = ((sum + 1) / (count + 2)).sort_values()

        game = np.array(["OW2" if i in OW2_MAPS else "OW1" for i in maps.index])

        logging.info("making plot")
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 4))

        if count_only:
            sns.barplot(x=maps.index, y=maps.values, hue=game, palette={"OW1": "#991a5b", "OW2": "#f26f4c"},
                        dodge=False, ax=ax)
            ax.set_ylabel("Play Count")
        else:
            ax.axhline(50, color="white", linewidth=1, zorder=-1)
            sns.barplot(x=maps.index, y=100 * maps.values, hue=game, palette={"OW1": "#991a5b", "OW2": "#f26f4c"},
                        dodge=False, ax=ax)
            ax.set_ylim(0, 100)
            ax.set_ylabel("Winrate (%)")

        ax.set_xlabel("Map")
        ax.tick_params(axis='x', rotation=45)

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
        fig.set_dpi(400)
        fig.tight_layout()

        buffer = BytesIO()
        fig.savefig(buffer, transparent=True)
        buffer.seek(0)

        plt.close(fig)
        return buffer

# TODO: live-updating plot
