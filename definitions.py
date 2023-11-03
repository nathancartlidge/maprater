from enum import Enum


class Roles(Enum):
    TANK = 0
    DAMAGE = 1
    SUPPORT = 2


class Results(Enum):
    WIN = 1
    DRAW = 0
    LOSS = -1


ICONS = {
    Roles.TANK: "<:Tank:1031299011493249155>",
    Roles.DAMAGE: "<:Damage:1031299007793864734>",
    Roles.SUPPORT: "<:Support:1031299004836880384>",
    Results.WIN: "🏆",
    Results.DRAW: "🤝",
    Results.LOSS: "❌",
    True: "📈",
    False: "📉"
}
TTL = 60
