import logging

import discord
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.interactions import Interaction

from data.handler import DatabaseHandler
from definitions import ICONS, Results, Roles

ALIGNMENT_UPDATE = "\n> have you **not** just had an update? run the command" \
                   + "`/rank_update [role]` after an update to fix the alignment"


class UpdateCommands(discord.Cog):
    """Function to provide Rank Update Handling"""

    def __init__(self, bot: discord.Bot, db_handler: DatabaseHandler) -> None:
        super().__init__()
        self.bot = bot
        self.db_handler = db_handler

    @slash_command(description="Rank update information")
    async def rank_update(self, ctx: ApplicationContext,
                          role: Option(str, description="The role to update",
                                       choices=["Tank", "Damage", "Support"],
                                       required=True),
                          reset: Option(bool, description="Force a rank update?",
                                        choices=[True, False], default=False)):
        """A manual rank update"""
        if reset:
            logging.info("Forcing a rank update on %s for %s", role, ctx.user.name)

        role_enum = {"Tank": Roles.TANK, "Damage": Roles.DAMAGE, "Support": Roles.SUPPORT}[role]

        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        _, string = await self.db_handler.do_rank_update(ctx.guild_id, ctx.user.name, role_enum, force=reset)
        if string is None:
            if reset:
                await ctx.respond(f"Rank Update tracking enabled for {role}!", ephemeral=True)
            else:
                await ctx.respond(f"No known rank update for {role} - have you started tracking?",
                                  ephemeral=True)
        else:
            string, _ = UpdateCommands.format_update(role_enum, string, reset)
            if reset:
                string += "\n> please rank all your games!"
            await ctx.respond(string, ephemeral=True)

    @staticmethod
    def format_update(role: Roles, results: list[Results], current_sr: int, is_final: bool = False):
        """Formats update strings nicely"""
        lines = []

        win_count = results.count(Results.WIN)
        draw_count = results.count(Results.DRAW)
        loss_count = results.count(Results.LOSS)
        update_emoji = ICONS[win_count >= 5 or loss_count <= win_count]

        if is_final:
            lines.append(f"{ICONS[role]} **Rank Update!**")
        else:
            lines.append(f"{ICONS[role]} **Rank Update So Far:**")

        result_emojis = "".join([ICONS[result] for result in results])
        lines.append(f"{update_emoji}: {result_emojis}")

        win_string = f"{win_count} {('win', 'wins')[win_count != 1]}"
        draw_string = f", {draw_count} {('draw', 'draws')[draw_count != 1]}," if draw_count != 0 else ""
        loss_string = f"{loss_count} {('loss', 'losses')[loss_count != 1]}"

        lines.append(f"{win_string}{draw_string} and {loss_string}")

        sr = 25 * (win_count - loss_count)
        # todo: division estimation

        lines.append(f"Expected Outcome: `{sr:+}sr` (`{current_sr + sr}sr`)")

        return "\n".join(lines), sr

        # todo: a quick way to correct it if it's wrong for an update


async def check_update(interaction: Interaction, user: discord.User, role: Roles, db_handler: DatabaseHandler):
    """Checks whether a rank update is required"""
    updated, results = await db_handler.do_rank_update(interaction.guild_id, user.name, role)
    current_sr = await db_handler.get_sr(interaction.guild_id, user.name, role)
    string, sr = UpdateCommands.format_update(role, results, current_sr, is_final=updated)
    if updated:
        string += ALIGNMENT_UPDATE
        await db_handler.set_sr(interaction.guild_id, user.name, role, min(5000, current_sr + sr))
    await interaction.response.send_message(string, ephemeral=True)
