"""A southern European (Mediterranean) fishless pond, month by month.

Everything here is data: which plants show which state in each month, how the
banks and water change through the year, and which animals live in the pond and
when. Abundances are rough phenology for lowland Iberia / southern France /
Italy (0 = absent, 3 = peak), indexed January..December.

The pond is fishless and semi-permanent: the kind amphibians breed in. That
rules out fish (in practice the invasive mosquitofish, Gambusia holbrooki,
which eats tadpoles) and branchiopods such as Triops or fairy shrimps, which
need ponds that dry out completely every summer.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from datetime import date

TAU = math.tau


# ---------------------------------------------------------------- seasons
def _months(*ms: int) -> frozenset:
    return frozenset(ms)


SEASON_NAMES = ["WINTER", "WINTER", "SPRING", "SPRING", "SPRING", "SUMMER",
                "SUMMER", "SUMMER", "AUTUMN", "AUTUMN", "AUTUMN", "WINTER"]

# Near bank, near bank highlight, far hills, far hills highlight. Mediterranean
# grasslands are greenest in winter and spring (the rainy season), turn golden
# in the summer drought and green up again after the autumn rains.
HILLS = [
    (0x4A8C46, 0x6AAA58, 0x7AA898, 0x96C0AC),  # Jan
    (0x4C9444, 0x70B456, 0x78AE96, 0x94C6AA),
    (0x4C9A3C, 0x74C050, 0x74B48E, 0x90CCA6),
    (0x54A03A, 0x7CC452, 0x74B48E, 0x90CCA6),
    (0x6CA03C, 0x94C252, 0x80B48A, 0x9CCAA0),
    (0x9AA042, 0xBCBC58, 0x9CB488, 0xB4C69C),  # Jun: drying out
    (0xBC9C4A, 0xDCC070, 0xB4AE84, 0xC8C49C),
    (0xC09848, 0xE0BC6C, 0xB8AC80, 0xCCC29A),
    (0xB4944A, 0xD4B468, 0xB0AA84, 0xC4C09C),
    (0x9C9448, 0xBCB062, 0xA0AC88, 0xB8C2A0),  # Oct: first rains
    (0x6A9A46, 0x8CB85C, 0x88AE92, 0xA2C4A8),
    (0x50904A, 0x70AE5C, 0x80AA96, 0x9AC2AC),
]
SKIES = {
    "WINTER": [0x5C80C4, 0x7898D0, 0x94B2DC, 0xB0CAE6, 0xCCDEEE],
    "SPRING": [0x3C6FD8, 0x5890F0, 0x78B0F8, 0x9CD0F8, 0xC4E8F8],
    "SUMMER": [0x2C5CCC, 0x4680E4, 0x66A4F0, 0x8CC4F4, 0xD8ECF0],
    "AUTUMN": [0x4870C8, 0x6490DC, 0x84AEE6, 0xA8C8EC, 0xE4DCC8],
}
CLOUDS = {"WINTER": 4, "SPRING": 3, "SUMMER": 1, "AUTUMN": 3}
# Water tint: clear in winter, greener with phytoplankton in summer, tea-colored
# with leaf tannins in autumn.
WATER_TINT = [
    (0x3A6EA8, 0.10), (0x3A6EA8, 0.05), (0x3A9A88, 0.08), (0x3A9A88, 0.12),
    (0x4A9A70, 0.18), (0x5A9A50, 0.25), (0x5A9A50, 0.32), (0x5A9A48, 0.36),
    (0x6A8A48, 0.30), (0x8A7A50, 0.28), (0x8A7A50, 0.22), (0x5A7AA0, 0.12),
]
# How far the water line drops (pixels) as the pond shrinks in the dry season.
DROP = [0, 0, 0, 0, 0, 1, 3, 5, 6, 4, 1, 0]

DECIDUOUS = {12: "bare", 1: "bare", 2: "bare", 3: "bud", 10: "turning", 11: "gold"}  # others: "leaf"
TYPHA = {12: "dead", 1: "dead", 2: "dead", 3: "shoots", 4: "young", 5: "green", 6: "flowering",
         7: "mature", 8: "mature", 9: "mature", 10: "yellowing", 11: "straw"}


@dataclass(frozen=True)
class Season:
    month: int

    @property
    def name(self) -> str:
        return SEASON_NAMES[self.month - 1]

    @property
    def hills(self) -> tuple:
        return HILLS[self.month - 1]

    @property
    def sky(self) -> list[int]:
        return SKIES[self.name]

    @property
    def clouds(self) -> int:
        return CLOUDS[self.name]

    @property
    def water_tint(self) -> tuple[int, float]:
        return WATER_TINT[self.month - 1]

    @property
    def drop(self) -> int:
        return DROP[self.month - 1]

    @property
    def deciduous(self) -> str:  # white poplar / willow on the far bank
        return DECIDUOUS.get(self.month, "leaf")

    @property
    def typha(self) -> str:  # reedmace, Typha domingensis / T. latifolia
        return TYPHA[self.month]

    def has(self, feature: str) -> bool:
        return self.month in FEATURES[feature]


FEATURES = {
    # White water lily, Nymphaea alba: leaves reach the surface in April, flowers June-September.
    "lily_pads": _months(4, 5, 6, 7, 8, 9, 10, 11),
    "lily_flowers": _months(6, 7, 8, 9),
    # Pond water-crowfoot, Ranunculus peltatus: floating leaves late winter, white flowers in spring.
    "crowfoot_leaves": _months(2, 3, 4, 5),
    "crowfoot_flowers": _months(3, 4, 5),
    # Duckweed, Lemna minor, and filamentous algae mats in the warm months.
    "duckweed": _months(6, 7, 8, 9, 10),
    "algae": _months(7, 8),
    # Pondweed, Potamogeton, grows up through the water column in the warm season.
    "pondweed": _months(5, 6, 7, 8, 9),
    # Fallen poplar leaves float in autumn and rot on the bottom over winter.
    "floating_leaves": _months(10, 11, 12),
    "leaf_litter": _months(10, 11, 12, 1, 2, 3),
    # Bank flowers: crown daisy (Glebionis coronaria), corn poppy (Papaver rhoeas),
    # autumn squill (Prospero autumnale) after the first rains.
    "daisies": _months(3, 4, 5),
    "poppies": _months(4, 5),
    "squill": _months(9, 10, 11),
    # Juncus flower clusters.
    "rush_flowers": _months(5, 6, 7, 8),
}


# ---------------------------------------------------------------- animals
@dataclass(frozen=True)
class Species:
    key: str
    name: str
    latin: str
    zone: str  # air, surface, film, water, bottom
    motion: str
    months: tuple  # abundance 0..3, Jan..Dec
    frames: tuple  # animation frames, each a list of rows, facing right
    colors: dict
    outline: bool = True
    bare: str = ""  # sprite chars drawn without outline (wings, thin legs)
    group: tuple = (1, 1)
    anchor: str = "center"  # center, bottom (rests on y0), top (hangs from y0)
    frame_every: int = 1


# Odonates in flight are drawn from above, wings spread: the classic arcade "X".
_DRAGONFLY_OPEN = [
    ".......vv.vv...",
    ".......wv.wv...",
    "......wwv.wwv..",
    "adadadadaTTTTEE",
    "......wwv.wwv..",
    ".......wv.wv...",
    ".......vv.vv...",
]
_DRAGONFLY_BEAT = [
    "...............",
    "...............",
    "......vvv.vvv..",
    "adadadadaTTTTEE",
    "......vvv.vvv..",
    "...............",
    "...............",
]
_DAMSELFLY_OPEN = ["......v.v..", "......wvwv.", "kbkkkkkkTTe", "......wvwv.", "......v.v.."]
_DAMSELFLY_BEAT = ["...........", "......vvvv.", "kbkkkkkkTTe", "......vvvv.", "..........."]
WING, VEIN = 0xF4FAFF, 0x8C9CB0

SPECIES = [
    # -- air (Odonata adults; none fly at night)
    Species("ischnura", "Iberian bluetail", "Ischnura graellsii", "air", "fly",
            (0, 1, 2, 3, 3, 3, 3, 3, 3, 2, 1, 0),
            (_DAMSELFLY_OPEN, _DAMSELFLY_BEAT),
            {"k": 0x24302C, "b": 0x40B8E8, "T": 0x50B0B0, "e": 0x2A8A90, "w": WING, "v": VEIN},
            outline=False, group=(1, 2)),
    Species("anax", "Emperor dragonfly", "Anax imperator", "air", "dart",
            (0, 0, 1, 2, 3, 3, 3, 3, 2, 1, 0, 0), (_DRAGONFLY_OPEN, _DRAGONFLY_BEAT),
            {"d": 0x1E3E7A, "a": 0x4A9AE8, "T": 0x6CBC4C, "E": 0x3C80D0, "w": WING, "v": VEIN}, outline=False),
    Species("crocothemis", "Scarlet darter", "Crocothemis erythraea", "air", "dart",
            (0, 0, 0, 1, 2, 3, 3, 3, 3, 2, 0, 0), (_DRAGONFLY_OPEN, _DRAGONFLY_BEAT),
            {"d": 0xA82020, "a": 0xE8402C, "T": 0xC84A3A, "E": 0xB83028, "w": WING, "v": VEIN}, outline=False),
    Species("sympetrum", "Common darter", "Sympetrum striolatum", "air", "dart",
            (1, 0, 0, 0, 0, 1, 2, 2, 3, 3, 3, 2), (_DRAGONFLY_OPEN, _DRAGONFLY_BEAT),
            {"d": 0x8A3A20, "a": 0xD06A34, "T": 0x9A6A3A, "E": 0x9A4A28, "w": WING, "v": VEIN}, outline=False),
    # -- surface film
    Species("gerris", "Pond skater", "Gerris lacustris", "surface", "skate",
            (0, 1, 2, 3, 3, 3, 3, 3, 3, 2, 1, 0),
            (["......bbbh.", "...ll.l..l.", ".dd..d....d"],),
            {"b": 0x2E2A20, "h": 0x2E2A20, "l": 0x4A4436, "d": 0xFFFFFF},
            outline=False, group=(1, 3), anchor="bottom"),
    Species("culex", "Mosquito larvae", "Culex pipiens", "film", "hang",
            (0, 0, 1, 2, 3, 3, 3, 3, 2, 1, 0, 0),
            (["s..", ".b.", ".b.", "..h"], ["s..", ".b.", "b..", "h.."]),
            {"s": 0x2A2A20, "b": 0x5A5A44, "h": 0x3A3A2A},
            outline=False, group=(2, 4), anchor="top", frame_every=3),
    Species("notonecta", "Backswimmer", "Notonecta glauca", "film", "backswim",
            (1, 1, 2, 2, 3, 3, 3, 3, 3, 2, 2, 1),
            (["l......", ".hhhhhR", "wwwwwwR", "l......"],),
            {"h": 0x4A4A38, "w": 0xE4E0C8, "R": 0xC83828, "l": 0xB8B090}, bare="l", group=(1, 2)),
    # -- open water
    Species("dytiscus", "Great diving beetle", "Dytiscus circumflexus", "water", "dive",
            (1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1),
            ([".dDDDd.", "dDDDDDh", ".yyyyy.", "l.l.l.."], [".dDDDd.", "dDDDDDh", ".yyyyy.", ".l.l.l."]),
            {"D": 0x3E4A2A, "d": 0x2A3418, "h": 0x2A3418, "y": 0xD8B040, "l": 0x6A5A30}, bare="l", frame_every=2),
    Species("sigara", "Lesser water boatman", "Sigara lateralis", "water", "paddle",
            (2, 2, 2, 2, 2, 2, 2, 3, 3, 3, 2, 2),
            (["bBbBh", "l..l."], ["bBbBh", ".l..l"]),
            {"b": 0x6A5A3A, "B": 0xA89A68, "h": 0x5A4A30, "l": 0x8A7A50}, bare="l", group=(2, 3), frame_every=2),
    Species("daphnia", "Water fleas", "Daphnia magna", "water", "hop",
            (1, 2, 3, 3, 3, 2, 1, 1, 1, 2, 2, 1),
            (["eb", "bB"],),
            {"e": 0x2A1A18, "b": 0xD89A70, "B": 0xF0C8A0}, outline=False, group=(4, 8)),
    Species("triturus", "Marbled newt", "Triturus marmoratus", "water", "newt",
            (2, 3, 3, 3, 1, 0, 0, 0, 0, 0, 1, 2),
            (["........cCcCcC...", "tt..GgKGgKGgKGGh.", ".ttGgKGgKgGgGGGhe", "....bbwbbwbbbbb..", "......l.....l...."],
             ["........cCcCcC...", "....GgKGgKGgKGGh.", "tttGgKGgKgGgGGGhe", "....bbwbbwbbbbb..", ".....l.....l....."]),
            {"c": 0x1E241A, "C": 0xC8C8B0, "G": 0x5AA040, "g": 0x3A7A30, "K": 0x1A2A18, "h": 0x5AA040,
             "e": 0xD8A030, "t": 0x4A8A38, "b": 0x3A3430, "w": 0xE8E8E0, "l": 0x4A8A38},
            bare="l", frame_every=4),
    # Breeds from autumn to spring; adults linger in water that persists through summer.
    Species("pleurodeles", "Iberian ribbed newt", "Pleurodeles waltl", "water", "newt",
            (2, 3, 3, 3, 2, 1, 1, 1, 1, 2, 2, 2),
            (["......gGGgGGgGGh..", "tt..GgDGGgDGgGGGhe", ".ttGGoGGoGGoGGGhh.", "....yyyyyyyyyyy...", ".....l......l....."],
             ["......gGGgGGgGGh..", "....GgDGGgDGgGGGhe", "tttGGoGGoGGoGGGhh.", "....yyyyyyyyyyy...", "......l......l...."]),
            {"G": 0x7A7A5A, "g": 0x5A5A44, "D": 0x34342A, "o": 0xE8902C, "h": 0x6E6E52, "e": 0xC8A048,
             "t": 0x6A6A50, "y": 0xB8AC78, "l": 0x6A6A50},
            bare="l", frame_every=4),
    # -- bottom
    Species("caddis", "Caddisfly larva", "Limnephilidae", "bottom", "crawl",
            (3, 3, 3, 2, 1, 0, 0, 0, 1, 2, 3, 3),
            (["cCcCcC..", "CcCcCcHl", ".....l.l"], ["cCcCcC..", "CcCcCcHl", "......l."]),
            {"c": 0x7A5A34, "C": 0xA88A5A, "H": 0x3A2A18, "l": 0xC8A870},
            bare="l", group=(1, 2), anchor="bottom", frame_every=4),
    Species("anax_nymph", "Dragonfly nymph", "Anax imperator", "bottom", "stalk",
            (2,) * 12,
            (["..GgGgGgEE", "gGgGgGgGGE", "..l..l..l."],),
            {"G": 0x7A8A44, "g": 0x56662E, "E": 0xA8B060, "l": 0x56662E}, bare="l", anchor="bottom"),
    Species("damsel_nymph", "Damselfly nymph", "Ischnura graellsii", "bottom", "stalk",
            (2, 2, 3, 3, 2, 2, 2, 2, 2, 2, 2, 2),
            (["L.........", "LLbbbbbbHH", "L..l.l.l.."],),
            {"L": 0xB8D088, "b": 0x7A9A50, "H": 0x5A7A38, "l": 0x5A7A38}, bare="lL", anchor="bottom"),
    Species("planorbarius", "Great ramshorn snail", "Planorbarius corneus", "bottom", "creep",
            (1, 1, 2, 2, 3, 3, 3, 3, 2, 2, 1, 1),
            ([".sss..", "sSaSs.", "saSas.", ".sss.t", "fffff."],),
            {"s": 0x6A3A1E, "S": 0xA0602E, "a": 0x4A2414, "f": 0x6A5A48, "t": 0x6A5A48},
            group=(1, 2), anchor="bottom"),
]
BY_KEY = {s.key: s for s in SPECIES}
SLOTS = {"air": (0, 2), "surface": (0, 1), "film": (0, 1), "water": (1, 3), "bottom": (1, 3)}


@dataclass
class Critter:
    species: Species
    x0: float
    y0: float
    phase: float
    amp: float
    speed: int = 1
    jitter: tuple = field(default=(0, 0))


def season_for(day: date) -> Season:
    return Season(day.month)


def assemble(day: date, seed: str, night: bool, surface: int, bottom: int, width: int) -> list[Critter]:
    """Pick today's pond community: a weighted, seeded draw from species active this month."""
    rng = random.Random(f"{seed}:{day.isoformat()}")
    m = day.month - 1
    out: list[Critter] = []
    for zone, (lo, hi) in SLOTS.items():
        if zone == "air" and night:
            continue  # odonates roost at night
        pool = [s for s in SPECIES if s.zone == zone and s.months[m] > 0]
        for _ in range(min(len(pool), rng.randint(lo, hi))):
            sp = rng.choices(pool, weights=[s.months[m] for s in pool])[0]
            pool.remove(sp)
            count = max(1, round(rng.randint(*sp.group) * (0.5 + sp.months[m] / 6)))
            out.extend(_spawn(sp, count, rng, surface, bottom, width))
    return out


