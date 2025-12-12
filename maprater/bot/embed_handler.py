"""Provides views - primarily for map voting"""

from datetime import datetime, timezone
import itertools
import logging

import discord
from discord import ButtonStyle
from discord.interactions import Interaction

from maprater.data.db_handler import DatabaseHandler
from maprater.data.constants import (
    DEFAULT_SEASON,
    MAPS,
    RESULTS_SCORES,
    MapType,
    RESULTS_EMOJI,
    FullRank,
)
from maprater.bot.plotting import PlotCommands


class MapButtons(discord.ui.View):
    """Persistent map rating buttons"""

    MAP_TYPES: list[MapType | None] = None

    def __init__(self, db_handler: DatabaseHandler):
        self.db_handler = db_handler
        super().__init__(timeout=None)  # timeout of the view must be set to None

    def __init_subclass__(cls, **kwargs):
        # cursed!!
        cls.make_buttons(cls)
        super().__init_subclass__()

    async def _callback(self, map_name, interaction: Interaction):
        logging.info("map callback - %s by %s", map_name, interaction.user)
        _, past_results = await self.db_handler.get_last(
            server_id=interaction.guild_id,
            count=100,
            username=interaction.user.name,
            map_name=map_name,
        )
        winrate = (
            (1 + sum("win" in l[2] for l in past_results))
            / (len(past_results) + 2)
            * 100
        )
        past_results_emoji = [
            RESULTS_EMOJI[result] for _, _, result, _ in past_results[:20]
        ]
        map_info = f"-# Normalised Winrate: `{winrate:.1f}%`\n-# Past Results: {''.join(past_results_emoji)}\n"

        # await interaction.response.send_message(
        #     content=text, view=VotingButtons(map_name, self.db_handler), ephemeral=True
        # )
        current_rank = await self.db_handler.get_rank(
            interaction.guild_id, interaction.user.name
        )
        await interaction.response.send_modal(
            VotingModal(
                map_name, self.db_handler, map_info=map_info, current_rank=current_rank
            )
        )

    def make_buttons(self):
        if self.MAP_TYPES is None:
            raise NotImplementedError()

        i = 0
        colours = itertools.cycle(
            [ButtonStyle.red, ButtonStyle.green, ButtonStyle.blurple, ButtonStyle.grey]
        )
        for map_type in self.MAP_TYPES:
            colour = next(colours)
            if map_type is None:
                continue

            map_names = sorted(MAPS[map_type])
            for map_name in map_names:

                @discord.ui.button(
                    label=map_name, custom_id=map_name, row=i // 5, style=colour
                )
                async def func(self, interaction: Interaction, _, map_name=map_name):
                    return await self._callback(
                        map_name=map_name, interaction=interaction
                    )

                setattr(self, f"_map_{map_name}", func)
                i += 1
            if i % 5 == 4:
                i += 1


class OW1Modes(MapButtons):
    MAP_TYPES = (MapType.CONTROL, MapType.ESCORT, MapType.HYBRID)


class OW2Modes(MapButtons):
    MAP_TYPES = (MapType.PUSH, MapType.FLASHPOINT, None, MapType.CLASH)


BUTTON_MAPS = {"Overwatch 1 Modes": OW1Modes, "Overwatch 2 Modes": OW2Modes}


class VotingCore:
    def __init__(self, voted_map: str, db_handler: DatabaseHandler):
        self.map = voted_map
        self.db_handler = db_handler

    async def _submit_edit(self, result: str, interaction: Interaction):
        net_result, recent_results_emoji = await self._submit(result, interaction)

        await interaction.response.edit_message(
            content=f"**{result.title()}** on **{self.map}**\n"
            f"-# Today: `{net_result:+}` {''.join(recent_results_emoji)}",
            view=None,
        )

    async def _submit_post(self, result: int | str, interaction: Interaction):
        net_result, recent_results_emoji = await self._submit(result, interaction)

        if isinstance(result, int):
            result_text = "Win" if result > 0 else "Draw" if result == 0 else "Loss"
        else:
            result_text = result.title()

        rank = await self.db_handler.get_rank(
            interaction.guild_id, interaction.user.name
        )
        if rank is not None:
            rank_text = f"{rank}\n"
        else:
            rank_text = ""

        await interaction.response.send_message(
            content=f"**{result_text}** on **{self.map}**\n{rank_text}"
            f"-# Today: `{net_result:+}` {''.join(recent_results_emoji)}\n",
            ephemeral=True,
        )

    async def _submit(self, result: str | int, interaction: Interaction):
        assert interaction.guild_id is not None
        logging.info("%s voted: %s on %s", interaction.user.name, result, self.map)

        await self.db_handler.write_line(
            server_id=interaction.guild_id,
            username=interaction.user.name,
            mapname=self.map,
            result=result,
            timestamp=datetime.now(tz=timezone.utc).timestamp(),
        )
        if isinstance(result, int):
            # update rank
            await self.db_handler.update_rank(
                interaction.guild_id, interaction.user.name, result
            )

        _, results = await self.db_handler.get_last(
            interaction.guild_id, 25, interaction.user.name
        )
        min_time = (
            datetime.now(tz=timezone.utc)
            .replace(hour=0, minute=0, second=0, microsecond=0)
            .timestamp()
        )
        recent_results = [l for l in results if l[3] >= min_time]

        recent_results_emoji = [
            RESULTS_EMOJI[result] for _, _, result, _ in recent_results
        ]
        net_result = sum(RESULTS_SCORES[result] for _, _, result, _ in recent_results)
        return net_result, recent_results_emoji


