import logging
from typing import Optional

import discord
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.interactions import Interaction

from data.handler import DatabaseHandler
from definitions import ICONS, Ranks, Results, Roles

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
                                        choices=[True, False], default=False),
                          user: Option(discord.Member, description="See someone else's update",
                                       required=False, default=None)):
        """A manual rank update"""
        if reset and user is None:
            logging.info("Forcing a rank update on %s for %s", role, ctx.user.name)

        role_enum = {"Tank": Roles.TANK, "Damage": Roles.DAMAGE, "Support": Roles.SUPPORT}[role]

        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        profile_active = self.db_handler.get_identity(ctx.guild_id, ctx.user.name if user is None else user.name)
        current_sr = await self.db_handler.get_sr(ctx.guild_id, ctx.user.name if user is None else user.name, role_enum)
        updated, results = await self.db_handler.do_rank_update(ctx.guild_id,
                                                                ctx.user.name if user is None else user.name,
                                                                role_enum, force=reset and user is None)

        if results is None:
            if reset and user is None:
                await ctx.respond(f"Rank Update tracking enabled for {role}!", ephemeral=True)
            else:
                await ctx.respond(f"No known rank update for {role} - have you started tracking?",
                                  ephemeral=True)
        else:
            # todo: profile selection
            embed = self.rank_update_message(
                role_enum,
                results,
                current_sr,
                user,
                profile_active,
                updated
            )
            if reset and user is None:
                embed.add_field(name="Warning", value="Please input all your games!", inline=False)

            await ctx.respond(embed=embed, ephemeral=True)

    @staticmethod
    def rank_update_message(role: Roles, results: list[Results], current_sr: int, user: str,
                            profile_active: Optional[str], updated: bool = False):
        """Formats updates nicely"""
        win_count = results.count(Results.WIN)
        draw_count = results.count(Results.DRAW)
        loss_count = results.count(Results.LOSS)

        update_emoji = ICONS[loss_count <= win_count]
        sr = 25 * (win_count - loss_count)

        if current_sr == 0:
            rank_emoji = ""
        else:
            new_sr = current_sr + sr
            rank = Ranks(max(0, min(6, 1 + (new_sr - 1500) // 500)))
            tier = 5 - ((new_sr % 500) // 100)
            rank_emoji = ICONS[rank] + str(tier)

        embed = discord.Embed(
            title=f"{ICONS[role]} - " + f"{rank_emoji} - `{current_sr + sr}sr`" if current_sr != 0 else None,
            colour=discord.Colour.from_rgb(0x29, 0xAE, 0x67) if sr >= 0 else discord.Colour.red(),
        )

        if profile_active is not None:
            embed.set_author(name=f"{user} as {profile_active}")
        else:
            embed.set_author(name=f"{user}")

        if len(results) > 0:
            result_emojis = "".join([ICONS[result] for result in results])
            win_string = f"{win_count} {('win', 'wins')[win_count != 1]}"
            draw_string = f", {draw_count} {('draw', 'draws')[draw_count != 1]}," if draw_count != 0 else ""
            loss_string = f"{loss_count} {('loss', 'losses')[loss_count != 1]}"

            embed.add_field(
                name="Games This Update",
                value=f"{result_emojis}\n*{win_string}{draw_string} and {loss_string}*",
                inline=False
            )

            final_sr = 25 * (max(5, win_count) - loss_count)
            # todo: division estimation

            embed.add_field(
                name="Change",
                value=f"{update_emoji} (`{sr:+}sr`)",
                inline=True
            )
            if current_sr != 0:
                embed.add_field(
                    name="Outcome",
                    value=f"`{final_sr:+}sr` ({max(5, win_count)}w / {loss_count}l)",
                    inline=True
                )
        else:
            embed.add_field(
                name=" ",
                value=":warning: No games tracked so far this update",
                inline=False
            )

        if updated:
            # todo: a quick way to correct it if it's wrong for an update
            embed.add_field(
                name=" ",
                value=ALIGNMENT_UPDATE,
                inline=False
            )

        return embed

    @staticmethod
    def sr_from_update(results: list[Results]):
        """Formats update strings nicely"""
        win_count = results.count(Results.WIN)
        loss_count = results.count(Results.LOSS)

        if len(results) > 0:
            sr = 25 * (win_count - loss_count)
        else:
            sr = 0

        return sr


async def check_update(interaction: Interaction, user: discord.User, role: Roles, db_handler: DatabaseHandler):
    """Checks whether a rank update is required"""
    profile_active = db_handler.get_identity(interaction.guild_id, user.name)
    updated, results = await db_handler.do_rank_update(interaction.guild_id, user.name, role)
    current_sr = await db_handler.get_sr(interaction.guild_id, user.name, role)
    sr_change = UpdateCommands.sr_from_update(results)
    if updated and current_sr != 0:
        await db_handler.set_sr(interaction.guild_id, user.name, role, min(5000, current_sr + sr_change))
    embed = UpdateCommands.rank_update_message(role, results, current_sr, user.name, profile_active, updated)
    await interaction.response.send_message(embed=embed, ephemeral=True)