def _spawn(sp: Species, count: int, rng: random.Random, surface: int, bottom: int, width: int) -> list[Critter]:
    zone = sp.zone
    if zone == "air":
        cx, cy = rng.uniform(24, width - 24), rng.uniform(14, surface - 14)
    elif zone in ("surface", "film"):
        cx = rng.choice((rng.uniform(6, 40), rng.uniform(88, width - 10)))
        cy = surface
    elif zone == "water":
        cx, cy = rng.uniform(18, width - 18), rng.uniform(surface + 8, bottom - 10)
    else:
        cx, cy = rng.uniform(8, width - 12), bottom - 1
    crew = []
    for i in range(count):
        jx = rng.uniform(-8, 8) if count > 1 else 0
        jy = rng.uniform(-4, 4) if count > 1 and zone in ("water", "air") else 0
        crew.append(Critter(sp, cx + jx, cy + jy, rng.random(), rng.uniform(6, 16) if zone != "air" else rng.uniform(16, 34),
                            speed=rng.choice((1, 1, 2)) if zone == "air" else 1))
    return crew


def place(c: Critter, t: float, surface: int, bottom: int) -> tuple[float, float, bool]:
    """Position of a critter at loop time t in [0, 1); every path loops seamlessly."""
    ph = c.phase * TAU
    k = c.speed
    m = c.species.motion
    if m == "fly":
        a = TAU * t * k + ph
        return c.x0 + c.amp * math.cos(a), c.y0 + 4 * math.sin(2 * a), -math.sin(a) > 0
    if m == "dart":  # hover, then dash: the warp stops time three times per loop
        s = t - math.sin(TAU * t * 3) / (TAU * 3)
        a = TAU * s * k + ph
        return c.x0 + c.amp * math.cos(a), c.y0 + 6 * math.sin(2 * a), -math.sin(a) >= 0
    if m == "skate":  # glide in strides, out and back
        u = (t + c.phase) % 1 * 8
        n, e = int(u), u - int(u)
        e = 1 - (1 - e) ** 3
        s = (n + e) / 4 if n < 4 else 2 - (n + e) / 4
        return c.x0 + c.amp * s, surface, n < 4
    if m == "hang":
        wr = max(0.0, math.sin(TAU * t + ph)) ** 6
        return c.x0 + round(math.sin(TAU * t * 2 + ph) * 0.6), surface + 1 + 4 * wr, True
    if m == "backswim":
        d = max(0.0, math.sin(TAU * t + ph)) ** 2
        return c.x0 + 8 * math.sin(TAU * t + ph), surface + 2 + 16 * d, math.cos(TAU * t + ph) > 0
    if m == "dive":  # sweep down to forage, then back up to the surface for air
        a = TAU * t + ph
        lo, hi = surface + 3, bottom - 12
        return c.x0 + c.amp * math.cos(a), lo + (hi - lo) * (0.5 + 0.5 * math.sin(a)), -math.sin(a) > 0
    if m == "paddle":
        a = TAU * t * 2 + ph
        return c.x0 + c.amp * math.sin(a), bottom - 6 + 2 * math.sin(TAU * t * 3 + ph), math.cos(a) > 0
    if m == "hop":  # sink slowly, flick back up
        u = (t * 3 + c.phase) % 1
        return c.x0 + 1.5 * math.sin(TAU * t + ph), c.y0 - 3 + 5 * u, True
    if m == "newt":
        a = TAU * t + ph
        return c.x0 + c.amp * 1.4 * math.cos(a), bottom - 9 + 3 * math.sin(2 * a), -math.sin(a) > 0
    if m == "crawl":
        a = TAU * t + ph
        return c.x0 + c.amp * 0.4 * math.sin(a), c.y0, math.cos(a) > 0
    if m == "stalk":
        a = TAU * t + ph
        return c.x0 + 2 * math.sin(a), c.y0, math.cos(a + 0.5) > 0
    if m == "creep":
        a = TAU * t + ph
        return c.x0 + 1.5 * math.sin(a), c.y0, math.cos(a) > 0
    return c.x0, c.y0, True


def census(critters: list[Critter]) -> list[dict]:
    seen: dict[str, dict] = {}
    for c in critters:
        s = c.species
        seen.setdefault(s.key, {"name": s.name, "latin": s.latin, "count": 0})["count"] += 1
    return list(seen.values())
