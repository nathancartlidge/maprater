from enum import Enum

class MapType(Enum):
    CONTROL = 0
    ESCORT = 1
    FLASHPOINT = 2
    HYBRID = 3
    PUSH = 4
    CLASH = 5

MAPS = {
    MapType.CONTROL: ["Antarctic", "Busan", "Ilios", "Lijiang", "Nepal", "Oasis", "Samoa"],
    MapType.ESCORT: ["Circuit", "Dorado", "Havana", "Junkertown", "Rialto", "Route 66", "Shambali", "Gibraltar"],
    MapType.FLASHPOINT: ["Junk City", "Suravasa"],
    MapType.HYBRID: ["Blizzard", "Eichenwalde", "Hollywood", "King's", "Midtown", "Numbani", "Paraiso"],
    MapType.PUSH: ["Colosseo", "Esperanca", "Queen St", "Runasapi"],
    MapType.CLASH: ["Hanaoka", "Anubis"]
}

WINLOSS_PALETTE = {"Win": "#4bc46d", "Loss": "#c9425d"}
ROLE_PALETTE = {"Tank": "tab:orange", "Damage": "tab:blue", "Support": "tab:green"}

OW2_MAPS = ["Queen St", "Circuit", "Colosseo", "Midtown", "Paraiso",
            "Esperanca", "Shambali", "Antarctic", "Junk City", "Suravasa",
            "Samoa", "Runasapi", "Hanaoka", "Anubis"]

TTL = 60