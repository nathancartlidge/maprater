"""Provides all plotting functionality"""

from io import BytesIO
import logging

from typing import Optional

import discord
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt

from discord import ApplicationContext
from discord.ext import commands
from discord.commands import Option, slash_command

from db_handler import DatabaseHandler

PLOT_DESCRIPTION = {
    "normalise": "Data has been normalised by winrate (equal weight to ratings" \
        + " given from losses as ratings given from wins)",
    "winloss": "Data has been separated by map and win/loss",
    "maptype": "Data has been separated by map type and win/loss",
    "maptype_role": "Data has been separated by map type and role",
    "role": "Data has been separated by map type and role, not normalised",
    "average": "Data has been separated by map, but has not been normalised",
    "count": "Data shows the number of ratings per map, separated by win/loss",
    "distribution": "Data shows KDE-smoothed plot of ranking distribution, separated by win/loss",
    "distribution_all": "Data shows KDE-smoothed plot of ranking distribution, separated by voter"
}
WINLOSS_PALETTE = {"Win": "#4bc46d", "Loss": "#c9425d"}
ROLE_PALETTE = {"Tank": "tab:orange", "Damage": "tab:blue", "Support": "tab:green"}
MAP_TYPES = {
    "Circuit": "Payload",
    "Dorado": "Payload",
    "Havana": "Payload",
    "Junkertown": "Payload",
    "Rialto": "Payload",
    "R66": "Payload",
    "WPG": "Payload",

    "Blizzard": "Hybrid",
    "Eichenwalde": "Hybrid",
    "Hollywood": "Hybrid",
    "Kings": "Hybrid",
    "Midtown": "Hybrid",
    "Paraiso": "Hybrid",

    "Busan": "Control",
    "Ilios": "Control",
    "Lijiang": "Control",
    "Nepal": "Control",
    "Oasis": "Control",

    "QueenStreet": "Push",
    "Esperanca": "Push",
    "Colosseo": "Push"
}

mpl.use("agg")  # force non-interactive backend

