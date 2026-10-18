#!/usr/bin/env python3
"""
Snap lyric start times to the nearest detected onset or beat.

Usage:
    python3 scripts/snap_to_beats.py lyrics.json beats.json [output.json] [--max-shift 0.12]
        [--grid beats|onsets] [--hook-grid beats|onsets]

Only moves a line if a hit is within --max-shift seconds (default 0.12),
so hand-timed lines are tightened, never dragged to the wrong word.
--hook-grid lets hooks ("emphasis": true) use a different grid, e.g. verses
on vocal onsets and hooks on the beat.
Uses beats.json from detect_beats.py. Needs no extra libraries.

Built by SERTAI LAB. MIT License.
"""
import argparse
import bisect
import json


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lyrics")
    ap.add_argument("beats")
    ap.add_argument("output", nargs="?")
    ap.add_argument("--max-shift", type=float, default=0.12)
    ap.add_argument("--grid", choices=["onsets", "beats"], default="onsets")
    ap.add_argument("--hook-grid", choices=["onsets", "beats"], help="Grid for emphasis lines")
    a = ap.parse_args()

    cfg = json.load(open(a.lyrics, encoding="utf-8"))
    b = json.load(open(a.beats, encoding="utf-8"))
    grids = {k: sorted(b.get("onset_times" if k == "onsets" else "beat_times", []))
             for k in ("onsets", "beats")}
    for k in {a.grid, a.hook_grid or a.grid}:
        if not grids[k]:
            raise SystemExit(f"No {k} found in {a.beats}")

    moved = 0
    for line in cfg["lyrics"]:
        grid = grids[a.hook_grid if (a.hook_grid and line.get("emphasis")) else a.grid]
        t = line["start"]
        i = bisect.bisect_left(grid, t)
        near = [g for g in grid[max(0, i - 1):i + 1]]
        best = min(near, key=lambda g: abs(g - t))
        if abs(best - t) <= a.max_shift and best != t:
            line["start"] = round(best, 3)
            moved += 1
    cfg["lyrics"].sort(key=lambda l: l["start"])
    out = a.output or a.lyrics
    json.dump(cfg, open(out, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    hook = f", hooks to {a.hook_grid}" if a.hook_grid else ""
    print(f"Snapped {moved}/{len(cfg['lyrics'])} lines to {a.grid}{hook}. Saved: {out}")


if __name__ == "__main__":
    main()
