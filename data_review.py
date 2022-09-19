#%%
import io
from itertools import count
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from discord import File

plt.style.use("dark_background")

# %%
def get_pandas_data():
    data = pd.read_csv("data.csv")
    data["time"] = pd.to_datetime(data["time"])
    data.rename(columns={"win/loss": "winloss"}, inplace=True)
    return data

#%%
def make_figure(data, wingroup=False, countplot=False, draw_is_loss=False):
    data = data.replace(to_replace="x", value="l" if draw_is_loss else "w")

    if wingroup:
        grouped = data.groupby(["map", "winloss"])["sentiment"]
    else:
        grouped = data.groupby(["map"])["sentiment"]

    if countplot:
        agg = grouped.count()
        agg = agg.fillna(0)
    else:
        agg = grouped.mean()

    agg = agg.sort_values()
    agg = agg.reset_index()

    fig, ax = plt.subplots(figsize=(12, 6))

    if wingroup:
        hue = "winloss"
    else:
        hue = None

    sns.barplot(
        data=agg,
        x="map",
        y="sentiment",
        ax=ax,
        hue=hue
    )

    sns.despine(ax=ax)
    ax.tick_params(axis='x', rotation=45)
    ax.set_xlabel("Map")

    if countplot:
        ax.set_ylabel("Count")
    else:
        ax.set_ylabel("Quality")
        ax.set_ylim((0, 6))

    if wingroup:
        ax.get_legend().set_title("Win / Loss")

    fig.set_dpi(300)

    buffer = io.BytesIO()
    fig.savefig(buffer, transparent=True)
    buffer.seek(0)
    return File(fp=buffer, filename="graph.png")

# %%
# TODO: normalise win vs loss
# TODO: filter to a specific person
# TODO: fix colours?
# TODO: live-updating plot