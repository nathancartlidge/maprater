import logging
import os
import discord

from discord_slash import ButtonStyle, ComponentMessage
from discord_slash.utils.manage_components import create_actionrow, create_button
import aiofiles

def make_map_buttons():
    row_1 = [
        create_button(style=ButtonStyle.red, label="Busan",  custom_id="Busan"),
        create_button(style=ButtonStyle.red, label="Ilios",  custom_id="Ilios"),
        create_button(style=ButtonStyle.red, label="Lijang", custom_id="Lijang"),
        create_button(style=ButtonStyle.red, label="Nepal",  custom_id="Nepal"),
        create_button(style=ButtonStyle.red, label="Oasis",  custom_id="Oasis")
    ]
    row_2 = [
        create_button(style=ButtonStyle.blue, label="Hanamura", custom_id="Hanamura"),
        create_button(style=ButtonStyle.blue, label="Volskaya", custom_id="Volskaya"),
        create_button(style=ButtonStyle.blue, label="Anubis",   custom_id="Anubis"),
        create_button(style=ButtonStyle.green, label="Watchpoint: Gibraltar", custom_id="WPG"),
    ]
    row_3 = [
        create_button(style=ButtonStyle.green, label="Junkertown", custom_id="Junkertown"),
        create_button(style=ButtonStyle.green, label="Route 66",   custom_id="Route66"),
        create_button(style=ButtonStyle.green, label="Dorado",     custom_id="Dorado"),
        create_button(style=ButtonStyle.green, label="Havana",     custom_id="Havana"),
        create_button(style=ButtonStyle.green, label="Rialto",     custom_id="Rialto"),
    ]
    row_4 = [
        create_button(style=ButtonStyle.gray, label="Blizzard World", custom_id="Blizzard"),
        create_button(style=ButtonStyle.gray, label="Eichenwalde",    custom_id="Eich"),
        create_button(style=ButtonStyle.gray, label="King's Row",     custom_id="Kings"),
        create_button(style=ButtonStyle.gray, label="Hollywood",      custom_id="Hollywood"),
        create_button(style=ButtonStyle.gray, label="Numbani",        custom_id="Numbani"),
    ]

    arows = [
        create_actionrow(*row_1),
        create_actionrow(*row_2),
        create_actionrow(*row_3),
        create_actionrow(*row_4)
    ]
    return arows, [button["custom_id"] for button in row_1+row_2+row_3+row_4]

def make_winloss_buttons(prefix: str):
    options = [
        create_button(style=ButtonStyle.green, label="win",  custom_id=prefix + "w"),
        create_button(style=ButtonStyle.grey,  label="draw", custom_id=prefix + "x"),
        create_button(style=ButtonStyle.red,   label="loss", custom_id=prefix + "l"),
    ]
    return create_actionrow(*options), [option["custom_id"] for option in options] 

def make_role_buttons(prefix: str):
    options = [
        create_button(style=ButtonStyle.gray, label="tank",    custom_id=prefix + "t"),
        create_button(style=ButtonStyle.gray, label="damage",  custom_id=prefix + "d"),
        create_button(style=ButtonStyle.gray, label="support", custom_id=prefix + "s"),
    ]
    return create_actionrow(*options), [option["custom_id"] for option in options]

def make_quality_buttons(prefix: str):
    options = [
        create_button(style=ButtonStyle.green, label="gg!",     custom_id=prefix + "5"),
        create_button(style=ButtonStyle.gray,  label="decent",   custom_id=prefix + "4"),
        create_button(style=ButtonStyle.gray,  label="ok",     custom_id=prefix + "3"),
        create_button(style=ButtonStyle.gray,  label="mediocre", custom_id=prefix + "2"),
        create_button(style=ButtonStyle.red,   label="bad",      custom_id=prefix + "1"),
    ]
    options2 = [
        create_button(style=ButtonStyle.green, label="overwatch is actually good", custom_id=prefix + "6"),
        create_button(style=ButtonStyle.red,   label="i should uninstall",         custom_id=prefix + "0")
    ]
    return create_actionrow(*options), create_actionrow(*options2), \
        [option["custom_id"] for option in options] + [option["custom_id"] for option in options2]

def make_submit_button(prefix: str):
    options = [
        create_button(style=ButtonStyle.blurple, label="Submit", custom_id=prefix + "S"),
    ]
    return create_actionrow(*options), [option["custom_id"] for option in options] 



async def write_line(*args):
    if os.path.exists("data.csv"):
        size = os.path.getsize("data.csv")
        if size:
            async with aiofiles.open("data.csv", mode="a") as file:
                await file.write(",".join(map(str, args)) + "\n")
            return

    async with aiofiles.open("data.csv", mode="w") as file:
        await file.write("author,map,win/loss,role,sentiment,time\n")
        await file.write(",".join(map(str, args)) + "\n")

async def remove_last_line():
    if os.path.exists("data.csv"):
        async with aiofiles.open("data.csv", mode="r") as file:
            lines = await file.readlines()
        async with aiofiles.open("data.csv", mode="w") as file:
            await file.writelines(lines[:-1])
            return lines[-1]

async def get_line_count():
    if os.path.exists("data.csv"):
        async with aiofiles.open("data.csv", mode="r") as file:
            lines = await file.readlines()
            return len(lines)
    return -1