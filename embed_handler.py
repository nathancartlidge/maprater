import time
import logging

from datetime import datetime as dt

import discord
from discord.interactions import Interaction
from discord import ButtonStyle

QUAL = [
    "i should uninstall",
    "bad",
    "mediocre",
    "ok",
    "decent",
    "gg!",
    "i should reinstall"
]

TTL = 60

class MapButtons(discord.ui.View):
    def __init__(self, file_handler):
        super().__init__(timeout=None) # timeout of the view must be set to None
        self.file_handler = file_handler

    async def _callback(self, map_name, interaction: Interaction):
        logging.info("map callback - %s by %s", map_name, interaction.user)
        
        deltime = round(time.time() + TTL)
        text = f"rating for **{map_name}**: (deletes <t:{deltime}:R>)"

        await interaction.response.send_message(
            content=text,
            view=VotingButtons(text, map_name, self.file_handler),
            delete_after=TTL
        )

    # auto-generated functions, probably a better way of doing this
    @discord.ui.button(label="Busan", custom_id="Busan", style=ButtonStyle.red, row=0)
    async def _Busan(self, _, interaction):
        await self._callback("Busan", interaction)

    @discord.ui.button(label="Ilios", custom_id="Ilios", style=ButtonStyle.red, row=0)
    async def _Ilios(self, _, interaction):
        await self._callback("Ilios", interaction)

    @discord.ui.button(label="Lijang", custom_id="Lijang", style=ButtonStyle.red, row=0)
    async def _Lijang(self, _, interaction):
        await self._callback("Lijang", interaction)

    @discord.ui.button(label="Nepal", custom_id="Nepal", style=ButtonStyle.red, row=0)
    async def _Nepal(self, _, interaction):
        await self._callback("Nepal", interaction)

    @discord.ui.button(label="Oasis", custom_id="Oasis", style=ButtonStyle.red, row=0)
    async def _Oasis(self, _, interaction):
        await self._callback("Oasis", interaction)

    @discord.ui.button(label="Hanamura", custom_id="Hanamura", style=ButtonStyle.blurple, row=1)
    async def _Hanamura(self, _, interaction):
        await self._callback("Hanamura", interaction)

    @discord.ui.button(label="Volskaya", custom_id="Volskaya", style=ButtonStyle.blurple, row=1)
    async def _Volskaya(self, _, interaction):
        await self._callback("Volskaya", interaction)

    @discord.ui.button(label="Anubis", custom_id="Anubis", style=ButtonStyle.blurple, row=1)
    async def _Anubis(self, _, interaction):
        await self._callback("Anubis", interaction)

    @discord.ui.button(label="WP: Gibraltar", custom_id="WPG", style=ButtonStyle.green, row=1)
    async def _WPG(self, _, interaction):
        await self._callback("WPG", interaction)

    @discord.ui.button(label="Junkertown", custom_id="Junkertown", style=ButtonStyle.green, row=2)
    async def _Junkertown(self, _, interaction):
        await self._callback("Junkertown", interaction)

    @discord.ui.button(label="Route 66", custom_id="Route66", style=ButtonStyle.green, row=2)
    async def _Route66(self, _, interaction):
        await self._callback("Route66", interaction)

    @discord.ui.button(label="Dorado", custom_id="Dorado", style=ButtonStyle.green, row=2)
    async def _Dorado(self, _, interaction):
        await self._callback("Dorado", interaction)

    @discord.ui.button(label="Havana", custom_id="Havana", style=ButtonStyle.green, row=2)
    async def _Havana(self, _, interaction):
        await self._callback("Havana", interaction)

    @discord.ui.button(label="Rialto", custom_id="Rialto", style=ButtonStyle.green, row=2)
    async def _Rialto(self, _, interaction):
        await self._callback("Rialto", interaction)

    @discord.ui.button(label="Blizzard World", custom_id="Blizzard", style=ButtonStyle.grey, row=3)
    async def _Blizzard(self, _, interaction):
        await self._callback("Blizzard", interaction)

    @discord.ui.button(label="Eichenwalde", custom_id="Eich", style=ButtonStyle.grey, row=3)
    async def _Eich(self, _, interaction):
        await self._callback("Eich", interaction)

    @discord.ui.button(label="Kings Row", custom_id="Kings", style=ButtonStyle.grey, row=3)
    async def _Kings(self, _, interaction):
        await self._callback("Kings", interaction)

    @discord.ui.button(label="Hollywood", custom_id="Hollywood", style=ButtonStyle.grey, row=3)
    async def _Hollywood(self, _, interaction):
        await self._callback("Hollywood", interaction)

    @discord.ui.button(label="Numbani", custom_id="Numbani", style=ButtonStyle.grey, row=3)
    async def _Numbani(self, _, interaction):
        await self._callback("Numbani", interaction)


