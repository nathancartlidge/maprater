from datetime import datetime
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
MAPS_LIST = [map_name for map_set in MAPS.values() for map_name in map_set]
MAP_TYPES = [key.name.title() for key in MAPS]

WINLOSS_PALETTE = {"Win": "#4bc46d", "Loss": "#c9425d"}
ROLE_PALETTE = {"Tank": "tab:orange", "Damage": "tab:blue", "Support": "tab:green"}

OW2_MAPS = ["Queen St", "Circuit", "Colosseo", "Midtown", "Paraiso",
            "Esperanca", "Shambali", "Antarctic", "Junk City", "Suravasa",
            "Samoa", "Runasapi", "Hanaoka", "Anubis"]

TTL = 60

SEASONS = {
    13: "2024-10-15T19:00:00",
    14: "2024-12-10T19:00:00",
    15: "2025-02-11T19:00:00"
}


class Seasons(Enum):
    Thirteen = 13
    Fourteen = 14
    All = None


DEFAULT_SEASON = Seasons.All

FIRE_RANKINGS = {
    "Antarctic": "Good",
    "Busan": "Good",
    "Ilios": "Bad",
    "Lijiang": "Good",
    "Nepal": "Good",
    "Oasis": "Good",
    "Samoa": "Okay",
    "Circuit": "Good",
    "Dorado": "Bad",
    "Havana": "Good",
    "Junkertown": "Bad",
    "Rialto": "Good",
    "Route 66": "Okay",
    "Shambali": "Good",
    "Gibraltar": "Bad",
    "Junk City": "Okay",
    "Suravasa": "Good",
    "Blizzard": "Bad",
    "Eichenwalde": "Good",
    "Hollywood": "Bad",
    "King's": "Good",
    "Midtown": "Okay",
    "Numbani": "Bad",
    "Paraiso": "Bad",
    "Colosseo": "Good",
    "Esperanca": "Bad",
    "Queen St": "Bad",
    "Runasapi": "Good",
    "Hanaoka": "Good",
    "Anubis": "Okay"
}
