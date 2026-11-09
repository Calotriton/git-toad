"""git-toad command line: collect GitHub activity, render the toad."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date, timedelta

from . import __version__
from .art import DELAY_CS, FRAMES, H, SKINS, W, Scene
from .collect import CollectError, collect
from .encode import encode_gif, encode_png
from .life import BEHAVIORS, STAGES, Toad, read

STILL_FRAME = 12


def _write(path: str, data: bytes) -> None:
    tmp = path + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, path)


def render_toad(toad: Toad, out_dir: str, skin: str, scale: int, hud: bool, name: str = "toad") -> Scene:
    scene = Scene(toad, skin=skin, hud=hud)
    frames = scene.frames()
    os.makedirs(out_dir, exist_ok=True)
    _write(os.path.join(out_dir, f"{name}.gif"), encode_gif(frames, W, H, scale, DELAY_CS))
    _write(os.path.join(out_dir, f"{name}.png"), encode_png(frames[STILL_FRAME], W, H, scale))
    pond = {"date": scene.day.isoformat(), "season": scene.season.name.lower(), "species": scene.census}
    _write(os.path.join(out_dir, "pond.json"), json.dumps(pond, indent=1, ensure_ascii=False).encode())
    return scene


def cmd_collect(args) -> int:
    snapshot = collect(args.login)
    text = json.dumps(snapshot, indent=1)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(text)
    else:
        print(text)
    return 0


def cmd_render(args) -> int:
    with open(args.snapshot, encoding="utf-8") as fh:
        toad = read(json.load(fh))
    if args.stage is not None:
        toad.stage = args.stage
    if args.behavior:
        toad.behavior = args.behavior
    if args.date:
        toad.day = date.fromisoformat(args.date)
    scene = render_toad(toad, args.output_dir, args.skin, args.scale, not args.no_hud)
    print(f"{toad.login}: LV{toad.stage} {toad.stage_name}, {toad.total} contributions, "
          f"behavior={toad.behavior}, spots={toad.spots}, {scene.season.name.lower()} {toad.day} -> {args.output_dir}")
    for s in scene.census:
        print(f"  {s['count']} x {s['name']} ({s['latin']})")
    return 0


def demo_snapshot(total: int) -> dict:
    today = date(2026, 1, 1)
    days = [((today - timedelta(days=i)).isoformat(), 0) for i in range(400, 0, -1)]
    per = max(1, total // 300)
    left = total
    for i in range(len(days) - 1, -1, -1):
        if left <= 0:
            break
        n = min(per, left)
        days[i] = (days[i][0], n)
        left -= n
    langs = [{"name": "Python", "color": "#3572A5", "repos": 5}, {"name": "Rust", "color": "#dea584", "repos": 3},
             {"name": "TypeScript", "color": "#3178c6", "repos": 2}]
    return {"login": "demo", "days": days, "languages": langs}


def cmd_demo(args) -> int:
    """Render every stage x behavior (or every month), plus a still contact sheet."""
    os.makedirs(args.output_dir, exist_ok=True)
    sheet_rows = []
    if args.seasons:
        toad = read(demo_snapshot(STAGES[args.stage][0] + 40))
        toad.spots = 3
        toad.behavior = "idle"
        cols = 4
        for r in range(3):
            row = []
            for c in range(cols):
                toad.day = date(2026, r * cols + c + 1, 15)
                frames = Scene(toad, skin=args.skin).frames()
                if args.gifs:
                    _write(os.path.join(args.output_dir, f"month{toad.day.month:02d}.gif"),
                           encode_gif(frames, W, H, args.scale, DELAY_CS))
                row.append(frames[args.frame % FRAMES])
            sheet_rows.append(row)
    else:
        for stage, (threshold, _) in enumerate(STAGES):
            toad = read(demo_snapshot(max(threshold, 5) + 40))
            toad.stage = stage
            toad.spots = 3
            row = []
            for behavior in BEHAVIORS:
                toad.behavior = behavior
                frames = Scene(toad, skin=args.skin, hud=True).frames()
                if args.gifs:
                    _write(os.path.join(args.output_dir, f"stage{stage}_{behavior}.gif"),
                           encode_gif(frames, W, H, args.scale, DELAY_CS))
                row.append(frames[args.frame % FRAMES])
            sheet_rows.append(row)
    cols = len(sheet_rows[0])
    gap = 2
    sw, sh = cols * (W + gap), len(sheet_rows) * (H + gap)
    sheet = [0x101010] * (sw * sh)
    for r, row in enumerate(sheet_rows):
        for c, px in enumerate(row):
            for y in range(H):
                o = (r * (H + gap) + y) * sw + c * (W + gap)
                sheet[o : o + W] = px[y * W : (y + 1) * W]
    _write(os.path.join(args.output_dir, "sheet.png"), encode_png(sheet, sw, sh, args.sheet_scale))
    print(f"wrote demo to {args.output_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="git-toad", description="A 16-bit pond toad grown from your GitHub contributions.")
    p.add_argument("--version", action="version", version=f"git-toad {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("collect", help="fetch public contribution data into a snapshot JSON")
    c.add_argument("login")
    c.add_argument("--output", "-o")
    c.set_defaults(func=cmd_collect)

    r = sub.add_parser("render", help="render toad.gif and toad.png from a snapshot")
    r.add_argument("snapshot")
    r.add_argument("--output-dir", "-d", default="toad")
    r.add_argument("--skin", choices=sorted(SKINS), default="meadow")
    r.add_argument("--scale", type=int, default=4)
    r.add_argument("--no-hud", action="store_true")
    r.add_argument("--stage", type=int, choices=range(len(STAGES)), help="override the life stage")
    r.add_argument("--behavior", choices=BEHAVIORS, help="override the behavior")
    r.add_argument("--date", help="draw the pond as on this day (YYYY-MM-DD), for previews")
    r.set_defaults(func=cmd_render)

    d = sub.add_parser("demo", help="render every stage and behavior")
    d.add_argument("--output-dir", "-d", default="demo")
    d.add_argument("--skin", choices=sorted(SKINS), default="meadow")
    d.add_argument("--scale", type=int, default=4)
    d.add_argument("--frame", type=int, default=STILL_FRAME)
    d.add_argument("--sheet-scale", type=int, default=2)
    d.add_argument("--gifs", action="store_true")
    d.add_argument("--seasons", action="store_true", help="one frame per month instead of per stage")
    d.add_argument("--stage", type=int, default=4, choices=range(len(STAGES)), help="stage for --seasons")
    d.set_defaults(func=cmd_demo)

    args = p.parse_args(argv)
    try:
        return args.func(args)
    except CollectError as err:
        print(f"git-toad: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
