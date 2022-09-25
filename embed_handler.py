from discord_slash import ButtonStyle
from discord_slash.utils.manage_components import create_actionrow, create_button

WL = ["win", "draw", "loss"]

ROLE = [
    "tank",
    "damage",
    "support"
]

QUAL = [
    "i should uninstall",
    "bad",
    "mediocre",
    "ok",
    "decent",
    "gg!",
    "overwatch is actually good"
]

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
        create_button(style=ButtonStyle.green, label=WL[0], custom_id=prefix + "w"),
        create_button(style=ButtonStyle.grey,  label=WL[1], custom_id=prefix + "x"),
        create_button(style=ButtonStyle.red,   label=WL[2], custom_id=prefix + "l"),
    ]
    return create_actionrow(*options), [option["custom_id"] for option in options] 

def make_role_buttons(prefix: str):
    options = [
        create_button(style=ButtonStyle.gray, label=ROLE[0], custom_id=prefix + "t"),
        create_button(style=ButtonStyle.gray, label=ROLE[1], custom_id=prefix + "d"),
        create_button(style=ButtonStyle.gray, label=ROLE[2], custom_id=prefix + "s"),
    ]
    return create_actionrow(*options), [option["custom_id"] for option in options]

def make_quality_buttons(prefix: str):
    options = [
        create_button(style=ButtonStyle.green, label=QUAL[5], custom_id=prefix + "5"),
        create_button(style=ButtonStyle.gray,  label=QUAL[4], custom_id=prefix + "4"),
        create_button(style=ButtonStyle.gray,  label=QUAL[3], custom_id=prefix + "3"),
        create_button(style=ButtonStyle.gray,  label=QUAL[2], custom_id=prefix + "2"),
        create_button(style=ButtonStyle.red,   label=QUAL[1], custom_id=prefix + "1"),
    ]
    options2 = [
        create_button(style=ButtonStyle.green, label=QUAL[6], custom_id=prefix + "6"),
        create_button(style=ButtonStyle.red,   label=QUAL[0], custom_id=prefix + "0")
    ]
    return create_actionrow(*options), create_actionrow(*options2), \
        [option["custom_id"] for option in options] + [option["custom_id"] for option in options2]

def make_submit_button(prefix: str):
    options = [
        create_button(style=ButtonStyle.blurple, label="Submit", custom_id=prefix + "S"),
    ]
    return create_actionrow(*options), [option["custom_id"] for option in options] 

def make_plot_buttons():
    options = [
        create_button(style=ButtonStyle.grey, label="update plot")
    ]
    return create_actionrow(*options), options[0]["custom_id"]

def make_last_undo_button(btn_id: str, count):
    label = "Delete rows" if count != 1 else "Delete row"
    button = create_button(style=ButtonStyle.red, label=label, custom_id=btn_id)
    return create_actionrow(button)