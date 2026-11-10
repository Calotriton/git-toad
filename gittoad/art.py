"""16-bit style pond scene and the toad's sprites, frame by frame."""

from __future__ import annotations

import math
import random

from .font import text_pixels, text_width
from .life import STAGES, Toad
from .pond import Season, assemble, census, place, season_for
from .sky import Sky, moon_phase

W, H = 128, 96  # the pond scene
STATUS_H = 13  # dialogue box under the scene
TYPE_FRAMES = 20  # frames it takes to type the status out
SURFACE = 40  # water line
BOTTOM = 86  # pond floor
FRAMES = 48
DELAY_CS = 10
TAU = math.tau

OUTLINE = 0x181425
WHITE = 0xF8F8F8
BAYER = (0, 8, 2, 10, 12, 4, 14, 6, 3, 11, 1, 9, 15, 7, 13, 5)
N4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


# ---------------------------------------------------------------- color utils
def mix(a: int, b: int, f: float) -> int:
    out = 0
    for shift in (16, 8, 0):
        ca, cb = (a >> shift) & 255, (b >> shift) & 255
        out |= round(ca + (cb - ca) * f) << shift
    return out


def bayer(x: int, y: int) -> float:
    return (BAYER[(y & 3) * 4 + (x & 3)] + 0.5) / 16


def gradient(colors: list[int], t: float, x: int, y: int, edge: float = 0.45) -> int:
    """Banded gradient with ordered dithering on the band edges, like SNES skies."""
    n = len(colors) - 1
    pos = max(0.0, min(1.0, t)) * n
    i = min(int(pos), n - 1)
    f = pos - i
    return colors[i + 1] if (f - (1 - edge)) / edge > bayer(x, y) else colors[i]


# ---------------------------------------------------------------- themes
DAY = {
    "sky": [0x3C6FD8, 0x5890F0, 0x78B0F8, 0x9CD0F8, 0xC4E8F8],
    "far": 0x6EAE9A, "far_hi": 0x8CC8AE,
    "near": 0x3E8A4C, "near_hi": 0x5CA85A, "tree": 0x2E6E3E, "tree_hi": 0x4E9A4A,
    "water": [0x4AA8E0, 0x3488CC, 0x286CB0, 0x205694, 0x184078],
    "surface": 0xBCEAF8, "shimmer": 0xF8FFFF, "caustic": 0x6CC4F0,
    "mud": [0x7A5E3C, 0x5E4428, 0x46321E], "pebble": 0x9A8A70, "pebble_dk": 0x6A5A44,
    "plant": 0x2E7A3A, "plant_hi": 0x52A84A,
    "reed": 0x4E8A2C, "reed_hi": 0x78B040, "cattail": 0x6E3E22, "cattail_hi": 0x9A6036,
    "pad": 0x3E9A3A, "pad_hi": 0x6CC85A, "pad_dk": 0x24602A,
    "petal": 0xF890B8, "petal_hi": 0xFFD8E8, "petal_dk": 0xC85888, "pistil": 0xF8D040,
    "cloud": 0xFFFFFF, "cloud_sh": 0xD8ECF8, "cloud_dk": 0xB0D4F0,
    "bubble": 0xD8F6FF, "bubble_dk": 0x8CD0F0,
}

NIGHT_INK = 0x0C1238


def _night(day: dict) -> dict:
    t = {k: (mix(v, NIGHT_INK, 0.55) if isinstance(v, int) else [mix(c, NIGHT_INK, 0.55) for c in v]) for k, v in day.items()}
    t["sky"] = [0x080A24, 0x0E1238, 0x161C4C, 0x1E285E, 0x2A3870]
    t["water"] = [0x1E3C6C, 0x18325E, 0x132850, 0x0F1F42, 0x0A1634]
    t["surface"] = 0x6C88B8
    t["shimmer"] = 0xD8E4F8
    t["caustic"] = 0x2A4C80
    return t


NIGHT = _night(DAY)


def make_theme(season: Season, night: bool) -> dict:
    t = dict(DAY)
    t["sky"] = list(season.sky)
    t["near"], t["near_hi"], t["far"], t["far_hi"] = season.hills
    tint, f = season.water_tint
    t["water"] = [mix(c, tint, f) for c in DAY["water"]]
    t["caustic"] = mix(DAY["caustic"], tint, f)
    return _night(t) if night else t

SKINS = {
    "meadow": {"H": 0xD0F890, "L": 0x88D850, "G": 0x48A838, "D": 0x286830, "Y": 0xF8F0B8, "y": 0xD8C880},
    "golden": {"H": 0xFFF4B0, "L": 0xFFD448, "G": 0xE09A1E, "D": 0x9A5A10, "Y": 0xFFF6DC, "y": 0xE8D29A},
    "azure": {"H": 0xB0ECFF, "L": 0x50B8F0, "G": 0x2070D0, "D": 0x16408A, "Y": 0xD8ECFF, "y": 0x98B4E0},
    "crimson": {"H": 0xFFC0A8, "L": 0xFF6E4C, "G": 0xD0302A, "D": 0x7A1420, "Y": 0xFFE4C4, "y": 0xE0B48C},
    "violet": {"H": 0xECD0FF, "L": 0xB47EEC, "G": 0x7A44C2, "D": 0x45207A, "Y": 0xF6E8FF, "y": 0xCFB2E8},
}
TADPOLE = {"H": 0xB0A470, "L": 0x7E7048, "G": 0x524530, "D": 0x30281C, "Y": 0xC8B880, "y": 0x9A8A5C}
EYE = {"W": 0xFFFFFF, "P": OUTLINE, "o": OUTLINE}


# ---------------------------------------------------------------- canvas
class Canvas:
    def __init__(self, px: list[int] | None = None):
        self.px = px if px is not None else [0] * (W * H)

    def copy(self) -> "Canvas":
        return Canvas(self.px[:])

    def set(self, x: int, y: int, c: int) -> None:
        if 0 <= x < W and 0 <= y < H:
            self.px[y * W + x] = c

    def get(self, x: int, y: int) -> int:
        return self.px[y * W + x] if 0 <= x < W and 0 <= y < H else 0

    def blit(self, sprite: dict, ox: int, oy: int, flip: bool = False, tone=None) -> None:
        for (x, y), c in sprite.items():
            self.set(ox + (-x if flip else x), oy + y, tone(c) if tone else c)


