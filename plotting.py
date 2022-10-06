import io
import logging

import discord
import pandas as pd
import seaborn as sns
import matplotlib as mpl
import matplotlib.pyplot as plt

from discord.commands import Option, slash_command
from discord.ext import commands

from db_handler import DatabaseHandler

PLOT_DESCRIPTION = {
    "normalise": "Data has been normalised by winrate (equal weight to ratings given from losses as ratings given from wins)",
    "group": "Data has been separated by win/loss",
    "ungroup": "Data has not been normalised",
    "count": "Data shows the number of ratings per map, separated by win/loss",
    "distribution": "Data shows KDE-smoothed plot of ranking distribution, separated by win/loss",
    "distribution_all": "Data shows KDE-smoothed plot of ranking distribution, separated by voter"
}
WINLOSS_PALETTE = {"Win": "#4bc46d", "Loss": "#c9425d"}


class PlotCommands(commands.Cog):
    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler

    @slash_command(description="Plot the current data")
    async def plot(self, ctx: discord.context.ApplicationContext,
                   mode: Option(str, description="What plotting mode should be used?",
                                default="normalise",
                                choices=["normalise", "group", "ungroup", "count", "distribution"]),
                   user: Option(discord.Member, description="Limit data to a particular person",
                                required=False, default=None)):
        logging.debug("Creating Plot - Invoked by %s", ctx.author)
        data = self.db_handler.get_pandas_data(ctx.guild_id)

        if user is not None:
            # filter data to the user specified
            data = data[data.author == str(user)]
        else:
            if mode == "distribution":
                mode = "distribution_all"


        if (lines := data.shape[0]) < 1:
            await ctx.respond(
                content="Error - No matching data found - Cannot create graphs",
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
                content="Error occured while making graph",
                ephemeral=True
            )
            raise

        await ctx.respond(
            content=f"Results plot for {lines} entries\n*{PLOT_DESCRIPTION[mode]}*",
            files=[discord.File(fp=buffer, filename="graph.png")],
            ephemeral=True
        )

        del buffer, figure, aggregate

    def _process_data(self, data: pd.DataFrame, mode: str = None,
                      draw_is_loss: bool = False):
        """Converts raw Dataframe to Pandas group-by format"""
        
        data = data.replace(to_replace="x", value="l" if draw_is_loss else "w")
        data = data.replace(to_replace=["w", "l"], value=["Win", "Loss"])

        if mode in ("distribution", "distribution_all"):
            return data  # No processing needed - not split by map

        if mode == "ungroup":
            grouped = data.groupby(["map"])["sentiment"]
        else:
            grouped = data.groupby(["map", "winloss"])["sentiment"]

        if mode == "normalise" or mode is None:
            agg = grouped.mean()
            agg = agg.unstack()
            agg = agg.mean(axis=1)
        elif mode in ("group", "ungroup"):
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

        fig, ax = plt.subplots(figsize=(12, 6))

        if mode == "normalise" or mode is None:
            sns.barplot(
                data=agg,
                x="map",
                y=0,
                ax=ax,
                palette="flare_r"
            )
        elif mode == "group":
            sns.barplot(
                data=agg,
                x="map",
                y="sentiment",
                ax=ax,
                hue="winloss",
                palette=WINLOSS_PALETTE
            )
        elif mode == "ungroup":
            sns.barplot(
                data=agg,
                x="map",
                y="sentiment",
                ax=ax,
                palette="flare_r"
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
            ax.set_ylim((0, 6))
            ax.set_ylabel("Quality")

        if mode in ("group", "count", "distribution", "distribution_all"):
            legend = ax.get_legend()
            if mode == "distribution_all":
                legend.set_title("Author")
            else:
                legend.set_title("Win / Loss")
            legend.get_frame().set_alpha(0)

        sns.despine(ax=ax)

        if mode not in ("distribution", "distribution_all"):
            ax.tick_params(axis='x', rotation=45)
            ax.set_xlabel("Map")

        return fig

    @staticmethod
    def _export_figure(fig):
        fig.set_dpi(450)
        fig.tight_layout()

        buffer = io.BytesIO()
        fig.savefig(buffer, transparent=True)
        buffer.seek(0)

        plt.close(fig)
        return buffer

# TODO: live-updating plot