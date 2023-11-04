"""Implements basic bot commands"""

from io import BytesIO
import logging

import discord
from discord import ApplicationContext
from discord.commands import Option, slash_command
from discord.ext import commands

from definitions import ICONS, Roles
from embed_handler import ResultButtons, UndoLast
from data.handler import DatabaseHandler


class BaseCommands(commands.Cog):
    """Basic commands used for bot"""

    def __init__(self, bot: discord.Bot, db_handler: DatabaseHandler):
        self.bot = bot
        self.db_handler = db_handler

    @slash_command(description="Create rating buttons")
    async def make_buttons(self, ctx: ApplicationContext):
        """
        Create map-rating buttons.
        Note that this will only work once per channel?
        """
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        logging.info("Created buttons - Invoked by %s", ctx.author.name)
        await ctx.respond(
            content="*over-sr-watch*",
            view=ResultButtons(self.bot, self.db_handler)
        )

    @slash_command(description="Get raw data")
    async def data(self, ctx: ApplicationContext):
        """Extracts raw data from the bot"""
        logging.info("Getting Raw Data - Invoked by %s", ctx.author.name)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        lines = await self.db_handler.get_line_count(ctx.guild_id)

        if lines < 1:
            await ctx.respond(content=":warning: No ratings found!", ephemeral=True)
            return

        path = self.db_handler.file(ctx.guild_id)
        file = discord.File(fp=path, filename="data.db")

        await ctx.respond(
            content=f"{lines} entries",
            file=file,
            ephemeral=True
        )

    @slash_command(description="Get the last n rows of data")
    async def last(
            self, ctx: ApplicationContext,
            count: Option(int, description="Number of entries to return",
                          min_value=1, max_value=100, required=True),
            user: Option(discord.Member, description="Limit to a particular person",
                         required=False, default=None),
            role: Option(str, description="Limit to a particular role",
                         required=False, default=None, choices=["Tank", "Damage", "Support"])):
        """Prints the last `n` pieces of data to discord, with option to delete"""
        logging.info("Getting last %s rows - Invoked by %s",
                     count, ctx.author)
        if ctx.guild_id is None:
            await ctx.respond(":warning: This bot does not support DMs")
            return

        username = user.name if user is not None else None

        role_enum = {"Tank": Roles.TANK, "Damage": Roles.DAMAGE, "Support": Roles.SUPPORT}[role]
        ids, lines = await self.db_handler.get_last(ctx.guild_id, count, username, role_enum)

        if len(lines) == 0:
            await ctx.respond(content=":warning: No ratings found!", ephemeral=True)
        else:
            can_delete = False
            if isinstance(ctx.user, discord.Member) \
                    and ctx.user.guild_permissions.manage_messages \
                    and len(lines) <= 4:
                can_delete = True

            lines = self._format_lines(lines)
            length = len("\n".join(lines))

            if length >= 2000:
                block = ""
                index = 0
                while index < len(lines) \
                        and len(block + "\n" + lines[index]) < 2000:
                    block += "\n" + lines[index]
                    index += 1

                await ctx.respond(content=block, ephemeral=True)

                while index < len(lines):
                    block = "*(continued)*\n"
                    while index < len(lines) \
                            and len(block + "\n" + lines[index]) < 2000:
                        block += "\n" + lines[index]
                        index += 1

                    await ctx.followup.send(content=block, ephemeral=True)

                return

            elif can_delete:
                # only short responses will need the delete button
                await ctx.respond(
                    content="\n".join(lines),
                    view=UndoLast(lines, ids, self.db_handler, can_delete),
                    ephemeral=True
                )

            else:
                await ctx.respond(
                    content="\n".join(lines),
                    ephemeral=True
                )

    @slash_command(description="Get your current SR")
    async def get_sr(self, ctx: ApplicationContext):
        output = ""
        for role in Roles:
            sr = await self.db_handler.get_sr(ctx.guild_id, ctx.user.name, role)
            output += f"{ICONS[role]}: `{sr}sr`\n"
        await ctx.respond(content=output, ephemeral=True)

    @slash_command(description="Set your current SR for a role")
    async def set_sr(
            self, ctx: ApplicationContext,
            role: Option(str, description="Role to set", choices=["Tank", "Damage", "Support"]),
            value: Option(int, description="Current SR", min_value=0, max_value=5000)
    ):
        role = Roles[role.upper()]
        await self.db_handler.set_sr(ctx.guild_id, ctx.user.name, role, value)
        await ctx.respond(content=f"Set {ICONS[role]} SR to `{value}`", ephemeral=True)

    @slash_command(description="Sets your current profile")
    async def set_profile(
            self, ctx: ApplicationContext,
            name: Option(str, description="Profile Name", required=False, default=None)
    ):
        self.db_handler.set_identity(ctx.guild_id, ctx.user.name, name)
        if name is None:
            await ctx.respond(content=f"Using default identity", ephemeral=True)
        else:
            await ctx.respond(content=f"Using '{name}' identity", ephemeral=True)

    def _format_lines(self, lines: list):
        """convert lines into pretty strings"""
        output = []
        skip_username = len(lines) == 0 or all(line[0] == lines[0][0] for line in lines)
        if skip_username:
            output.append(f"Data for user `{lines[0][0]}`:")
        for (username, result, role, datetime) in lines:
            # todo: cleanup into definitions
            result_string = {"W": "🏆", "L": "❌", "D": "🤝"}[result]
            role_string = {"T": "<:Tank:1031299011493249155>",
                           "D": "<:Damage:1031299007793864734>",
                           "S": "<:Support:1031299004836880384>"}[role]

            if skip_username:
                output.append(f"{result_string} on {role_string} (<t:{datetime}:R>)")
            else:
                output.append(f"`{username.replace('--', ' as ')}`: {result_string} on {role_string} (<t:{datetime}:R>)")

        return output