class PlotCommands(commands.Cog):
    """Commands related to plotting data"""
    def __init__(self, db_handler: DatabaseHandler) -> None:
        super().__init__()
        self.db_handler = db_handler

    @slash_command(description="Plot the current data")
    async def plot(self, ctx: ApplicationContext,
                   mode: Option(str, description="What plotting mode should be used?",
                                required=True,
                                choices=["normalise", "winloss", "maptype",
                                         "maptype_role", "role", "average",
                                         "count", "distribution"]),
                   user: Option(discord.Member, description="Limit data to a particular person",
                                required=False, default=None)):
        """Creates a plot of the current rating set"""
        logging.info("Creating Plot (%s/%s) - Invoked by %s", mode, user, ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        data = self.db_handler.get_pandas_data(ctx.guild_id)

        if user is not None:
            # filter data to the user specified
            data = data[data.author == str(user)]
        else:
            if mode == "distribution":
                mode = "distribution_all"


        if (lines := data.shape[0]) < 1:
            await ctx.respond(
                content=":warning: No matching data found - Cannot create graphs",
                ephemeral=True
            )
            return

        await ctx.defer(ephemeral=True)

        try:
            aggregate = self._process_data(data, mode)
            figure = self._plot_data(aggregate, mode)
            buffer = self._export_figure(figure)
        except:
            await ctx.respond(
                content=":warning: Error occured while making graph",
                ephemeral=True
            )
            raise

        await ctx.respond(
            content=f"Results plot for {lines} entries\n*{PLOT_DESCRIPTION[mode]}*",
            files=[discord.File(fp=buffer, filename="graph.png")],
            ephemeral=True
        )

        del buffer, figure, aggregate

    def _process_data(self, data: pd.DataFrame, mode: Optional[str] = None,
                      draw_is_loss: bool = False):
        """Converts raw Dataframe to Pandas group-by format"""

        data["winloss"] = data["winloss"].replace(
            to_replace=["w", "x", "l"],
            value=["Win", "Loss" if draw_is_loss else "Win", "Loss"]
        )
        data["role"] = data["role"].replace(to_replace=["t", "d", "s"],
                                            value=["Tank", "Damage", "Support"])
        data["map_type"] = [MAP_TYPES[map] for map in data["map"]]

        if mode in ("distribution", "distribution_all"):
            return data  # No processing needed - not split by map

        if mode == "average":
            grouped = data.groupby(["map"])["sentiment"]
        elif mode == "maptype":
            grouped = data.groupby(["map_type", "winloss"])["sentiment"]
        elif mode == "maptype_role":
            grouped = data.groupby(["map_type", "role"])["sentiment"]
        elif mode == "role":
            grouped = data.groupby(["map", "role"])["sentiment"]
        else:
            grouped = data.groupby(["map", "winloss"])["sentiment"]

        if mode == "normalise" or mode is None:
            agg = grouped.mean()
            agg = agg.unstack()
            agg = agg.mean(axis=1)
        elif mode in ("winloss", "average", "maptype", "maptype_role", "role"):
            agg = grouped.mean()
        elif mode == "count":
            agg = grouped.count()
            agg = agg.fillna(0)
        else:
            raise ValueError("Incorrect mode")

        agg = agg.sort_values()
        agg = agg.reset_index()
        return agg

    @staticmethod
    def _plot_data(agg, mode=None):
        """Converts pandas groupby to matplolib plot image buffer"""
        # The closest-matching theme for Discord (assuming dark mode)
        mpl.style.use("dark_background")

        if mode == "maptype":
            fig, ax = plt.subplots(figsize=(8, 6))
        else:
            fig, ax = plt.subplots(figsize=(12, 6))

        if mode == "normalise" or mode is None:
            sns.barplot(
                data=agg,
                x="map",
                y=0,
                ax=ax,
                palette="flare_r"
            )
        elif mode == "winloss":
            sns.barplot(
                data=agg,
                x="map",
                y="sentiment",
                ax=ax,
                hue="winloss",
                palette=WINLOSS_PALETTE
            )
        elif mode == "average":
            sns.barplot(
                data=agg,
                x="map",
                y="sentiment",
                ax=ax,
                palette="flare_r"
            )
        elif mode == "maptype":
            sns.barplot(
                data=agg,
                x="map_type",
                y="sentiment",
                ax=ax,
                hue="winloss",
                palette=WINLOSS_PALETTE
            )
        elif mode == "role":
            sns.barplot(
                data=agg,
                x="map",
                y="sentiment",
                ax=ax,
                hue="role",
                palette=ROLE_PALETTE
            )
        elif mode == "maptype_role":
            sns.barplot(
                data=agg,
                x="map_type",
                y="sentiment",
                ax=ax,
                hue="role",
                palette=ROLE_PALETTE
            )
        elif mode == "count":
            sns.barplot(
                data=agg,
                x="map",
                y="sentiment",
                ax=ax,
                hue="winloss",
                palette=WINLOSS_PALETTE,
            )
            ax.set_ylabel("Count")
        elif mode == "distribution":
            sns.kdeplot(
                data=agg,
                x="sentiment",
                ax=ax,
                hue="winloss",
                palette=WINLOSS_PALETTE,
                fill=True,
                bw_adjust=1.25
            )
        elif mode == "distribution_all":
            sns.kdeplot(
                data=agg,
                x="sentiment",
                ax=ax,
                hue="author",
                fill=True,
                bw_adjust=1
            )
        else:
            raise ValueError("Incorrect mode")

        if mode in ("distribution", "distribution_all"):
            ax.set_xlim(-1, 7)
            ax.set_xlabel("Quality")
        elif mode != "count":
            ax.set_ylim(bottom=0, top=6)
            ax.set_ylabel("Quality")

        if mode in ("winloss", "maptype", "count", "distribution",
                    "distribution_all", "role", "maptype_role"):
            legend = ax.get_legend()
            if legend is not None:
                if mode == "distribution_all":
                    legend.set_title("Author")
                elif mode in ("role", "maptype_role"):
                    legend.set_title("Role")
                else:
                    legend.set_title("Win / Loss")
                legend.get_frame().set_alpha(0)

        sns.despine(ax=ax)

        if mode not in ("distribution", "distribution_all"):
            ax.tick_params(axis='x', rotation=45)
            if mode in ("maptype", "maptype_role"):
                ax.set_xlabel("Map Type")
            else:
                ax.set_xlabel("Map")

        return fig

    @staticmethod
    def _export_figure(fig):
        fig.set_dpi(450)
        fig.tight_layout()

        buffer = BytesIO()
        fig.savefig(buffer, transparent=True)
        buffer.seek(0)

        plt.close(fig)
        return buffer

# TODO: live-updating plot
