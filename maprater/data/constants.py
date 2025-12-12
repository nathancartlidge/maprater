from enum import Enum

from typing_extensions import NamedTuple


class MapType(Enum):
    CONTROL = 0
    ESCORT = 1
    FLASHPOINT = 2
    HYBRID = 3
    PUSH = 4
    CLASH = 5


MAPS = {
    MapType.CONTROL: [
        "Antarctic",
        "Busan",
        "Ilios",
        "Lijiang",
        "Nepal",
        "Oasis",
        "Samoa",
    ],
    MapType.ESCORT: [
        "Circuit",
        "Dorado",
        "Havana",
        "Junkertown",
        "Rialto",
        "Route 66",
        "Shambali",
        "Gibraltar",
    ],
    MapType.FLASHPOINT: ["Junk City", "Suravasa", "Aatlis"],
    MapType.HYBRID: [
        "Blizzard",
        "Eichenwalde",
        "Hollywood",
        "King's",
        "Midtown",
        "Numbani",
        "Paraiso",
    ],
    MapType.PUSH: ["Colosseo", "Esperanca", "Queen St", "Runasapi"],
    MapType.CLASH: ["Hanaoka", "Anubis"],
}
MAPS_LIST = [map_name for map_set in MAPS.values() for map_name in map_set]
MAP_TYPES = [key.name.title() for key in MAPS]

WINLOSS_PALETTE = {"Win": "#4bc46d", "Loss": "#c9425d"}
RESULTS_EMOJI = {
    "wide-win": "✓",
    "win": "🏆",
    "loss": "❌",
    "wide-loss": "×",
    "draw": "🤝",
}
RESULTS_SCORES = {"wide-win": 0.5, "win": 1, "loss": -1, "wide-loss": -0.5, "draw": 0}
RESULTS_SCORE_0_1 = {
    "wide-win": 0.75,
    "win": 1,
    "loss": 0,
    "wide-loss": 0.25,
    "draw": 0.5,
}
RESULTS_SCORES_PRIME = {"wide-win": 1, "win": 1, "loss": -1, "wide-loss": -1, "draw": 0}
RESULTS_SCORES_PRIME_0_1 = {
    "wide-win": 1,
    "win": 1,
    "loss": 0,
    "wide-loss": 0,
    "draw": 0.5,
}
ROLE_PALETTE = {"Tank": "tab:orange", "Damage": "tab:blue", "Support": "tab:green"}

OW2_MAPS = [
    "Queen St",
    "Circuit",
    "Colosseo",
    "Midtown",
    "Paraiso",
    "Esperanca",
    "Shambali",
    "Antarctic",
    "Junk City",
    "Suravasa",
    "Samoa",
    "Runasapi",
    "Hanaoka",
    "Anubis",
]

TTL = 60

SEASONS = {
    13: "2024-10-15T19:00:00",
    14: "2024-12-10T19:00:00",
    15: "2025-02-18T19:00:00",
    16: "2025-04-22T19:00:00",
    17: "2025-06-24T19:00:00",
    18: "2025-08-26T19:00:00",
    19: "2025-10-14T19:00:00",
    20: "2025-12-09T19:00:00",
    21: "2026-12-31T23:59:59",
}


class Seasons(Enum):
    Thirteen = 13
    Fourteen = 14
    Fifteen = 15
    Sixteen = 16
    Seventeen = 17
    Eighteen = 18
    Nineteen = 19
    Twenty = 20
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
    "Anubis": "Okay",
    "Aatlis": "Okay",
}


class Ranks(Enum):
    BRONZE = 0
    SILVER = 1
    GOLD = 2
    PLAT = 3
    DIAMOND = 4
    MASTERS = 5
    GM = 6
    CHAMP = 7


RANK_EMOJI = {
    Ranks.BRONZE: "<:bronze:1448043323800555631>",
    Ranks.SILVER: "<:silver:1448043196067221676>",
    Ranks.GOLD: "<:gold:1448043378393612329>",
    Ranks.PLAT: "<:plat:1448043225548984320>",
    Ranks.DIAMOND: "<:diamond:1448043147497177178>",
    Ranks.MASTERS: "<:master:1448043072486248620>",
    Ranks.GM: "<:gm:1448043106577416283>",
    Ranks.CHAMP: "<:champ:1448043261137522748>",
}


class FullRank(NamedTuple):
    rank: Ranks
    division: int
    percentage: int

    @property
    def emoji(self) -> str:
        return RANK_EMOJI[self.rank]

    def __str__(self):
        return f"{self.emoji} **{self.division}** @ {self.percentage}%"
