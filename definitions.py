from enum import Enum


class Roles(Enum):
    TANK = 0
    DAMAGE = 1
    SUPPORT = 2


class Results(Enum):
    WIN = 1
    DRAW = 0
    LOSS = -1


class Ranks(Enum):
    BRONZE = 0
    SILVER = 1
    GOLD = 2
    PLAT = 3
    DIAMOND = 4
    MASTER = 5
    GRANDMASTER = 6


ICONS = {
    Roles.TANK: "<:Tank:1031299011493249155>",
    Roles.DAMAGE: "<:Damage:1031299007793864734>",
    Roles.SUPPORT: "<:Support:1031299004836880384>",
    Results.WIN: "🏆",
    Results.DRAW: "🤝",
    Results.LOSS: "❌",
    True: "📈",
    False: "📉",
    Ranks.BRONZE: "<:bronze:1174792396786118716>",
    Ranks.SILVER: "<:silver:1174792400942682112>",
    Ranks.GOLD: "<:gold:1174792398098931722>",
    Ranks.PLAT: "<:plat:1174792596992835614>",
    Ranks.DIAMOND: "<:diamond:1174792590881726564>",
    Ranks.MASTER: "<:master:1174792594463658054>",
    Ranks.GRANDMASTER: "<:gm:1174792593062772806>",
}
TTL = 60
