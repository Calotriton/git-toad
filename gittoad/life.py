"""Turn a contribution snapshot into a toad: its life stage, spots and mood."""

from __future__ import annotations

from dataclasses import dataclass, field

# (minimum total contributions, HUD name)
STAGES = [
    (0, "SPAWN"),
    (30, "TADPOLE"),
    (300, "POLLIWOG"),
    (1000, "FROGLET"),
    (3000, "FROG"),
    (10000, "OLD TOAD"),
]
MILESTONES = [100, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000]
BEHAVIORS = ["idle", "hunt", "leap", "sleep"]
SLEEP_QUIET_DAYS = 14
DEFAULT_SPOT = "#f8d848"


@dataclass
class Toad:
    login: str
    total: int
    stage: int
    behavior: str
    spots: int  # 0..3 pairs of spots, earned with streaks
    spot_colors: list[int] = field(default_factory=list)
    longest_streak: int = 0
    quiet_days: int = 0

    @property
    def stage_name(self) -> str:
        return STAGES[self.stage][1]

    @property
    def progress(self) -> float:
        if self.stage == len(STAGES) - 1:
            return 1.0
        lo, hi = STAGES[self.stage][0], STAGES[self.stage + 1][0]
        return (self.total - lo) / (hi - lo)


def hex_color(text: str) -> int:
    return int(text.lstrip("#")[:6], 16)


def stage_for(total: int) -> int:
    return max(i for i, (threshold, _) in enumerate(STAGES) if total >= threshold)


def read(snapshot: dict) -> Toad:
    counts = [count for _, count in snapshot.get("days", [])]
    total = sum(counts)
    stage = stage_for(total)

    quiet = 0
    for c in reversed(counts):
        if c:
            break
        quiet += 1

    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)

    yesterday = counts[-1] if counts else 0
    week_ago = total - sum(counts[-7:])
    thresholds = MILESTONES + [t for t, _ in STAGES[1:]]
    crossed = any(week_ago < m <= total for m in thresholds)
    active = sorted(c for c in counts[-365:] if c)
    busy = yesterday >= 3 and len(active) >= 10 and yesterday >= active[int(len(active) * 0.9)]

    if counts and quiet >= SLEEP_QUIET_DAYS:
        behavior = "sleep"
    elif crossed or busy:
        behavior = "leap"
    elif yesterday:
        behavior = "hunt"
    else:
        behavior = "idle"

    langs = snapshot.get("languages") or []
    colors = [hex_color(l["color"]) for l in langs[:3] if l.get("color")] or [hex_color(DEFAULT_SPOT)]

    return Toad(
        login=snapshot.get("login", "octocat"),
        total=total,
        stage=stage,
        behavior=behavior,
        spots=min(3, longest // 7),
        spot_colors=colors,
        longest_streak=longest,
        quiet_days=quiet,
    )
