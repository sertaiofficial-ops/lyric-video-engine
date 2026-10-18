#!/usr/bin/env python3
"""
Import SRT or LRC lyrics into lyrics.json.

Usage:
    python3 scripts/import_subtitles.py <lyrics.srt|lyrics.lrc> [output.json] [--style dark] [--preset presets/vertical_9x16.json]

Hook rules (applied automatically, edit the result by hand afterwards):
  - A line written in ALL CAPS, or a line that repeats 2+ times in the song,
    is marked "emphasis": true with "shake": 4.
  - A line ending in "!" gets "shake": 5.
  - Everything else: "emphasis": false, "shake": 0 (1 if it is short, <= 3 words).
  - If a cue has an end time and the next cue starts more than 0.4 s later,
    a " " line is inserted so the screen clears during the gap.
  - Enhanced LRC word tags (<mm:ss.xx>word) become "words" timings, which the
    renderer uses for the karaoke-style word sweep.

Built by SERTAI LAB. MIT License.
"""
import argparse
import json
import re
import sys
from collections import Counter

SRT_TIME = re.compile(r"(\d+):(\d+):(\d+)[,.](\d+)\s*-->\s*(\d+):(\d+):(\d+)[,.](\d+)")
LRC_TIME = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def srt_cues(text):
    cues = []
    for block in re.split(r"\n\s*\n", text.strip()):
        lines = [l.strip() for l in block.splitlines() if l.strip()]
        for i, l in enumerate(lines):
            m = SRT_TIME.search(l)
            if m:
                g = [int(x) for x in m.groups()]
                start = g[0] * 3600 + g[1] * 60 + g[2] + g[3] / 1000
                end = g[4] * 3600 + g[5] * 60 + g[6] + g[7] / 1000
                body = " ".join(lines[i + 1:])
                body = re.sub(r"<[^>]+>|\{[^}]+\}", "", body).strip()
                if body:
                    cues.append({"start": start, "end": end, "text": body})
                break
    return cues


WORD_TAG = re.compile(r"<(\d+):(\d+(?:\.\d+)?)>\s*([^<]*)")


def lrc_cues(text):
    cues = []
    for line in text.splitlines():
        stamps = LRC_TIME.findall(line)
        raw = LRC_TIME.sub("", line)
        words = []
        for mm, ss, chunk in WORD_TAG.findall(raw):  # enhanced LRC word tags
            for w in chunk.split():
                words.append({"start": round(int(mm) * 60 + float(ss), 3)})
                break
        body = re.sub(r"<\d+:\d+(?:\.\d+)?>", "", raw)
        body = re.sub(r"\s+", " ", body).strip()
        for mm, ss in stamps:
            cue = {"start": int(mm) * 60 + float(ss), "end": None, "text": body}
            if words and len(words) == len(body.split()):
                cue["words"] = words
            cues.append(cue)
    cues.sort(key=lambda c: c["start"])
    return [c for c in cues if c["text"] or cues]


def norm(s):
    return re.sub(r"[^\w\s]", "", s.lower()).strip()


def mark(cues):
    counts = Counter(norm(c["text"]) for c in cues if c["text"])
    out = []
    for i, c in enumerate(cues):
        t = c["text"]
        letters = [ch for ch in t if ch.isalpha()]
        caps = bool(letters) and all(ch.isupper() for ch in letters)
        repeated = counts[norm(t)] >= 2 if t else False
        emphasis = caps or repeated
        shake = 4 if emphasis else (1 if t and len(t.split()) <= 3 else 0)
        if t.endswith("!"):
            shake = 5
        entry = {"start": round(c["start"], 3), "text": t or " ",
                 "emphasis": emphasis, "shake": shake}
        if c.get("words"):
            entry["words"] = c["words"]
        out.append(entry)
        nxt = cues[i + 1]["start"] if i + 1 < len(cues) else None
        if c.get("end") and (nxt is None or nxt - c["end"] > 0.4):
            out.append({"start": round(c["end"], 3), "text": " ", "emphasis": False, "shake": 0})
    return out


def main():
    ap = argparse.ArgumentParser(description="SRT/LRC to lyrics.json")
    ap.add_argument("input")
    ap.add_argument("output", nargs="?", default="lyrics.json")
    ap.add_argument("--style", default="dark", choices=["dark", "neon", "minimal"])
    ap.add_argument("--look", help="Optional look preset (fonts, colours, animations) to merge in")
    ap.add_argument("--preset", help="JSON file with layout keys (width, height, text_y, ...)")
    a = ap.parse_args()

    text = open(a.input, encoding="utf-8-sig").read()
    cues = srt_cues(text) if "-->" in text else lrc_cues(text)
    if not cues:
        sys.exit("No timed lines found. Is this a valid .srt or .lrc file?")

    config = {}
    for p in (a.preset, a.look):
        if p:
            config.update({k: v for k, v in json.load(open(p, encoding="utf-8")).items()
                           if not k.startswith("_")})
    config["style"] = a.style
    config["lyrics"] = mark(cues)
    with open(a.output, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    hooks = sum(1 for l in config["lyrics"] if l["emphasis"])
    print(f"Lines: {len(config['lyrics'])}  Hooks: {hooks}  Saved: {a.output}")


if __name__ == "__main__":
    main()