class VotingButtons(discord.ui.View):
    def __init__(self, line, voted_map, file_handler):
        super().__init__()
        self.line = line
        self.map = voted_map
        self.file_handler = file_handler
        self.votes = []
        self.partial_votes = {}

    async def _result(self, result, interaction: Interaction):
        logging.info("result - %s by %s", result, interaction.user)
        user = str(interaction.user)
        if user not in self.partial_votes:
            self.partial_votes[user] = {}
        self.partial_votes[user]["winloss"] = result
        await interaction.response.defer(ephemeral=True, invisible=True)

    @discord.ui.button(label="win", style=ButtonStyle.green, row=0)
    async def _win(self, _, interaction):
        await self._result("w", interaction)

    @discord.ui.button(label="draw", style=ButtonStyle.grey, row=0)
    async def _draw(self, _, interaction):
        await self._result("w", interaction)

    @discord.ui.button(label="loss", style=ButtonStyle.red, row=0)
    async def _loss(self, _, interaction):
        await self._result("w", interaction)


    async def _role(self, role, interaction: Interaction):
        logging.info("role - %s by %s", role, interaction.user)
        user = str(interaction.user)
        if user not in self.partial_votes:
            self.partial_votes[user] = {}
        self.partial_votes[user]["role"] = role
        await interaction.response.defer(ephemeral=True, invisible=True)

    @discord.ui.button(label="tank", style=ButtonStyle.grey, row=1)
    async def _tank(self, _, interaction):
        await self._role("t", interaction)

    @discord.ui.button(label="damage", style=ButtonStyle.grey, row=1)
    async def _damage(self, _, interaction):
        await self._role("d", interaction)

    @discord.ui.button(label="support", style=ButtonStyle.grey, row=1)
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
        logging.info("Submit - %s", interaction.user)

        if (user := str(interaction.user)) in self.votes:
            await interaction.response.send_message(
                content="You have already voted! To remove a vote, use the `/last` command",
                ephemeral=True
            )
            return

        a = self.partial_votes[user].get("winloss", None)
        b = self.partial_votes[user].get("role", None)
        c = self.partial_votes[user].get("quality", None)

        if a is None or b is None or c is None:
            await interaction.response.send_message(
                content="Please fill in all sections!",
                ephemeral=True
            )
            return

        logging.info("%s voted: %s %s %s %s", user, self.map, a, b, c)
        await self.file_handler.write_line(user, self.map, a, b, c, dt.now().isoformat())

        self.votes.append(user)
        voters_line = ", ".join(map(lambda f: f.split("#")[0], self.votes))

        await interaction.response.edit_message(
            content=f"{self.line}\nVoters: *{voters_line}*")


class UndoLast(discord.ui.View):
    def __init__(self, lines, count, file_handler) -> None:
        self.lines = lines
        self.count = count
        self.handler = file_handler
        super().__init__()

    @discord.ui.button(label="Delete row(s)", style=ButtonStyle.red)
    async def _undo(self, _, interaction):
        await self.handler.delete_last(self.count)
        await self.message.edit(
            content=f"```{''.join(self.lines)}```*successfully deleted*",
            view=None
        )