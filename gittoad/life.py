"""Turn a contribution snapshot into a toad: its life stage, spots and mood."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

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
STATUS_CHARS = 27  # what fits in the dialogue box


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
    day: date = field(default_factory=date.today)  # the day the toad is drawn for
    yesterday: int = 0
    reason: str = ""  # why it leaps: "stage", "milestone" or "busy"
    milestone: int = 0

    @property
    def stage_name(self) -> str:
        return STAGES[self.stage][1]

    @property
    def status(self) -> str:
        """One line for the dialogue box saying why the toad does what it does."""
        n, q, b = self.yesterday, self.quiet_days, self.behavior
        if b == "sleep":
            options = [f"ZZZ... {q} QUIET DAYS"] if q else ["ZZZ..."]
        elif b == "leap":
            options = {
                "stage": [f"NEW STAGE: {self.stage_name}!"],
                "milestone": [f"MILESTONE: {self.milestone} REACHED!", f"MILESTONE: {self.milestone}!"],
                "busy": [f"BIG DAY: {n} CONTRIBUTIONS!", f"BIG DAY: {n} CONTRIBS!"],
            }.get(self.reason, ["CELEBRATING!"])
        elif b == "hunt" and n:
            if self.stage == 0:  # frogspawn doesn't eat
                options = [f"+{n} CONTRIBUTION{'' if n == 1 else 'S'} YESTERDAY", f"+{n} CONTRIBS YESTERDAY"]
            else:
                options = [f"{n} NEW CONTRIBUTION{'' if n == 1 else 'S'}. YUM!", f"{n} NEW CONTRIBS. YUM!"]
        elif b == "hunt":
            options = ["HUNTING!"]
        elif q == 1:
            options = ["NO CONTRIBUTIONS YESTERDAY"]
        elif q > 1:
            options = [f"{q} QUIET DAYS IN A ROW"]
        else:
            options = ["JUST CHILLING"]
        for text in options:
            if len(text) <= STATUS_CHARS:
                return text
        return options[-1][:STATUS_CHARS]

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
    new_stage = stage_for(week_ago) < stage
    crossed = [m for m in MILESTONES if week_ago < m <= total]
    active = sorted(c for c in counts[-365:] if c)
    busy = yesterday >= 3 and len(active) >= 10 and yesterday >= active[int(len(active) * 0.9)]
    reason = "stage" if new_stage else "milestone" if crossed else "busy" if busy else ""

    if counts and quiet >= SLEEP_QUIET_DAYS:
        behavior = "sleep"
    elif reason:
        behavior = "leap"
    elif yesterday:
        behavior = "hunt"
    else:
        behavior = "idle"

    langs = snapshot.get("languages") or []
    colors = [hex_color(l["color"]) for l in langs[:3] if l.get("color")] or [hex_color(DEFAULT_SPOT)]

    days = snapshot.get("days") or []
    observed = snapshot.get("observed") or (days[-1][0] if days else None)

    return Toad(
        day=date.fromisoformat(observed) if observed else date.today(),
        login=snapshot.get("login", "octocat"),
        total=total,
        stage=stage,
        behavior=behavior,
        spots=min(3, longest // 7),
        spot_colors=colors,
        longest_streak=longest,
        quiet_days=quiet,
        yesterday=yesterday,
        reason=reason,
        milestone=max(crossed, default=0),
    )
