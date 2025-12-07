from discord.interactions import Interaction
from discord.ext import commands

from maprater.data.db_handler import DatabaseHandler

ALIGNMENT_UPDATE = (
    "\n> have you **not** just had an update? run the command"
    + "`/rank_update [role]` after an update to fix the alignment"
)


class UpdateCommand(commands.Cog):
    """Function to provide Rank Update Handling"""

    def __init__(self, db_handler: DatabaseHandler) -> None:
        super().__init__()
        self.db_handler = db_handler

    # @app_commands.command(name="rank_update", description="Rank update information")
    # @app_commands.describe(
    #     role="The role to update",
    #     reset="Force a rank update?",
    # )
    # @app_commands.choices(role=[
    #     app_commands.Choice(name="Tank", value="Tank"),
    #     app_commands.Choice(name="Damage", value="Damage"),
    #     app_commands.Choice(name="Support", value="Support"),
    # ])
    # async def rank_update(
    #     self,
    #     interaction: Interaction,
    #     role: str,
    #     reset: bool = False,
    # ):
    #     """A manual rank update"""
    #     if reset:
    #         logging.info("Forcing a rank update on %s for %s", role, interaction.user)
    #
    #     role_char = {"Tank": "t", "Damage": "d", "Support": "s"}[role]
    #
    #     if interaction.guild_id is None:
    #         await interaction.response.send_message(":warning: This bot does not support DMs")
    #         return
    #
    #     _, string = await self.db_handler.do_rank_update(
    #         interaction.guild_id, str(interaction.user), role_char, force=reset
    #     )
    #     if string is None:
    #         if reset:
    #             await interaction.response.send_message(
    #                 f"Rank Update tracking enabled for {role}!", ephemeral=True
    #             )
    #         else:
    #             await interaction.response.send_message(
    #                 f"No known rank update for {role} - have you started tracking?",
    #                 ephemeral=True,
    #             )
    #     else:
    #         string = UpdateCommand.format_update(role_char, string, reset)
    #         if reset:
    #             string += "\n> please rank all your games!"
    #         await interaction.response.send_message(string, ephemeral=True)

    @staticmethod
    def format_update(role: str, result: str, is_final: bool = False):
        """Formats update strings nicely"""
        lines = []

        role_emoji = {
            "t": "<:Tank:1031299011493249155>",
            "d": "<:Damage:1031299007793864734>",
            "s": "<:Support:1031299004836880384>",
        }[role]
        win_count = result.count("w")
        loss_count = result.count("l")
        update_emoji = "📈"
        if win_count < 5 and loss_count > win_count:
            update_emoji = "📉"

        if is_final:
            lines.append(f"{role_emoji} **Rank Update!**")
        else:
            lines.append(f"{role_emoji} **Rank Update So Far:**")

        result_emoji = result.replace("w", "🏆").replace("x", "🤝").replace("l", "❌")
        lines.append(f"{update_emoji}: {result_emoji}")

        sr = 25 * (win_count - loss_count)
        div = round(sr / 100)
        divisions = (
            (f"lost {div} division(s)", f"gained {div} division(s)")[div > 0],
            "same division",
        )[round(sr / 100) == 0]
        win_word = ("win", "wins")[win_count != 1]
        loss_word = ("loss", "losses")[loss_count != 1]
        lines.append(f"{win_count} {win_word} and {loss_count} {loss_word}")
        lines.append(f"Expected Outcome: *{divisions}* (`{sr:+}sr`)")

        return "\n".join(lines)


async def check_update(
    interaction: Interaction, username: str, role: str, db_handler: DatabaseHandler
):
    """Checks whether a rank update is required"""
    updated, wl_string = await db_handler.do_rank_update(
        interaction.guild_id, username, role
    )
    if updated:
        string = UpdateCommand.format_update(role, wl_string, is_final=True)
        string += ALIGNMENT_UPDATE
        await interaction.followup.send(string, ephemeral=True)