def outlined(body: dict, color: int = OUTLINE) -> dict:
    out = {}
    for x, y in body:
        for dx, dy in N4:
            if (x + dx, y + dy) not in body:
                out[(x + dx, y + dy)] = color
    out.update(body)
    return out


def ellipse(rx: float, ry: float):
    for y in range(-math.ceil(ry), math.ceil(ry) + 1):
        for x in range(-math.ceil(rx), math.ceil(rx) + 1):
            if (x / (rx + 0.4)) ** 2 + (y / (ry + 0.4)) ** 2 <= 1:
                yield x, y


# ---------------------------------------------------------------- frog sprites
# Left half of a front-facing frog; mirrored at draw time. Fill only: the dark
# outline is added automatically. Digits are spot slots that streaks unlock.
_HEAD = [
    ".....LLLL.......",
    "....LHHLLL......",
    "....LWWWWL......",
    "...GWWPPWWG.....",
    "...GWWPPWWGLLLLL",
    "...GLWWWWLGGGGGG",
    "..GGGLLLLGGGGGGG",
    "..LGGGGGGGGGG11G",
    "..GGGGGGGGGGG11G",
    "..DoGGGGGGGGGGGG",
    "..DDoooooooooooo",
]
FROG_SIT = _HEAD + [
    "..DGGYYYYYYYYYYY",
    ".LGDGGYYYYYYYYYY",
    "LGG22DGYYYYYYYYY",
    "GGG22DLGYYYYYYYY",
    "GGGGGDLGyYYYYYYY",
    "DGGGGDLGyyYYYYYY",
    "DDGGDLLGGyyyyyyy",
    ".DDDLLLLGGyyyyyy",
    "LLLLLL..LLL.....",
]
FROG_JUMP = _HEAD + [
    "...DGYYYYYYYYYYY",
    ".LLDGYYYYYYYYYYY",
    "LL.DGYYYYYYYYYYY",
    "...DGyYYYYYYYYYY",
    "...DGGyyyyyyyyyy",
    "...LG33Dyyyyyyy.",
    "...LG33D........",
    "....LGGD........",
    "....LGGD........",
    "....LGD.........",
    "...LLGD.........",
    "..LLLLLL........",
]
# Moss tuft with a little mushroom, growing between an old toad's eyes.
# Ten columns wide (x -5..4); the bottom row rests on top of the head.
TUFT = [
    ".rRRr.....",
    "rRwRRr....",
    "RRRRwR....",
    "..ss......",
    ".mss.M.mM.",
    "mMmMmMMmMm",
]
TUFT_COLORS = {"r": 0xA82E2A, "R": 0xE04A38, "w": 0xFFF0D8, "s": 0xE8DCC0, "m": 0x4E9A34, "M": 0x9CD45A}
# Old toads: the chosen skin weathered toward earthy browns, with gold eyes.
TOAD_EARTH = {"H": 0xD8C890, "L": 0xB09058, "G": 0x8A6A3A, "D": 0x4A3420, "Y": 0xE8D8B0, "y": 0xB8A070}
IRIS, IRIS_DK = 0xE8B030, 0xB07818


