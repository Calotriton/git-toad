"""16-bit style pond scene and the toad's sprites, frame by frame."""

from __future__ import annotations

import math
import random

from .font import text_pixels, text_width
from .life import STAGES, Toad

W, H = 128, 96
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


def _night() -> dict:
    t = {k: (mix(v, NIGHT_INK, 0.55) if isinstance(v, int) else [mix(c, NIGHT_INK, 0.55) for c in v]) for k, v in DAY.items()}
    t["sky"] = [0x080A24, 0x0E1238, 0x161C4C, 0x1E285E, 0x2A3870]
    t["water"] = [0x1E3C6C, 0x18325E, 0x132850, 0x0F1F42, 0x0A1634]
    t["surface"] = 0x6C88B8
    t["shimmer"] = 0xD8E4F8
    t["caustic"] = 0x2A4C80
    return t


NIGHT = _night()

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


def lily_pad(rx: int) -> dict:
    t = DAY
    body = {}
    for x in range(-rx, rx + 1):
        for y in range(-2, 2):
            if (x / (rx + 0.5)) ** 2 + ((y + 0.5) / 2.2) ** 2 <= 1:
                body[(x, y)] = t["pad_hi"] if y == -2 else t["pad"] if y < 1 else t["pad_dk"]
    for p in [(rx // 3, -2), (rx // 3 + 1, -1)]:
        body[p] = t["pad_dk"]
    return outlined(body, 0x1A4020)


def flower() -> dict:
    t = DAY
    rows = [".P.P.P.", "PpPpPpP", "pPPxPPp", ".ppppp."]
    cmap = {"P": t["petal"], "p": t["petal_dk"], "x": t["pistil"]}
    body = {(c - 3, r - 4): cmap[ch] for r, row in enumerate(rows) for c, ch in enumerate(row) if ch != "."}
    body[(-2, -4)] = t["petal_hi"]
    body[(0, -4)] = t["petal_hi"]
    return outlined(body)


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
class Scene:
    def __init__(self, toad: Toad, skin: str = "meadow", hud: bool = True):
        self.toad = toad
        self.night = toad.behavior == "sleep"
        self.theme = NIGHT if self.night else DAY
        self.skin = SKINS[skin]
        self.hud = hud
        self.rng = random.Random(toad.login)
        self.base = self._base()
        r = self.rng
        self.stars = [(r.randrange(W), r.randrange(28), r.random()) for _ in range(28)]
        self.bubbles = [(r.randrange(8, W - 8), r.random(), r.choice((1, 1, 2))) for _ in range(7)]
        self.plants = [(x, r.randrange(9, 17), r.random() * TAU) for x in (8, 15, 47, 90, 97, 118)]
        self.eggs = self._egg_cluster()

    def tone(self, c: int) -> int:
        return mix(c, NIGHT_INK, 0.3) if self.night and c != OUTLINE else c

    # -- static backdrop
    def _base(self) -> Canvas:
        t, cv = self.theme, Canvas()
        for y in range(SURFACE):
            for x in range(W):
                cv.set(x, y, gradient(t["sky"], y / (SURFACE - 1), x, y))
        if self.night:
            moon = {}
            for x, y in ellipse(5, 5):
                moon[(x, y)] = 0xF8F0C8 if x + y < 3 else 0xD8CC98
            for p in [(-2, -1), (1, 2), (2, -2)]:
                moon[p] = 0xC8BC88
            cv.blit(moon, 94, 19)
        else:
            cv.blit(cloud([(0, 0, 4), (5, -2, 5), (11, 0, 4)]), 58, 12)
            cv.blit(cloud([(0, 0, 3), (5, -1, 4), (9, 0, 3)]), 100, 20)
            cv.blit(cloud([(0, 0, 3), (4, -1, 3)]), 18, 22)
        for x in range(W):
            fy = int(28 + 2.5 * math.sin(x * 0.06 + 1.3) + 1.5 * math.sin(x * 0.15 + 0.4))
            for y in range(fy, SURFACE):
                cv.set(x, y, t["far_hi"] if y == fy else t["far"])
        for tx, r in [(30, 4), (38, 3), (74, 4), (82, 5), (122, 4)]:
            for x, y in ellipse(r, r):
                cv.set(tx + x, 33 - r + y, t["tree_hi"] if x + y < -1 else t["tree"])
        for x in range(W):
            ny = int(35 + 1.5 * math.sin(x * 0.09 + 2.1) + 1.2 * math.sin(x * 0.21 + 1))
            for y in range(ny, SURFACE):
                cv.set(x, y, t["near_hi"] if y == ny else t["near"])
        for y in range(SURFACE, H):
            for x in range(W):
                cv.set(x, y, gradient(t["water"], (y - SURFACE) / (BOTTOM - SURFACE), x, y))
        for x in range(W):
            top = BOTTOM + round(1.2 * math.sin(x * 0.2) + 0.8 * math.sin(x * 0.07 + 1))
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
        return cv

    def _egg_cluster(self) -> list[tuple[int, int, int]]:
        eggs = []
        for row in range(4):
            for col in range(5 - abs(row - 1)):
                x = 22 + col * 5 + (row % 2) * 2 + abs(row - 1) * 2
                y = SURFACE + 5 + row * 4
                eggs.append((x, y, self.rng.randrange(4)))
        return eggs

    # -- animated layers
    def _water(self, cv: Canvas, f: int, t: float) -> None:
        th = self.theme
        shift = f // 3
        for x in range(W):
            cv.set(x, SURFACE, th["shimmer"] if (x + shift) % 16 < 3 else th["surface"])
            if (x - shift) % 24 < 2:
                cv.set(x, SURFACE + 2, th["surface"])
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
        th = self.theme
        for x0, h, ph in self.plants:
            for i in range(h):
                y = BOTTOM - i
                x = x0 + round(math.sin(TAU * t + ph + i * 0.3) * 1.6 * i / h)
                cv.set(x, y, th["plant"])
                if i % 4 == 2:
                    cv.set(x - 1, y, th["plant_hi"])
                    cv.set(x - 2, y - 1, th["plant_hi"])
                elif i % 4 == 0 and i:
                    cv.set(x + 1, y, th["plant_hi"])
                    cv.set(x + 2, y - 1, th["plant_hi"])

    def _reeds(self, cv: Canvas, t: float) -> None:
        th = self.theme
        for x0, top, ph, tail in [(110, 14, 0.0, True), (114, 20, 1.3, True), (119, 11, 2.2, True),
                                  (123, 24, 0.7, False), (4, 26, 1.9, False), (7, 22, 0.4, True)]:
            for y in range(top, SURFACE + 8):
                k = max(0, SURFACE - y) / (SURFACE - top)
                x = x0 + round(math.sin(TAU * t + ph) * 1.2 * k)
                under = y > SURFACE
                cv.set(x, y, mix(th["reed"], th["water"][1], 0.5) if under else th["reed"])
                if not under and y % 3 == 0:
                    cv.set(x - 1, y, th["reed_hi"])
            if tail:
                x = x0 + round(math.sin(TAU * t + ph) * 1.2)
                for y in range(top + 2, top + 8):
                    cv.set(x, y, th["cattail"])
                    cv.set(x + 1, y, th["cattail_hi"] if y < top + 4 else th["cattail"])
                cv.set(x, top + 1, th["reed"])

    def _bubbles(self, cv: Canvas, t: float) -> None:
        th = self.theme
        for x0, ph, speed in self.bubbles:
            u = (t * speed + ph) % 1
            y = BOTTOM - 2 - round(u * (BOTTOM - SURFACE - 4))
            x = x0 + round(math.sin(u * TAU * 2) * 1.5)
            if speed == 2:
                cv.set(x, y, th["bubble"])
            else:
                for dx, dy in N4:
                    cv.set(x + dx, y + dy, th["bubble_dk"])
                cv.set(x - 1, y - 1, th["bubble"])

    def _pads(self, cv: Canvas, dip: int = 0) -> None:
        tone = self.tone
        cv.blit(lily_pad(8), 26, SURFACE, tone=tone)
        cv.blit(flower(), 25, SURFACE - 1, tone=tone)
        cv.blit(lily_pad(17), 64, SURFACE + dip, tone=tone)

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

    # -- the creature
    def _spawn(self, cv: Canvas, f: int, t: float) -> None:
        excited = self.toad.behavior == "leap"
        for i, (x, y, emb) in enumerate(self.eggs):
            dy = round(math.sin(TAU * t * 2 + i * 0.9) * 0.7)
            wiggle = emb + (f // (2 if excited else 6)) + i
            cv.blit(egg(wiggle if (excited or i % 3 == 0) else emb), x, y + dy, tone=self.tone)
        if excited:
            self._sparkles(cv, f, 34, SURFACE + 11, 14)

    def _swim(self, cv: Canvas, f: int, t: float) -> None:
        toad, b = self.toad, self.toad.behavior

        def path(u: float, laps: int, rx: float) -> tuple[float, float, bool]:
            a = TAU * u * laps
            x = 64 + rx * math.cos(a)
            y = 63 + 9 * math.sin(a) + 2 * math.sin(2 * a)
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
                    fx, fy = mx + math.sin(u * TAU * 2) * 2, SURFACE + 2 + (cy - SURFACE - 2) * u
                    flake = {(0, 0): 0x9AD848, (1, 0): 0x5AA830, (0, 1): 0x5AA830}
                    cv.blit(outlined(flake, 0x2A5A20), round(fx), round(fy))
                mouth = tc - 0.06 <= t <= tc + 0.04
        sprite = swimmer(toad.stage, phase, self.skin, toad.spot_colors, toad.spots, mouth)
        cv.blit(sprite, round(x), round(y), flip=not right, tone=self.tone)
        if b == "sleep":
            self._zzz(cv, t, round(x) + 6, round(y) - 6)

    def _frog(self, cv: Canvas, f: int, t: float) -> None:
        toad, b, skin = self.toad, self.toad.behavior, self.skin
        fx, fy = 64, SURFACE - 1
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
            elif t < 0.56:
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
            cv.blit(fly(f % 2), round(fly_pos[0]), round(fly_pos[1]), tone=self.tone)
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
            cv.blit(fly(f % 2), tx, ty - 1)

    def _splash(self, cv: Canvas, u: float, x: int) -> None:
        th = self.theme
        for side in (-1, 1):
            for k in range(3):
                dx = side * (6 + k * 4) * (0.4 + u)
                dy = -(10 - k * 3) * 4 * u * (1 - u)
                cv.set(round(x + side * 14 + dx), round(SURFACE - 2 + dy), th["shimmer"])
        r = 18 + u * 16
        for dx in range(-round(r), round(r) + 1):
            if abs(dx) > r - 3:
                cv.set(x + dx, SURFACE, 0xFFFFFF)

    def _sparkles(self, cv: Canvas, f: int, cx: int, cy: int, spread: int) -> None:
        r = random.Random(3)
        for i in range(5):
            ox, oy = r.randint(-spread, spread), r.randint(-spread, spread // 2)
            size = (f // 2 + i * 3) % 6
            if size < 3:
                cv.blit(sparkle(size), cx + ox, cy + oy)

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
        self._bubbles(cv, t)
        stage = self.toad.stage
        if stage < 4:
            self._pads(cv)
            if stage == 0:
                self._spawn(cv, f, t)
            else:
                self._swim(cv, f, t)
        else:
            self._frog(cv, f, t)
        self._reeds(cv, t)
        if self.hud:
            self._hud(cv)
        return cv.px

    def frames(self) -> list[list[int]]:
        return [self.frame(f) for f in range(FRAMES)]
