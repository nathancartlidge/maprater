import logging

import discord
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.interactions import Interaction

from db_handler import DatabaseHandler

ALIGNMENT_UPDATE = "\n> have you **not** just had an update? run the command" \
    + "`/rank_update [role]` after an update to fix the alignment"

class UpdateCommand(discord.Cog):
    """Function to provide Rank Update Handling"""
    def __init__(self, db_handler: DatabaseHandler) -> None:
        super().__init__()
        self.db_handler = db_handler

    @slash_command(description="Force a rank update")
    async def rank_update(self, ctx: ApplicationContext,
                          role: Option(str, description="The role to update",
                                       choices=["Tank", "Damage", "Support"],
                                       required=True)):
        """A manual rank update"""
        logging.debug("Forcing a rank update on %s for %s", role, ctx.user)
        role_char = {"Tank": "t", "Damage": "d", "Support": "s"}[role]

        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        _, string = await self.db_handler.do_rank_update(ctx.guild_id, str(ctx.user),
                                                         role_char, force=True)
        if string is None:
            await ctx.respond(f"Rank Update tracking enabled for {role}!", ephemeral=True)
        else:
            string = UpdateCommand.format_update(role_char, string)
            string += "\n> please rank all your games!"
            await ctx.respond(string, ephemeral=True)

    @staticmethod
    def format_update(role: str, result: str):
        """Formats update strings nicely"""
        lines = []

        role_emoji = {"t": "<:Tank:1031299011493249155>",
                      "d": "<:Damage:1031299007793864734>",
                      "s": "<:Support:1031299004836880384>"}[role]
        win_count = result.count("w")
        loss_count = result.count("l")
        update_emoji = "📈"
        if win_count < 7 and loss_count > win_count:
            update_emoji = "📉"

        lines.append(f"{role_emoji} **Rank Update!**")

        result_emoji = result.replace("w", "🏆").replace("x", "🤝").replace("l", "❌")
        lines.append(f"{update_emoji}: {result_emoji}")

        sr = 25 * (win_count - loss_count)
        div = round(sr/100)
        divisions = ((f"lost {div} division(s)", f"gained {div} division(s)")[div > 0],
                      "same division")[round(sr/100) == 0]
        lines.append(f"{win_count} win(s) and {loss_count} loss(es)"
                     + f" - `{sr:+}sr` / *{divisions}*")

        return "\n".join(lines)

async def check_update(interaction: Interaction, username: str,
                       role: str, db_handler: DatabaseHandler):
    """Checks whether a rank update is required"""
    updated, wl_string = await db_handler.do_rank_update(interaction.guild_id,
                                                         username, role)
    if updated:
        string = UpdateCommand.format_update(role, wl_string)
        string += ALIGNMENT_UPDATE
        await interaction.followup.send(string, ephemeral=True)