def parse(rows: list[str], mirror: bool = True) -> dict:
    full = [r + r[::-1] for r in rows] if mirror else rows
    w, h = len(full[0]), len(full)
    return {(c - w // 2, r - h): ch for r, row in enumerate(full) for c, ch in enumerate(row) if ch != "."}


SIT = parse(FROG_SIT)
JUMP = parse(FROG_JUMP)
SIT_H = len(FROG_SIT)
JUMP_H = len(FROG_JUMP)
def toad_skin(skin: dict) -> dict:
    weight = {"Y": 0.45, "y": 0.45}
    return {k: mix(v, TOAD_EARTH[k], weight.get(k, 0.7)) for k, v in skin.items()}


def tuft() -> dict:
    body = {(c - 5, r - len(TUFT)): TUFT_COLORS[ch] for r, row in enumerate(TUFT) for c, ch in enumerate(row) if ch != "."}
    # No outline under the moss: it should sit flush on the head.
    return {p: c for p, c in outlined(body).items() if p[1] < 0}


def _is_wart(x: int, row: int) -> bool:
    return ((x * 73856093) ^ (row * 19349663)) % 11 == 0


def frog_sprite(template: dict, skin: dict, spot_colors: list[int], spots: int, look: int, closed: bool,
                old: bool = False) -> dict:
    top = min(y for _, y in template)
    eye = {p for p, ch in template.items() if ch in "WP"}
    pupils = {(x + look, y) for (x, y), ch in template.items() if ch == "P"} & eye
    body = {}
    for (x, y), ch in template.items():
        row = y - top
        if (x, y) in eye:
            if closed:
                ch = "o" if row == 4 else "L"
            elif old and row == 2:
                ch = "G"  # heavy upper lid
            elif old and row == 3:
                ch = "D"
            elif (x, y) in pupils:
                ch = "P"
            elif old:
                body[(x, y)] = IRIS if row == 4 else IRIS_DK
                continue
            else:
                ch = "W"
        if ch.isdigit():
            slot = int(ch)
            body[(x, y)] = spot_colors[(slot - 1) % len(spot_colors)] if slot <= spots else skin["G"]
        else:
            body[(x, y)] = skin.get(ch) or EYE[ch]
    if old:
        for (x, y), ch in template.items():
            row = y - top
            if ch in "GLD" and row >= 6 and _is_wart(x, row):
                body[(x, y)] = skin["H"]
                if template.get((x, y + 1), ".") in "GLD":
                    body[(x, y + 1)] = skin["D"]
    return outlined(body)


# ---------------------------------------------------------------- swimmers
def swimmer(stage: int, phase: float, skin: dict, spot_colors: list[int], spots: int, mouth_open: bool) -> dict:
    """Side view tadpole (stage 1), polliwog with hind legs (2) or froglet (3), facing right."""
    pal = TADPOLE if stage < 3 else skin
    rx, ry, tail_len = {1: (5, 4, 13), 2: (6, 4, 13), 3: (7, 5, 7)}[stage]
    fin = mix(pal["L"], 0x9CD8F0, 0.55)
    core = pal["G"] if stage < 3 else pal["D"]
    body: dict = {}
    for x, y in ellipse(rx, ry):
        if y <= -ry + 1:
            c = pal["L"]
        elif y >= ry - 1:
            c = pal["Y"]
        elif x <= -rx + 1:
            c = pal["D"]
        else:
            c = pal["G"]
        body[(x, y)] = c
    for hx in (0, 1):
        if (hx, -ry + 1) in body:
            body[(hx, -ry + 1)] = pal["H"]

    # legs
    kick = round(math.sin(phase * 2))
    if stage >= 2:
        for p in [(-rx + 2, ry), (-rx + 1, ry + 1), (-rx, ry + 1), (-rx - 1 + kick, ry + 2), (-rx - 2 + kick, ry + 2)]:
            body[p] = pal["L"] if stage == 3 else pal["G"]
    if stage == 3:
        for p in [(rx - 3, ry), (rx - 3, ry + 1), (rx - 2, ry + 2), (rx - 1, ry + 2)]:
            body[p] = pal["L"]

    # eye
    ex = rx - 3
    ey = -1 if stage < 3 else -ry + 1
    if stage == 3:
        for p in [(ex - 1, ey - 2), (ex, ey - 2), (ex + 1, ey - 2), (ex, ey - 3)]:
            body[p] = pal["L"]
    for p in [(ex, ey - 1), (ex + 1, ey - 1), (ex, ey)]:
        body[p] = EYE["W"]
    body[(ex + 1, ey)] = OUTLINE

    # mouth
    if mouth_open:
        body.pop((rx, 1), None)
        body.pop((rx, 0), None)
        body[(rx - 1, 1)] = OUTLINE
    else:
        body[(rx - 1, 1)] = pal["D"]

    # tail
    tail_pts = []
    for s in range(tail_len + 1):
        u = s / tail_len
        x = -rx + 1 - s
        yc = math.sin(phase - s * 0.5) * (0.3 + 1.7 * u)
        half = (1 - u) * (2.2 if stage < 3 else 2.6) + 0.5
        inner = 0.5 if stage < 3 else 0.9
        for y in range(round(yc - half), round(yc + half) + 1):
            if (x, y) not in body:
                body[(x, y)] = core if abs(y - yc) <= inner + 0.2 else fin
        tail_pts.append((x, round(yc)))

    # streak speckles, colored by top languages
    slots = [(-1, -1), (-3, 1), (1, 1), tail_pts[3], tail_pts[6], tail_pts[min(9, tail_len - 1)]]
    for i in range(spots * 2):
        x, y = slots[i]
        if (x, y) in body:
            body[(x, y)] = spot_colors[i % len(spot_colors)]
    return outlined(body)


# ---------------------------------------------------------------- small props
def egg(embryo: int) -> dict:
    jelly, rim, deep = 0xD8F2F8, 0x9AD2E4, 0x5E9EC0
    body = {}
    for x, y in ellipse(2.2, 2.2):
        body[(x, y)] = jelly if y < 0 or (x < 0 and y == 0) else rim
    body[(-1, -1)] = 0xFFFFFF
    curl = [[(0, 0), (1, 0)], [(0, 0), (0, 1)], [(0, 0), (-1, 0)], [(0, 0), (1, 1)]][embryo % 4]
    for p in curl:
        body[p] = OUTLINE
    return outlined(body, deep)


def fly(flap: int) -> dict:
    body = {(0, 0): 0x6A6A8A, (1, 0): 0x302838, (0, 1): 0x302838, (1, 1): 0x302838, (2, 0): 0xE83850}
    wing = 0xE8F8FF
    if flap:
        body.update({(-1, -1): wing, (0, -1): wing, (1, -1): wing})
    else:
        body.update({(-1, 0): wing, (-2, 0): wing, (-1, -1): wing})
    return body


def moth(flap: int) -> dict:
    body = {(0, 0): 0x8A7A68, (1, 0): 0x6A5A48, (2, 0): 0x6A5A48, (3, -1): 0xC8B8A0, (3, 0): 0x5A4A38}
    wing, edge = 0xD8CCB4, 0xA89880
    if flap:
        body.update({(0, -1): wing, (1, -1): wing, (1, -2): wing, (2, -2): edge, (0, -2): edge})
    else:
        body.update({(-1, 0): wing, (-1, 1): wing, (0, 1): wing, (1, 1): edge, (-2, 1): edge})
    return body


def moon_sprite(phase: float) -> dict:
    """The moon as it really is tonight; the dark side faintly lit by earthshine."""
    r = 5
    lit_c, shade_c, crater, dark = 0xF8F0C8, 0xD8CC98, 0xC8BC88, 0x2A3058
    px = {}
    c = math.cos(TAU * phase)
    for x, y in ellipse(r, r):
        w = math.sqrt(max(0.0, 1 - (y / (r + 0.4)) ** 2))
        nx = x / (r + 0.4)
        lit = nx > w * c if phase < 0.5 else nx < -w * c
        if lit:
            px[(x, y)] = crater if (x, y) in ((-2, -1), (1, 2), (2, -2)) else lit_c if x + y < 3 else shade_c
        else:
            px[(x, y)] = dark
    return px


def sparkle(size: int) -> dict:
    px = {(0, 0): 0xFFFFFF}
    for r in range(1, size + 1):
        c = 0xFFF0A0 if r == 1 else 0xF8C838
        for dx, dy in N4:
            px[(dx * r, dy * r)] = c
    return px


NOTE = ["..##", "..#.", "..#.", "###.", "##.."]


def glyph_sprite(rows: list[str], color: int) -> dict:
    return outlined({(c, r): color for r, row in enumerate(rows) for c, ch in enumerate(row) if ch == "#"})


def text_sprite(text: str, color: int) -> dict:
    return outlined({p: color for p in text_pixels(text)})


# Young Nymphaea leaves come up reddish in April; they yellow and brown in autumn.
PAD_AGE = {4: (0x8A4A3A, 0.35), 10: (0xB0A040, 0.25), 11: (0xA07A3A, 0.5)}


def lily_pad(rx: int, month: int) -> dict:
    t = DAY
    tint, f = PAD_AGE.get(month, (0, 0.0))
    hi, mid, dk = (mix(t[k], tint, f) for k in ("pad_hi", "pad", "pad_dk"))
    body = {}
    for x in range(-rx, rx + 1):
        for y in range(-2, 2):
            if (x / (rx + 0.5)) ** 2 + ((y + 0.5) / 2.2) ** 2 <= 1:
                body[(x, y)] = hi if y == -2 else mid if y < 1 else dk
    for p in [(rx // 3, -2), (rx // 3 + 1, -1)]:
        body[p] = dk
    return outlined(body, 0x1A4020)


def flower() -> dict:
    """White water lily, Nymphaea alba: the native one is white, not pink."""
    rows = [".W.W.W.", "WwWwWwW", "wWWyWWw", ".wwwww."]
    cmap = {"W": 0xFFFFFF, "w": 0xC8D4E0, "y": 0xF8D040}
    return outlined({(c - 3, r - 4): cmap[ch] for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != "."})


UNDERWATER_OUTLINE = 0x102038
_CRITTER_CACHE: dict = {}


def critter_sprite(sp, index: int) -> dict:
    key = (sp.key, index)
    if key not in _CRITTER_CACHE:
        rows = sp.frames[index]
        h, w = len(rows), len(rows[0])
        oy = {"center": -(h // 2), "bottom": -(h - 1), "top": 0}[sp.anchor]
        solid, bare = {}, {}
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch != ".":
                    (bare if ch in sp.bare else solid)[(c - w // 2, r + oy)] = sp.colors[ch]
        if sp.outline:
            solid = outlined(solid, OUTLINE if sp.zone == "air" else UNDERWATER_OUTLINE)
        solid.update(bare)
        _CRITTER_CACHE[key] = solid
    return _CRITTER_CACHE[key]


def cloud(circles: list[tuple[int, int, float]]) -> dict:
    t = DAY
    px = {}
    for cx, cy, r in circles:
        for x, y in ellipse(r, r * 0.8):
            px[(cx + x, cy + y)] = 1
    bottom = max(y for _, y in px)
    return {
        (x, y): t["cloud_dk"] if y >= bottom - 1 else t["cloud_sh"] if y >= bottom - 3 else t["cloud"]
        for (x, y) in px
    }


# ---------------------------------------------------------------- the scene
HORIZON = 40  # where the banks meet the water at full level
# Far-bank trees: holm oaks (Quercus ilex) stay evergreen; white poplars (Populus alba) turn and drop.
TREES = [(30, 4, "poplar"), (38, 3, "oak"), (74, 4, "poplar"), (82, 5, "oak"), (122, 4, "poplar")]
SEASON_INK = {"WINTER": 0xC8E0F8, "SPRING": 0xB8F088, "SUMMER": 0xF8D878, "AUTUMN": 0xF0A050}


class Scene:
    def __init__(self, toad: Toad, skin: str = "meadow", hud: bool = True, day=None, sky: Sky | None = None):
        self.toad = toad
        self.day = day or toad.day
        self.season = season_for(self.day)
        self.month = self.season.month
        # Night falls for real when a location is known, and always when the toad is asleep.
        self.night = (sky is not None and sky.night) or toad.behavior == "sleep"
        self.moon = sky.moon if sky is not None else moon_phase(self.day)
        self.theme = make_theme(self.season, self.night)
        self.sy = HORIZON + self.season.drop  # water line, lower in the dry season
        self.lilies = self.season.has("lily_pads")
        self.skin = SKINS[skin]
        self.hud = hud
        self.rng = random.Random(toad.login)
        r = self.rng
        self.stars = [(r.randrange(W), r.randrange(28), r.random()) for _ in range(28)]
        self.bubbles = [(r.randrange(8, W - 8), r.random(), r.choice((1, 1, 2))) for _ in range(6)]
        self.chara = [(x, r.randrange(6, 12), r.random() * TAU) for x in (8, 15, 47, 90, 97, 118)]
        self.pondweed = [(x, r.random() * TAU) for x in (34, 106)]
        self.eggs = self._egg_cluster()
        self.critters = assemble(self.day, toad.login, self.night, self.sy, BOTTOM, W)
        self.base = self._base()

    @property
    def census(self) -> list[dict]:
        return census(self.critters)

    def tone(self, c: int) -> int:
        return mix(c, NIGHT_INK, 0.3) if self.night and c != OUTLINE else c

    def bg(self, c: int) -> int:
        return mix(c, NIGHT_INK, 0.55) if self.night else c

    # -- static backdrop
    def _base(self) -> Canvas:
        t, cv, season, sy = self.theme, Canvas(), self.season, self.sy
        for y in range(HORIZON):
            for x in range(W):
                cv.set(x, y, gradient(t["sky"], y / (HORIZON - 1), x, y))
        if self.night:
            cv.blit(moon_sprite(self.moon), 94, 19)
        else:
            grey = 0.25 if season.name == "WINTER" else 0.0
            shapes = [((58, 12), [(0, 0, 4), (5, -2, 5), (11, 0, 4)]), ((100, 20), [(0, 0, 3), (5, -1, 4), (9, 0, 3)]),
                      ((18, 22), [(0, 0, 3), (4, -1, 3)]), ((84, 8), [(0, 0, 3), (5, -1, 4), (10, 0, 3), (14, 1, 2)])]
            for (cx, cy), circles in shapes[: season.clouds]:
                cv.blit({p: mix(c, 0x8A98B0, grey) for p, c in cloud(circles).items()}, cx, cy)
        for x in range(W):
            fy = int(28 + 2.5 * math.sin(x * 0.06 + 1.3) + 1.5 * math.sin(x * 0.15 + 0.4))
            for y in range(fy, HORIZON):
                cv.set(x, y, t["far_hi"] if y == fy else t["far"])
        for tx, r, kind in TREES:
            self._tree(cv, tx, r, kind)
        near_top = []
        for x in range(W):
            ny = int(35 + 1.5 * math.sin(x * 0.09 + 2.1) + 1.2 * math.sin(x * 0.21 + 1))
            near_top.append(ny)
            for y in range(ny, HORIZON):
                cv.set(x, y, t["near_hi"] if y == ny else t["near"])
        self._bank_flowers(cv, near_top)
        for y in range(HORIZON, sy):  # mud exposed by the summer drawdown
            for x in range(W):
                crack = (x + (y * 5) // 3) % 9 == 0 or (y - HORIZON) % 3 == 2 and (x * 7) % 11 < 2
                c = 0x4A3A28 if y == sy - 1 else 0x5E4A36 if crack else 0x86705A
                cv.set(x, y, self.bg(c))
        for y in range(sy, H):
            for x in range(W):
                cv.set(x, y, gradient(t["water"], (y - sy) / (BOTTOM - sy), x, y))
        tops = []
        for x in range(W):
            top = BOTTOM + round(1.2 * math.sin(x * 0.2) + 0.8 * math.sin(x * 0.07 + 1))
            tops.append(top)
            for y in range(top, H):
                cv.set(x, y, gradient(t["mud"], (y - top) / (H - top), x, y) if y > top else 0)
            cv.set(x, top, mix(t["mud"][0], 0xFFFFFF, 0.15))
        r = random.Random(7)
        for _ in range(18):
            x, y = r.randrange(W), r.randrange(BOTTOM + 2, H)
            cv.set(x, y, t["pebble"])
            cv.set(x + 1, y, t["pebble"])
            cv.set(x + 1, y + 1, t["pebble_dk"])
            cv.set(x, y + 1, t["pebble_dk"])
        if season.has("leaf_litter"):
            r = random.Random(11)
            for _ in range(14):
                x = r.randrange(W - 2)
                c = self.bg(r.choice((0xC07830, 0x9A5A28, 0xD8A040, 0x7A4A24)))
                cv.set(x, tops[x], c)
                cv.set(x + 1, tops[x], c)
                cv.set(x + 1, tops[x] - 1, c)
        return cv

    def _tree(self, cv: Canvas, tx: int, r: int, kind: str) -> None:
        ground, bg = 33, self.bg
        if kind == "oak":
            for x, y in ellipse(r, r):
                cv.set(tx + x, ground - r + y, bg(0x58783E if x + y < -1 else 0x3A5A32))
            return
        state = self.season.deciduous
        bark = bg(0x9A8E7C)
        for y in range(ground - 2 * r - 2, ground + 1):
            cv.set(tx, y, bark)
        if state in ("bare", "bud"):
            for k in range(3):
                yb = ground - 4 - k * 3
                for d in range(1, r - k // 2 + 1):
                    cv.set(tx - d, yb - d, bark)
                    cv.set(tx + d, yb - d + 1, bark)
        cy = ground - r - 2
        for x, y in ellipse(r - 1, r + 1):
            b = bayer(tx + x, cy + y)
            if state == "bare":
                continue
            if state == "bud":
                c = 0xA8D878 if b < 0.3 else None
            elif state == "leaf":
                c = 0x74BA54 if x + y < -1 else 0x4E9A3E
            elif state == "turning":
                c = 0xC8B038 if b < 0.5 else (0x74BA54 if x + y < -1 else 0x5A9A3E)
            else:  # gold
                c = None if b < 0.2 else 0xF4D460 if x + y < -1 else 0xE0B030
            if c is not None:
                cv.set(tx + x, cy + y, bg(c))

    def _bank_flowers(self, cv: Canvas, near_top: list[int]) -> None:
        r = random.Random(17)
        kinds = [(f, c) for f, c in (("daisies", 0xF8D838), ("poppies", 0xE02828), ("squill", 0xB088D8))
                 if self.season.has(f)]
        for feature, color in kinds:
            for _ in range(12):
                x = r.randrange(2, W - 2)
                y = r.randrange(near_top[x] + 1, HORIZON)
                cv.set(x, y, self.bg(color))
                if feature == "poppies" and r.random() < 0.5:
                    cv.set(x + 1, y, self.bg(0xB01818))

    def _egg_cluster(self) -> list[tuple[int, int, int]]:
        eggs = []
        for row in range(4):
            for col in range(5 - abs(row - 1)):
                x = 22 + col * 5 + (row % 2) * 2 + abs(row - 1) * 2
                eggs.append((x, 5 + row * 4, self.rng.randrange(4)))
        return eggs

    # -- animated layers
    def _water(self, cv: Canvas, f: int, t: float) -> None:
        th, sy = self.theme, self.sy
        shift = f // 3
        for x in range(W):
            cv.set(x, sy, th["shimmer"] if (x + shift) % 16 < 3 else th["surface"])
            if (x - shift) % 24 < 2:
                cv.set(x, sy + 2, th["surface"])
        for i, (y, length) in enumerate([(50, 4), (57, 3), (63, 5), (70, 3), (77, 4)]):
            x0 = (i * 37 + round(math.sin(TAU * t + i) * 3)) % W
            for k in range(length):
                cv.set((x0 + k) % W, y, th["caustic"])
        if self.night:
            for x, y, ph in self.stars:
                if cv.get(x, y) in th["sky"]:
                    lit = (f / FRAMES + ph) % 1 < 0.7
                    cv.set(x, y, 0xF8F8D8 if lit else 0x8890C0)

    def _plants(self, cv: Canvas, t: float) -> None:
        bg = self.bg
        # Stoneworts (Chara): whorled, grey-green, carpeting the bottom all year.
        for x0, h, ph in self.chara:
            for i in range(h):
                y = BOTTOM - i
                x = x0 + round(math.sin(TAU * t + ph + i * 0.3) * 1.2 * i / h)
                cv.set(x, y, bg(0x4E7E4A))
                if i % 3 == 1:
                    for dx, dy in ((-1, 0), (1, 0), (-2, 1), (2, 1)):
                        cv.set(x + dx, y + dy, bg(0x7AA868))
        # Pondweed (Potamogeton) rises toward the light in the warm months.
        if self.season.has("pondweed"):
            h = BOTTOM - self.sy - 8
            for x0, ph in self.pondweed:
                for i in range(h):
                    y = BOTTOM - i
                    x = x0 + round(math.sin(TAU * t + ph + i * 0.15) * 2.0 * i / h)
                    cv.set(x, y, bg(0x6A7024))
                    if i % 5 == 3:
                        side = 1 if (i // 5) % 2 else -1
                        for dx in (1, 2, 3):
                            cv.set(x + side * dx, y, bg(0x8A8A30))
                        cv.set(x + side * 2, y - 1, bg(0xA8A848))

    def _surface_plants(self, cv: Canvas, t: float) -> None:
        sy, season, bg = self.sy, self.season, self.bg
        if season.has("crowfoot_leaves"):  # Ranunculus peltatus
            for x0, x1 in ((6, 20), (86, 104)):
                for i, x in enumerate(range(x0, x1, 4)):
                    cv.set(x, sy, bg(0x4E9A40))
                    cv.set(x + 1, sy, bg(0x5AA048))
                    cv.set(x + 1, sy - 1, bg(0x7AC058))
                    if season.has("crowfoot_flowers") and i % 2 == 0:
                        fx = x + 2
                        cv.set(fx, sy - 2, bg(0xF8D040))
                        for dx, dy in N4:
                            cv.set(fx + dx, sy - 2 + dy, bg(0xFFFFFF))
        if season.has("duckweed"):  # Lemna minor
            for x in list(range(0, 24)) + list(range(100, W)):
                if bayer(x, sy) < 0.6:
                    cv.set(x, sy, bg(0x6AB838 if x % 3 else 0x4E9A30))
        if season.has("algae"):
            for x in range(40, 58):
                for y in (sy + 1, sy + 2):
                    if bayer(x, y) < 0.5 - (y - sy) * 0.15:
                        cv.set(x, y, bg(0x7AA040))
        if season.has("floating_leaves"):
            brown = self.month == 12
            for i, (x0, ph) in enumerate(((12, 0.1), (44, 0.5), (96, 0.3), (116, 0.8))):
                x = round(x0 + 3 * math.sin(TAU * (t + ph)))
                c = bg(0xA06030 if brown or i % 2 else 0xE0B030)
                for dx in (0, 1, 2):
                    cv.set(x + dx, sy, c)
                cv.set(x + 1, sy - 1, c)

    def _reeds(self, cv: Canvas, t: float) -> None:
        self._typha(cv, t)
        self._juncus(cv, t)

    def _typha(self, cv: Canvas, t: float) -> None:
        """Reedmace through the year: dead straw, new shoots, green, flowering, seed heads."""
        bg, sy, state = self.bg, self.sy, self.season.typha
        green, green_hi = 0x4E8A2C, 0x78B040
        straw, straw_hi = 0xBCA478, 0xD8C498
        stems = [(110, 14, 0.0, True), (114, 20, 1.3, True), (119, 11, 2.2, True), (123, 24, 0.7, False)]

        def stem(x0, top, ph, col, hi, head):
            for y in range(top, sy + 8):
                k = max(0, sy - y) / (sy - top)
                x = x0 + round(math.sin(TAU * t + ph) * 1.2 * k)
                under = y > sy
                cv.set(x, y, bg(mix(col, self.theme["water"][1], 0.5) if under else col))
                if not under and y % 3 == 0:
                    cv.set(x - 1, y, bg(hi))
            if not head:
                return
            x = x0 + round(math.sin(TAU * t + ph) * 1.2)
            if head == "flowering":
                for y in range(top, top + 3):
                    cv.set(x, y, bg(0xE0C860))  # male spike shedding pollen
                c1, c2, y0 = 0x6A6A34, 0x8A8A44, top + 3
            else:
                c1, c2, y0 = 0x6E3E22, 0x9A6036, top + 2
            for y in range(y0, y0 + 6):
                cv.set(x, y, bg(c1))
                cv.set(x + 1, y, bg(c2 if y < y0 + 2 else c1))
            if head == "fluff":
                for i, y in enumerate(range(y0, y0 + 6, 2)):
                    cv.set(x + (2 if i % 2 else -1), y, bg(0xF0E8D8))
            cv.set(x, top + 1, bg(col))

        if state in ("dead", "shoots", "young", "straw"):
            for x0, top, ph, has in stems:
                if has or state == "straw":
                    stem(x0, top, ph, straw, straw_hi, "fluff" if has else None)
            if state in ("shoots", "young"):
                frac = 0.35 if state == "shoots" else 0.7
                for x0, top, ph, _ in stems:
                    stem(x0 + 2, round(sy - (sy - top) * frac), ph + 0.5, green, green_hi, None)
        else:
            col, hi = (0xA8A040, 0xC8C060) if state == "yellowing" else (green, green_hi)
            head = None if state == "green" else "flowering" if state == "flowering" else "seed"
            for x0, top, ph, has in stems:
                stem(x0, top, ph, col, hi, head if has else None)

    def _juncus(self, cv: Canvas, t: float) -> None:
        """A clump of rushes (Juncus) on the left bank; evergreen, tips browning in summer."""
        bg, sy = self.bg, self.sy
        tip = 0xA89050 if self.month in (7, 8, 9) else 0x5A9A48
        base = sy + 4
        for i, (bx, top, lean) in enumerate([(3, 22, -2), (5, 18, -1), (6, 25, 0), (8, 20, 1), (10, 24, 2), (12, 28, 3)]):
            for y in range(top, base):
                k = (base - y) / (base - top)
                x = bx + round(lean * k + math.sin(TAU * t + i) * 0.8 * k)
                c = tip if y < top + 2 else 0x3E7A3A
                cv.set(x, y, bg(mix(c, self.theme["water"][1], 0.5) if y > sy else c))
            if self.season.has("rush_flowers") and i % 2 == 0:
                y = top + (base - top) // 4
                k = (base - y) / (base - top)
                x = bx + round(lean * k + math.sin(TAU * t + i) * 0.8 * k)
                cv.set(x + 1, y, bg(0x7A5A30))
                cv.set(x + 1, y + 1, bg(0x9A7A40))

    def _bubbles(self, cv: Canvas, t: float) -> None:
        th, sy = self.theme, self.sy
        for x0, ph, speed in self.bubbles:
            u = (t * speed + ph) % 1
            y = BOTTOM - 2 - round(u * (BOTTOM - sy - 4))
            x = x0 + round(math.sin(u * TAU * 2) * 1.5)
            if speed == 2:
                cv.set(x, y, th["bubble"])
            else:
                for dx, dy in N4:
                    cv.set(x + dx, y + dy, th["bubble_dk"])
                cv.set(x - 1, y - 1, th["bubble"])

    def _critters(self, cv: Canvas, f: int, t: float, zones: tuple) -> None:
        for c in self.critters:
            sp = c.species
            if sp.zone not in zones:
                continue
            x, y, right = place(c, t, self.sy, BOTTOM)
            sprite = critter_sprite(sp, (f // sp.frame_every) % len(sp.frames))
            cv.blit(sprite, round(x), round(y), flip=not right, tone=self.tone)

    @property
    def perch_y(self) -> int:
        """Where the frog sits: a lily pad in the growing season, a mossy rock otherwise."""
        return self.sy - 1 if self.lilies else self.sy - 4

    def _pads(self, cv: Canvas, dip: int = 0) -> None:
        tone, sy = self.tone, self.sy
        if self.lilies:
            cv.blit(lily_pad(8, self.month), 26, sy, tone=tone)
            if self.season.has("lily_flowers"):
                cv.blit(flower(), 25, sy - 1, tone=tone)
            cv.blit(lily_pad(17, self.month), 64, sy + dip, tone=tone)
            return
        r = random.Random(5)
        body = {}
        for x, y in ellipse(22, 7):
            py = y + 2
            c = 0xB4B0A0 if py <= -3 else 0x8A8678 if py <= 0 else 0x625E54
            if py <= -2 and r.random() < 0.35:
                c = r.choice((0x5A8A3A, 0x7AAA48))
            body[(x, py)] = c
        above = {p: c for p, c in body.items() if p[1] <= 0}
        for p, c in outlined(above).items():
            if p[1] <= 0:
                cv.set(64 + p[0], sy + p[1], tone(c))
        for (x, y), c in body.items():
            if y > 0:
                cv.set(64 + x, sy + y, tone(mix(c, self.theme["water"][0], 0.55)))

    def _hud(self, cv: Canvas) -> None:
        toad = self.toad
        label = f"LV{toad.stage} {toad.stage_name}"
        cv.blit(text_sprite("LV", 0xF8D848), 3, 3)
        cv.blit(text_sprite(label[2:], WHITE), 3 + text_width("LV") + 1, 3)
        bar_w = 34
        fill = round((bar_w - 2) * max(0.0, min(1.0, toad.progress)))
        for x in range(bar_w):
            for y in range(4):
                edge = x in (0, bar_w - 1) or y in (0, 3)
                c = OUTLINE if edge else (0x78E060 if y == 1 else 0x40B040) if x - 1 < fill else 0x283850
                cv.set(3 + x, 10 + y, c)
        count = f"{toad.total}"
        x = W - 3 - text_width(count)
        cv.blit(text_sprite(count, WHITE), x, 3)
        cv.blit(outlined(fly(1)), x - 6, 5)
        season = self.season.name
        cv.blit(text_sprite(season, SEASON_INK[season]), W - 3 - text_width(season), 10)

    # -- the creature
    def _spawn(self, cv: Canvas, f: int, t: float) -> None:
        excited = self.toad.behavior == "leap"
        for i, (x, dy0, emb) in enumerate(self.eggs):
            dy = round(math.sin(TAU * t * 2 + i * 0.9) * 0.7)
            wiggle = emb + (f // (2 if excited else 6)) + i
            cv.blit(egg(wiggle if (excited or i % 3 == 0) else emb), x, self.sy + dy0 + dy, tone=self.tone)
        if excited:
            self._sparkles(cv, f, 34, self.sy + 11, 14)

    def _swim(self, cv: Canvas, f: int, t: float) -> None:
        toad, b, sy = self.toad, self.toad.behavior, self.sy

        def path(u: float, laps: int, rx: float) -> tuple[float, float, bool]:
            a = TAU * u * laps
            x = 64 + rx * math.cos(a)
            y = 65 + 8 * math.sin(a) + 2 * math.sin(2 * a)
            return x, y, math.sin(a) < 0  # facing right on the upper path

        mouth = False
        if b == "sleep":
            x, y, right = 46, BOTTOM - 6, True
            phase = TAU * t
        elif b == "leap":
            x, y, right = path(t, 2, 46)
            phase = TAU * t * 16
            for k in range(1, 5):
                bx, by, _ = path(t - k * 0.025, 2, 46)
                if (f + k) % 3:
                    cv.set(round(bx), round(by) - k % 2, self.theme["bubble"])
            self._sparkles(cv, f, round(x), round(y), 10)
        else:
            x, y, right = path(t, 1, 38)
            phase = TAU * t * 8
            if b == "hunt":
                tc = 0.72
                cx, cy, cr = path(tc, 1, 38)
                mx = cx + (8 if cr else -8)
                if 0.1 <= t < tc:
                    u = (t - 0.1) / (tc - 0.1)
                    fx, fy = mx + math.sin(u * TAU * 2) * 2, sy + 2 + (cy - sy - 2) * u
                    flake = {(0, 0): 0x9AD848, (1, 0): 0x5AA830, (0, 1): 0x5AA830}
                    cv.blit(outlined(flake, 0x2A5A20), round(fx), round(fy))
                mouth = tc - 0.06 <= t <= tc + 0.04
        sprite = swimmer(toad.stage, phase, self.skin, toad.spot_colors, toad.spots, mouth)
        cv.blit(sprite, round(x), round(y), flip=not right, tone=self.tone)
        if b == "sleep":
            self._zzz(cv, t, round(x) + 6, round(y) - 6)

    def _frog(self, cv: Canvas, f: int, t: float) -> None:
        toad, b, skin = self.toad, self.toad.behavior, self.skin
        fx, fy = 64, self.perch_y
        template, closed, look, sac, dip, oy = SIT, False, 0, 0.0, 0, 0
        tongue = None
        fly_pos = None

        if b == "sleep":
            closed = True
        elif b == "idle":
            closed = 0.30 <= t < 0.34 or 0.88 <= t < 0.91
            look = -1 if t < 0.2 else 1 if 0.7 <= t < 0.88 else 0
            for start in (0.45, 0.62):
                if start <= t < start + 0.15:
                    sac = math.sin(math.pi * (t - start) / 0.15)
            if 0.45 <= t < 0.95:
                u = (t - 0.45) / 0.5
                cv.blit(glyph_sprite(NOTE, WHITE), fx + 12 + round(u * 10), fy - 26 - round(u * 14))
        elif b == "hunt":
            def buzz(u: float) -> tuple[float, float]:
                hx, hy = 80 + 12 * math.sin(TAU * u * 3), 12 + 4 * math.sin(TAU * u * 5)
                if u < 0.2:
                    k = u / 0.2
                    return 134 + (hx - 134) * k, 6 + (hy - 6) * k
                return hx, hy

            t0, tc, t1 = 0.55, 0.62, 0.70
            if t < tc:
                fly_pos = buzz(t)
            prey = moth if self.night else fly  # frogs hunt moths after dark
            hx, hy = buzz(tc)
            look = 1 if (fly_pos or (hx, hy))[0] > fx + 4 else -1 if (fly_pos or (hx, hy))[0] < fx - 4 else 0
            mouth = (fx, fy - SIT_H + 10)
            if t0 <= t < t1:
                k = (t - t0) / (tc - t0) if t < tc else 1 - (t - tc) / (t1 - tc)
                tongue = (mouth, (mouth[0] + (hx - mouth[0]) * k, mouth[1] + (hy - mouth[1]) * k), t >= tc)
            closed = 0.72 <= t < 0.80
        elif b == "leap":
            if t < 0.08:
                oy = 1
            elif t < 0.48:
                u = (t - 0.08) / 0.4
                oy = -round(10 * 4 * u * (1 - u))
                template = JUMP
            elif t < 0.56 and self.lilies:
                dip = 1
            if 0.48 <= t < 0.8:
                self._splash(cv, (t - 0.48) / 0.32, fx)
            self._sparkles(cv, f, fx, fy - 10 + oy, 20)

        self._pads(cv, dip)
        old = toad.stage == len(STAGES) - 1
        if old:
            skin = toad_skin(skin)
        sprite = frog_sprite(template, skin, toad.spot_colors, toad.spots, look, closed, old)
        cv.blit(sprite, fx, fy + oy + dip, tone=self.tone)
        top = fy + oy + dip - (SIT_H if template is SIT else JUMP_H)
        if old:
            cv.blit(tuft(), fx, top + 4, tone=self.tone)
        if sac > 0.1:
            self._vocal_sac(cv, fx, fy + oy + dip - SIT_H + 12, sac, skin)
        if tongue:
            self._tongue(cv, *tongue, f)
        if fly_pos:
            cv.blit(prey(f % 2), round(fly_pos[0]), round(fly_pos[1]), tone=self.tone)
        if b == "sleep":
            self._zzz(cv, t, fx + 15, top + 4)

    def _vocal_sac(self, cv: Canvas, x: int, y: int, a: float, skin: dict) -> None:
        body = {}
        rx, ry = 2 + 5 * a, 1.5 + 3 * a
        for dx, dy in ellipse(rx, ry):
            body[(dx, dy)] = skin["Y"] if dy < ry * 0.4 else skin["y"]
        body[(-round(rx * 0.5), -round(ry * 0.5))] = 0xFFFFFF
        cv.blit(outlined(body), x, y + round(ry * 0.6), tone=self.tone)

    def _tongue(self, cv: Canvas, start, end, caught: bool, f: int) -> None:
        (x0, y0), (x1, y1) = start, end
        n = max(1, round(max(abs(x1 - x0), abs(y1 - y0))))
        body = {}
        for i in range(n + 1):
            body[(round(x0 + (x1 - x0) * i / n), round(y0 + (y1 - y0) * i / n))] = 0xE85A88
        tx, ty = round(x1), round(y1)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                body[(tx + dx, ty + dy)] = 0xE85A88
        body[(tx - 1, ty - 1)] = 0xFFA8C8
        cv.blit(outlined(body), 0, 0)
        if caught:
            cv.blit((moth if self.night else fly)(f % 2), tx, ty - 1)

    def _splash(self, cv: Canvas, u: float, x: int) -> None:
        th, sy = self.theme, self.sy
        for side in (-1, 1):
            for k in range(3):
                dx = side * (6 + k * 4) * (0.4 + u)
                dy = -(10 - k * 3) * 4 * u * (1 - u)
                cv.set(round(x + side * 14 + dx), round(sy - 2 + dy), th["shimmer"])
        r = 18 + u * 16
        for dx in range(-round(r), round(r) + 1):
            if abs(dx) > r - 3:
                cv.set(x + dx, sy, 0xFFFFFF)

    def _sparkles(self, cv: Canvas, f: int, cx: int, cy: int, spread: int) -> None:
        r = random.Random(3)
        for i in range(3):
            ox, oy = r.randint(-spread, spread), r.randint(-spread, spread // 2)
            step = (f // 3 + i * 5) % 12  # slow twinkle, lit a third of the time
            if step < 4:
                cv.blit(sparkle(1 if step in (1, 2) else 0), cx + ox, cy + oy)

    def _zzz(self, cv: Canvas, t: float, x: int, y: int) -> None:
        for i in range(3):
            u = (t + i / 3) % 1
            letter = "Z" if u > 0.4 else "z"
            cv.blit(text_sprite(letter, WHITE), x + round(u * 8 + math.sin(u * TAU) * 2), y - round(u * 18))

    # -- frames
    def frame(self, f: int) -> list[int]:
        t = f / FRAMES
        cv = self.base.copy()
        self._water(cv, f, t)
        self._plants(cv, t)
        self._critters(cv, f, t, ("bottom", "water", "film"))
        self._bubbles(cv, t)
        self._surface_plants(cv, t)
        self._critters(cv, f, t, ("air",))  # behind the frog and the reeds
        stage = self.toad.stage
        if stage < 4:
            self._pads(cv)
            if stage == 0:
                self._spawn(cv, f, t)
            else:
                self._swim(cv, f, t)
        else:
            self._frog(cv, f, t)
        self._critters(cv, f, t, ("surface",))
        self._reeds(cv, t)
        if self.hud:
            self._hud(cv)
            return cv.px + self._status_box(f)
        return cv.px

    @property
    def height(self) -> int:
        return H + STATUS_H if self.hud else H

    def _status_box(self, f: int) -> list[int]:
        """An RPG dialogue box under the pond; the reason types itself out, then a cursor blinks."""
        box = [OUTLINE] * (W * STATUS_H)

        def put(x: int, y: int, c: int) -> None:
            if 0 <= x < W and 0 <= y < STATUS_H:
                box[y * W + x] = c

        for y in range(1, STATUS_H - 1):
            for x in range(1, W - 1):
                frame = y in (1, STATUS_H - 2) or x in (1, W - 2)
                put(x, y, 0xE8E8F0 if frame else 0x24348C if y < 6 else 0x1C2870)
        msg = self.toad.status
        shown = min(len(msg), round(f * len(msg) / TYPE_FRAMES))
        pts = text_pixels(msg[:shown])
        for x, y in pts:
            put(6 + x, 5 + y, OUTLINE)
        for x, y in pts:
            put(5 + x, 4 + y, WHITE)
        if shown == len(msg) and (f // 4) % 2 == 0:
            for i, w in enumerate((5, 3, 1)):
                for dx in range(w):
                    put(W - 9 + (5 - w) // 2 + dx, 6 + i, 0xF8D848)
        return box

    def frames(self) -> list[list[int]]:
        return [self.frame(f) for f in range(FRAMES)]
