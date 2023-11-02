"""Provides views - primarily for map voting"""

import time
import logging

import discord
from discord import ButtonStyle
from discord.interactions import Interaction

from db_handler import DatabaseHandler
from rank_update import check_update

QUAL = [
    "I should uninstall",
    "Bad",
    "Mediocre",
    "OK",
    "Decent",
    "GG!",
    "I should reinstall"
]

TTL = 60


class MapButtons(discord.ui.View):
    """Persistent map rating buttons"""

    def __init__(self, db_handler):
        super().__init__(timeout=None)  # timeout of the view must be set to None
        self.db_handler = db_handler

    async def _callback(self, map_name, interaction: Interaction):
        logging.info("map callback - %s by %s", map_name, interaction.user)

        deltime = round(time.time() + TTL)
        text = f"rating for **{map_name}**: (deletes <t:{deltime}:R>)"

        await interaction.response.send_message(
            content=text,
            view=VotingButtons(text, map_name, self.db_handler),
            delete_after=TTL
        )

    @discord.ui.button(label="Push", custom_id="Push",
                       style=ButtonStyle.red, row=0)
    async def _Push(self, _, interaction):
        await self._callback("Push", interaction)

    @discord.ui.button(label="Payload", custom_id="Payload",
                       style=ButtonStyle.grey, row=0)
    async def _Payload(self, _, interaction):
        await self._callback("Payload", interaction)

    @discord.ui.button(label="Hybrid", custom_id="Hybrid",
                       style=ButtonStyle.red, row=0)
    async def _Hybrid(self, _, interaction):
        await self._callback("Hybrid", interaction)

    @discord.ui.button(label="Control", custom_id="Control",
                       style=ButtonStyle.grey, row=0)
    async def _Control(self, _, interaction):
        await self._callback("Control", interaction)

    @discord.ui.button(label="Flashpoint", custom_id="Flashpoint",
                       style=ButtonStyle.red, row=0)
    async def _Flashpoint(self, _, interaction):
        await self._callback("Flashpoint", interaction)


class VotingButtons(discord.ui.View):
    """Provides the initialised voting buttons"""

    def __init__(self, line, voted_map, db_handler: DatabaseHandler):
        super().__init__()
        self.line = line
        self.map = voted_map
        self.db_handler = db_handler
        self.votes = []
        self.partial_votes = {}

    async def _result(self, result, interaction: Interaction):
        logging.info("result - %s by %s", result, interaction.user)
        user = str(interaction.user)
        if user not in self.partial_votes:
            self.partial_votes[user] = {}
        self.partial_votes[user]["winloss"] = result
        await interaction.response.defer(ephemeral=True, invisible=True)

    @discord.ui.button(label="Win", style=ButtonStyle.green, row=0)
    async def _win(self, _, interaction):
        await self._result("w", interaction)

    @discord.ui.button(label="Draw", style=ButtonStyle.grey, row=0)
    async def _draw(self, _, interaction):
        await self._result("x", interaction)

    @discord.ui.button(label="Loss", style=ButtonStyle.red, row=0)
    async def _loss(self, _, interaction):
        await self._result("l", interaction)

    async def _role(self, role, interaction: Interaction):
        logging.info("role - %s by %s", role, interaction.user)
        user = str(interaction.user)
        if user not in self.partial_votes:
            self.partial_votes[user] = {}
        self.partial_votes[user]["role"] = role
        await interaction.response.defer(ephemeral=True, invisible=True)

    @discord.ui.button(label="Tank", style=ButtonStyle.grey, row=1)
    async def _tank(self, _, interaction):
        await self._role("t", interaction)

    @discord.ui.button(label="Damage", style=ButtonStyle.grey, row=1)
    async def _damage(self, _, interaction):
        await self._role("d", interaction)

    @discord.ui.button(label="Support", style=ButtonStyle.grey, row=1)
    async def _support(self, _, interaction):
        await self._role("s", interaction)

    async def _quality(self, quality, interaction: Interaction):
        logging.info("quality - %s by %s", quality, interaction.user)
        user = str(interaction.user)
        if user not in self.partial_votes:
            self.partial_votes[user] = {}
        self.partial_votes[user]["quality"] = quality
        await interaction.response.defer(ephemeral=True, invisible=True)

    @discord.ui.button(label=QUAL[5], style=ButtonStyle.green, row=2)
    async def _q5(self, _, interaction):
        await self._quality(5, interaction)

    @discord.ui.button(label=QUAL[4], style=ButtonStyle.grey, row=2)
    async def _q4(self, _, interaction):
        await self._quality(4, interaction)

    @discord.ui.button(label=QUAL[3], style=ButtonStyle.grey, row=2)
    async def _q3(self, _, interaction):
        await self._quality(3, interaction)

    @discord.ui.button(label=QUAL[2], style=ButtonStyle.grey, row=2)
    async def _q2(self, _, interaction):
        await self._quality(2, interaction)

    @discord.ui.button(label=QUAL[1], style=ButtonStyle.red, row=2)
    async def _q1(self, _, interaction):
        await self._quality(1, interaction)

    @discord.ui.button(label=QUAL[6], style=ButtonStyle.green, row=3)
    async def _q6(self, _, interaction):
        await self._quality(6, interaction)

    @discord.ui.button(label=QUAL[0], style=ButtonStyle.red, row=3)
    async def _q0(self, _, interaction):
        await self._quality(0, interaction)

    @discord.ui.button(label="Submit", style=ButtonStyle.blurple, row=4)
    async def _submit(self, _, interaction: Interaction):
        assert interaction.guild_id is not None
        logging.info("Submit - %s", interaction.user)

        if (user := str(interaction.user)) in self.votes:
            await interaction.response.send_message(
                content=":warning: You have already voted! To remove a vote, try `/last`",
                ephemeral=True
            )
            return

        wl = self.partial_votes[user].get("winloss", None)
        ro = self.partial_votes[user].get("role", None)
        qu = self.partial_votes[user].get("quality", None)

        if wl is None or ro is None or qu is None:
            await interaction.response.send_message(
                content=":warning: Please fill in all sections!",
                ephemeral=True
            )
            return

        logging.info("%s voted: %s %s %s %s", user, self.map, wl, ro, qu)

        await self.db_handler.write_line(server_id=interaction.guild_id,
                                         username=user, mapname=self.map,
                                         result=wl, role=ro, sentiment=qu,
                                         datetime=time.time())

        self.votes.append(user)
        voters_line = ", ".join(map(lambda f: f.split("#")[0], self.votes))

        await interaction.response.edit_message(
            content=f"{self.line}\nVoters: *{voters_line}*")

        await check_update(interaction, user, ro, self.db_handler)


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
