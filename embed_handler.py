"""Provides views - primarily for map voting"""

import time
import logging

import discord
from discord import ButtonStyle
from discord.interactions import Interaction

from definitions import Roles, Results, ICONS
from data.handler import DatabaseHandler
from rank_update import check_update


class ResultButtons(discord.ui.View):
    """Persistent input buttons"""

    def __init__(self, bot: discord.Bot, db_handler: DatabaseHandler):
        super().__init__(timeout=None)  # timeout of the view must be set to None
        self.bot = bot
        self.db_handler = db_handler

    async def _callback(self, result: Results, role: Roles, interaction: Interaction):
        assert interaction.guild_id is not None
        # todo: check last submission - time limit
        logging.info("%s: %s on %s", interaction.user, result.name, role.name)
        await self.db_handler.do_update(server_id=interaction.guild_id, username=interaction.user.name, result=result, role=role,
                                        datetime=time.time())
        await check_update(interaction, interaction.user, role, self.db_handler)

    async def _get_update(self, role: Roles, interaction: Interaction):
        assert interaction.guild_id is not None
        # todo: check last submission - time limit
        logging.info("query: %s on %s", interaction.user, role.name)
        await check_update(interaction, interaction.user, role, self.db_handler)

    # Tank
    @discord.ui.button(emoji=ICONS[Roles.TANK], custom_id="Tx",
                       style=ButtonStyle.grey, row=0)
    async def _tank_icon(self, _, interaction):
        await self._get_update(role=Roles.TANK, interaction=interaction)

    @discord.ui.button(label="Win", custom_id="TWin",
                       style=ButtonStyle.green, row=0)
    async def _tank_win(self, _, interaction):
        await self._callback(Results.WIN, Roles.TANK, interaction)

    @discord.ui.button(label="Draw", custom_id="TDraw",
                       style=ButtonStyle.blurple, row=0)
    async def _tank_draw(self, _, interaction):
        await self._callback(Results.DRAW, Roles.TANK, interaction)

    @discord.ui.button(label="Loss", custom_id="TLoss",
                       style=ButtonStyle.red, row=0)
    async def _tank_loss(self, _, interaction):
        await self._callback(Results.LOSS, Roles.TANK, interaction)

    # Damage
    @discord.ui.button(emoji=ICONS[Roles.DAMAGE], custom_id="Dx",
                       style=ButtonStyle.grey, row=1)
    async def _damage_icon(self, _, interaction):
        await self._get_update(role=Roles.DAMAGE, interaction=interaction)

    @discord.ui.button(label="Win", custom_id="DWin",
                       style=ButtonStyle.green, row=1)
    async def _damage_win(self, _, interaction):
        await self._callback(Results.WIN, Roles.DAMAGE, interaction)

    @discord.ui.button(label="Draw", custom_id="DDraw",
                       style=ButtonStyle.blurple, row=1)
    async def _damage_draw(self, _, interaction):
        await self._callback(Results.DRAW, Roles.DAMAGE, interaction)

    @discord.ui.button(label="Loss", custom_id="DLoss",
                       style=ButtonStyle.red, row=1)
    async def _damage_loss(self, _, interaction):
        await self._callback(Results.LOSS, Roles.DAMAGE, interaction)

    # Support
    @discord.ui.button(emoji=ICONS[Roles.SUPPORT], custom_id="Sx",
                       style=ButtonStyle.grey, row=2)
    async def _support_icon(self, _, interaction):
        await self._get_update(role=Roles.SUPPORT, interaction=interaction)

    @discord.ui.button(label="Win", custom_id="SWin",
                       style=ButtonStyle.green, row=2)
    async def _support_win(self, _, interaction):
        await self._callback(Results.WIN, Roles.SUPPORT, interaction)

    @discord.ui.button(label="Draw", custom_id="SDraw",
                       style=ButtonStyle.blurple, row=2)
    async def _support_draw(self, _, interaction):
        await self._callback(Results.DRAW, Roles.SUPPORT, interaction)

    @discord.ui.button(label="Loss", custom_id="SLoss",
                       style=ButtonStyle.red, row=2)
    async def _support_loss(self, _, interaction):
        await self._callback(Results.LOSS, Roles.SUPPORT, interaction)


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
