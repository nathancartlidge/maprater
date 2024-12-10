"""Provides views - primarily for map voting"""
import itertools
import time
import logging

import discord
from discord import ButtonStyle
from discord.interactions import Interaction

from db_handler import DatabaseHandler
from constants import LATEST_SEASON, MAPS, MapType
from plotting import PlotCommands


class MapButtons(discord.ui.View):
    """Persistent map rating buttons"""
    MAP_TYPES = None

    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler
        super().__init__(timeout=None) # timeout of the view must be set to None

    def __init_subclass__(cls, **kwargs):
        # cursed!!
        cls.make_buttons(cls)
        super().__init_subclass__()

    async def _callback(self, map_name, interaction: Interaction):
        logging.info("map callback - %s by %s", map_name, interaction.user)
        _, past_results = await self.db_handler.get_last(server_id=interaction.guild_id, count=20,
                                                         username=interaction.user.name, map_name=map_name)
        past_results_emoji = [{"win": "🏆", "loss": "❌", "draw": "🤝"}[result] for _, _, result, _ in past_results]
        text = f"**{map_name}**\n-# Past Results: {''.join(past_results_emoji)}\n"

        await interaction.response.send_message(
            content=text,
            view=VotingButtons(map_name, self.db_handler),
            ephemeral=True
        )

    def make_buttons(self):
        if self.MAP_TYPES is None:
            raise NotImplementedError()

        i = 0
        colours = itertools.cycle([ButtonStyle.red, ButtonStyle.green, ButtonStyle.blurple, ButtonStyle.grey])
        for map_type in self.MAP_TYPES:
            map_names = sorted(MAPS[map_type])
            colour = next(colours)
            for map_name in map_names:
                @discord.ui.button(label=map_name, custom_id=map_name, row=i // 5, style=colour)
                async def func(self, _, interaction: Interaction, map_name=map_name):
                    return await self._callback(map_name=map_name, interaction=interaction)

                setattr(self, f'_map_{map_name}', func)
                i += 1
            if i % 5 == 4:
                i += 1


class OW1Modes(MapButtons):
    MAP_TYPES = (MapType.CONTROL, MapType.ESCORT, MapType.HYBRID)


class OW2Modes(MapButtons):
    MAP_TYPES = (MapType.PUSH, MapType.FLASHPOINT, MapType.CLASH)


BUTTON_MAPS = {
    "Overwatch 1 Modes": OW1Modes,
    "Overwatch 2 Modes": OW2Modes
}

class VotingButtons(discord.ui.View):
    """Provides the initialised voting buttons"""
    def __init__(self, voted_map, db_handler: DatabaseHandler):
        super().__init__(timeout=1200) # stay active for 20 minutes
        self.map = voted_map
        self.db_handler = db_handler

    @discord.ui.button(label="win", style=ButtonStyle.green, row=0)
    async def _win(self, _, interaction):
        await self._submit(result="win", interaction=interaction)

    @discord.ui.button(label="draw", style=ButtonStyle.grey, row=0)
    async def _draw(self, _, interaction):
        await self._submit(result="draw", interaction=interaction)

    @discord.ui.button(label="loss", style=ButtonStyle.red, row=0)
    async def _loss(self, _, interaction):
        await self._submit(result="loss", interaction=interaction)

    async def _submit(self, result, interaction: Interaction):
        assert interaction.guild_id is not None
        logging.info("%s voted: %s on %s", interaction.user.name, result, self.map)

        await self.db_handler.write_line(server_id=interaction.guild_id, username=interaction.user.name, mapname=self.map, result=result, datetime=time.time())
        _, recent_results = await self.db_handler.get_last(server_id=interaction.guild_id, count=5, username=interaction.user.name)
        recent_results_emoji = [{"win": "🏆", "loss": "❌", "draw": "🤝"}[result] for _, _, result, _ in recent_results]

        await interaction.response.edit_message(content=f"**{result.title()}** on **{self.map}**\n"
                                                        f"-# Recent Games: {''.join(recent_results_emoji)}", view=None)


class FakeContext:
    def __init__(self, interaction: Interaction):
        self.defer = interaction.response.defer
        self.respond = interaction.respond
        self.guild_id = interaction.guild_id
        self.user = interaction.user


class PlotButtons(discord.ui.View):
    """Persistent plot buttons"""
    def __init__(self, db_handler: DatabaseHandler) -> None:
        super().__init__(timeout=None)
        self.db_handler = db_handler
        self.plot_commands = PlotCommands(db_handler)

    @discord.ui.button(label="Per-Map Winrate", custom_id="pmwr", style=ButtonStyle.blurple)
    async def _pmwr(self, _, interaction: Interaction):
        await self.plot_commands.map_winrate.callback(
            self=self.plot_commands,
            ctx=FakeContext(interaction),
            user=interaction.user,
            season=LATEST_SEASON
        )

    @discord.ui.button(label="Per-Map Play Count", custom_id="pmpc", style=ButtonStyle.blurple)
    async def _pmpc(self, _, interaction: Interaction):
        await self.plot_commands.map_play_count.callback(
            self=self.plot_commands,
            ctx=FakeContext(interaction),
            user=interaction.user,
            win_loss=False,
            season=LATEST_SEASON
        )

    @discord.ui.button(label="Rolling Winrate", custom_id="rw", style=ButtonStyle.green)
    async def _rw(self, _, interaction: Interaction):
        await self.plot_commands.winrate.callback(
            self=self.plot_commands,
            ctx=FakeContext(interaction),
            user=interaction.user,
            window_size=20,
            season=LATEST_SEASON
        )

    @discord.ui.button(label="Relative Rank", custom_id="rr", style=ButtonStyle.green)
    async def _rr(self, _, interaction: Interaction):
        await self.plot_commands.relative_rank.callback(
            self=self.plot_commands,
            ctx=FakeContext(interaction),
            user=interaction.user,
            real_dates=False,
            season=LATEST_SEASON
        )

    @discord.ui.button(label="Streaks", custom_id="s", style=ButtonStyle.red)
    async def _s(self, _, interaction: Interaction):
        await self.plot_commands.streak.callback(
            self=self.plot_commands,
            ctx=FakeContext(interaction),
            user=interaction.user,
            keep_aspect=True,
            season=LATEST_SEASON
        )


class UndoLast(discord.ui.View):
    """View for the 'undo' button triggered after /last"""
    def __init__(self, lines, ids: list[int], db_handler: DatabaseHandler,
                 can_delete: bool = False) -> None:
        super().__init__()
        self.lines = lines
        self.ids = ids
        self.db_handler = db_handler
        for child in self.children:
            child.disabled = not can_delete  # type: ignore

    @discord.ui.button(label="Delete row(s)", style=ButtonStyle.red, disabled=True)
    async def _undo(self, _, interaction: Interaction):
        assert self.message is not None
        assert interaction.guild_id is not None

        await self.db_handler.delete_ids(interaction.guild_id, self.ids)
        await interaction.response.edit_message(
            content="\n".join(self.lines) + "\n*successfully deleted*",
            view=None
        )
