"""Provides views - primarily for map voting"""
import itertools
import time
import logging
from enum import Enum
from functools import partial

import discord
from discord import ButtonStyle
from discord.interactions import Interaction

from db_handler import DatabaseHandler

class MapType(Enum):
    CONTROL = 0
    ESCORT = 1
    FLASHPOINT = 2
    HYBRID = 3
    PUSH = 4
    CLASH = 5

MAPS = {
    MapType.CONTROL: ["Antarctic", "Busan", "Ilios", "Lijiang", "Nepal", "Oasis", "Samoa"],
    MapType.ESCORT: ["Circuit", "Dorado", "Havana", "Junkertown", "Rialto", "Route 66", "Shambali", "Gibraltar"],
    MapType.FLASHPOINT: ["Junk City", "Suravasa"],
    MapType.HYBRID: ["Blizzard", "Eichenwalde", "Hollywood", "King's", "Midtown", "Numbani", "Paraiso"],
    MapType.PUSH: ["Colosseo", "Esperanca", "Queen St", "Runasapi"],
    MapType.CLASH: ["Hanaoka", "Anubis"]
}

TTL = 60

class MapButtons(discord.ui.View):
    """Persistent map rating buttons"""
    MAP_TYPES = None

    def __init__(self, db_handler):
        self.db_handler = db_handler
        super().__init__(timeout=None) # timeout of the view must be set to None

    def __init_subclass__(cls, **kwargs):
        # cursed!!
        cls.make_buttons(cls)
        super().__init_subclass__()

    async def _callback(self, map_name, interaction: Interaction):
        logging.info("map callback - %s by %s", map_name, interaction.user)
        text = f"Result for **{map_name}**"

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
        super().__init__()
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
        await interaction.response.edit_message(content=f"{result.title()} on {self.map}", view=None)

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
        await self.message.edit(
            content="\n".join(self.lines) + "\n\n*successfully deleted*",
            view=None
        )