class VotingModal(discord.ui.Modal, VotingCore):
    def __init__(
        self,
        voted_map: str,
        db_handler: DatabaseHandler,
        map_info: str,
        current_rank: FullRank | None,
        **kwargs,
    ):
        VotingCore.__init__(self, voted_map, db_handler)
        super().__init__(**kwargs, title=voted_map, timeout=1200)
        self.add_item(
            discord.ui.TextDisplay(
                content="*Enter the percentage SR change, or `w`/`l`/`d` for win/loss/draw*"
            )
        )

        self.add_item(discord.ui.TextDisplay(content=map_info))

        if current_rank is not None:
            self.add_item(
                discord.ui.TextDisplay(
                    content=f"-# I think you are currently {current_rank}"
                )
            )
        self.add_item(
            discord.ui.TextInput(
                label="Rank Change", required=True, placeholder="25%", id=0
            )
        )

    async def on_submit(self, interaction: discord.Interaction):
        result_raw: str = self.find_item(0).value.strip(" %")
        if result_raw.isnumeric():
            await self._submit_post(result=int(result_raw), interaction=interaction)
        elif result_raw and result_raw.lower()[0] in ("w", "l", "d"):
            result_string = {"w": "win", "l": "loss", "d": "draw"}[
                result_raw.lower()[0]
            ]
            await self._submit_post(result=result_string, interaction=interaction)
        else:
            await interaction.response.send_message(
                ":warning: Unable to parse SR change", ephemeral=True
            )


class VotingButtons(discord.ui.View, VotingCore):
    """Provides the initialised voting buttons"""

    def __init__(self, voted_map, db_handler: DatabaseHandler):
        super().__init__(timeout=1200)  # stay active for 20 minutes
        VotingCore.__init__(self, voted_map, db_handler)

    @discord.ui.button(label="win", style=ButtonStyle.green, row=0)
    async def _win(self, interaction, _):
        await self._submit_edit(result="win", interaction=interaction)

    @discord.ui.button(label="wide win", style=ButtonStyle.grey, row=0)
    async def _wide_win(self, interaction, _):
        await self._submit_edit(result="wide-win", interaction=interaction)

    @discord.ui.button(label="draw", style=ButtonStyle.grey, row=0)
    async def _draw(self, interaction, _):
        await self._submit_edit(result="draw", interaction=interaction)

    @discord.ui.button(label="wide loss", style=ButtonStyle.grey, row=0)
    async def _wide_loss(self, interaction, _):
        await self._submit_edit(result="wide-loss", interaction=interaction)

    @discord.ui.button(label="loss", style=ButtonStyle.red, row=0)
    async def _loss(self, interaction, _):
        await self._submit_edit(result="loss", interaction=interaction)


class PlotButtons(discord.ui.View):
    """Persistent plot buttons"""

    def __init__(self, db_handler: DatabaseHandler) -> None:
        super().__init__(timeout=None)
        self.db_handler = db_handler
        self.plot_commands = PlotCommands(db_handler)

    @discord.ui.button(
        label="Per-Map Winrate", custom_id="pmwr", style=ButtonStyle.blurple
    )
    async def _pmwr(self, interaction: Interaction, _):
        await self.plot_commands.map_winrate.callback(
            self=self.plot_commands,
            interaction=interaction,
            user=interaction.user,
            rein_colours=False,
            season=DEFAULT_SEASON,
        )

    @discord.ui.button(
        label="Per-Map Play Count", custom_id="pmpc", style=ButtonStyle.blurple
    )
    async def _pmpc(self, interaction: Interaction, _):
        await self.plot_commands.map_play_count.callback(
            self=self.plot_commands,
            interaction=interaction,
            user=interaction.user,
            win_loss=False,
            rein_colours=False,
            season=DEFAULT_SEASON,
        )

    @discord.ui.button(label="Rolling Winrate", custom_id="rw", style=ButtonStyle.green)
    async def _rw(self, interaction: Interaction, _):
        await self.plot_commands.winrate.callback(
            self=self.plot_commands,
            interaction=interaction,
            user=interaction.user,
            window_size=20,
            season=DEFAULT_SEASON,
        )

    @discord.ui.button(label="Relative Rank", custom_id="rr", style=ButtonStyle.green)
    async def _rr(self, interaction: Interaction, _):
        await self.plot_commands.relative_rank.callback(
            self=self.plot_commands,
            interaction=interaction,
            user=interaction.user,
            real_dates=False,
            season=DEFAULT_SEASON,
        )

    @discord.ui.button(label="Streaks", custom_id="s", style=ButtonStyle.red)
    async def _s(self, interaction: Interaction, _):
        await self.plot_commands.streak.callback(
            self=self.plot_commands,
            interaction=interaction,
            user=interaction.user,
            keep_aspect=True,
            season=DEFAULT_SEASON,
        )


class UndoLast(discord.ui.View):
    """View for the 'undo' button triggered after /last"""

    def __init__(
        self,
        lines,
        ids: list[int],
        db_handler: DatabaseHandler,
        can_delete: bool = False,
    ) -> None:
        super().__init__()
        self.lines = lines
        self.ids = ids
        self.db_handler = db_handler
        for child in self.children:
            child.disabled = not can_delete  # type: ignore

    @discord.ui.button(label="Delete row(s)", style=ButtonStyle.red, disabled=True)
    async def _undo(self, interaction: Interaction, _):
        assert interaction.message is not None
        assert interaction.guild_id is not None

        await self.db_handler.delete_ids(interaction.guild_id, self.ids)
        await interaction.response.edit_message(
            content="\n".join(self.lines) + "\n*successfully deleted*", view=None
        )
