"""Tests for the lyric video scripts using tiny inputs generated at test time."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import import_subtitles as subs  # noqa: E402
import render_lyric_video as rlv  # noqa: E402

needs_ffmpeg = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg not installed")


def run(*args):
    return subprocess.run([sys.executable, *map(str, args)], capture_output=True, text=True, cwd=ROOT)


# ---------- import_subtitles ----------

SRT = """1
00:00:01,000 --> 00:00:02,500
hello night

2
00:00:03,000 --> 00:00:04,000
NEVER LET GO

3
00:00:06,000 --> 00:00:07,000
hello night
"""


def test_srt_cues_parse_times():
    cues = subs.srt_cues(SRT)
    assert [c["start"] for c in cues] == [1.0, 3.0, 6.0]
    assert cues[0]["end"] == 2.5 and cues[1]["text"] == "NEVER LET GO"


def test_mark_emphasis_and_gap_blanks():
    out = subs.mark(subs.srt_cues(SRT))
    texts = [(o["start"], o["text"], o["emphasis"]) for o in out]
    assert (3.0, "NEVER LET GO", True) in texts      # all caps -> emphasis
    assert (1.0, "hello night", True) in texts       # repeated -> emphasis
    assert (4.0, " ", False) in texts                # gap > 0.4 s -> blank line


def test_lrc_cues():
    cues = subs.lrc_cues("[00:01.50]first line\n[00:03.00]second line\n")
    assert [(c["start"], c["text"]) for c in cues] == [(1.5, "first line"), (3.0, "second line")]


def test_import_subtitles_cli(tmp_path):
    srt = tmp_path / "in.srt"
    srt.write_text(SRT, encoding="utf-8")
    out = tmp_path / "lyrics.json"
    r = run(SCRIPTS / "import_subtitles.py", srt, out, "--style", "neon")
    assert r.returncode == 0, r.stderr
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["style"] == "neon"
    assert data["lyrics"][0]["text"] == "hello night"


# ---------- snap_to_beats ----------

def test_snap_to_beats(tmp_path):
    lyrics = tmp_path / "lyrics.json"
    lyrics.write_text(json.dumps({"style": "dark", "lyrics": [
        {"start": 1.05, "text": "a", "emphasis": False, "shake": 0},
        {"start": 2.50, "text": "b", "emphasis": False, "shake": 0},
    ]}), encoding="utf-8")
    beats = tmp_path / "beats.json"
    beats.write_text(json.dumps({"onset_times": [1.0, 2.0, 3.0], "beat_times": [1.0, 2.0, 3.0]}), encoding="utf-8")
    out = tmp_path / "snapped.json"
    r = run(SCRIPTS / "snap_to_beats.py", lyrics, beats, out)
    assert r.returncode == 0, r.stderr
    starts = [l["start"] for l in json.loads(out.read_text(encoding="utf-8"))["lyrics"]]
    assert starts == [1.0, 2.5]   # 0.05 s snapped, 0.5 s beyond max-shift left alone


# ---------- render helpers ----------

def test_parse_color_and_easing():
    assert tuple(rlv.parse_color("#FF0000"))[:3] == (255, 0, 0)
    assert rlv.clamp(2) == 1.0 and rlv.clamp(-1) == 0.0
    assert rlv.ease_out(0) == pytest.approx(0) and rlv.ease_out(1) == pytest.approx(1)


def test_bundled_fonts_resolve():
    for name in ("bebas-neue", "montserrat", "anton"):
        path = rlv.resolve_font(name, [str(ROOT)])
        assert path and Path(path).exists(), name


def test_example_lyrics_files_are_valid():
    for f in ROOT.glob("examples/*/lyrics.json"):
        data = json.loads(f.read_text(encoding="utf-8"))
        starts = [l["start"] for l in data["lyrics"]]
        assert starts == sorted(starts), f
        assert all(isinstance(l["text"], str) for l in data["lyrics"])


# ---------- end-to-end render ----------

@needs_ffmpeg
def test_render_tiny_video(tmp_path):
    video = tmp_path / "bg.mp4"
    audio = tmp_path / "beat.wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=0x101020:s=160x160:d=1.5:r=12",
                    "-pix_fmt", "yuv420p", str(video)], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=220:duration=1.5",
                    str(audio)], check=True)
    lyrics = tmp_path / "lyrics.json"
    lyrics.write_text(json.dumps({"style": "neon", "width": 160, "height": 160, "fps": 12,
                                  "text_y": 70, "band_top": 50, "band_height": 60, "lyrics": [
        {"start": 0.1, "text": "TEST", "emphasis": True, "shake": 3},
        {"start": 1.0, "text": "line", "emphasis": False, "shake": 0},
    ]}), encoding="utf-8")
    out = tmp_path / "out.mp4"
    r = run(SCRIPTS / "render_lyric_video.py", video, audio, lyrics, out)
    assert r.returncode == 0, r.stdout + r.stderr
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,width,height",
                            "-of", "json", str(out)], capture_output=True, text=True, check=True)
    streams = json.loads(probe.stdout)["streams"]
    v = next(s for s in streams if s["codec_type"] == "video")
    assert (v["width"], v["height"]) == (160, 160)
    assert any(s["codec_type"] == "audio" for s in streams)


@needs_ffmpeg
def test_stills_show_text_over_background(tmp_path):
    video = tmp_path / "bg.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=200x200:d=2:r=10",
                    "-pix_fmt", "yuv420p", str(video)], check=True)
    lyrics = tmp_path / "lyrics.json"
    lyrics.write_text(json.dumps({"style": "neon", "width": 200, "height": 200, "fps": 10,
                                  "text_y": 100, "band_top": 70, "band_height": 60,
                                  "lyrics": [{"start": 0.0, "text": "HELLO", "emphasis": True, "shake": 0}]}),
                      encoding="utf-8")
    stills = tmp_path / "stills"
    r = run(SCRIPTS / "render_lyric_video.py", video, "none", lyrics, tmp_path / "x.mp4",
            "--stills", "1.0", "--stills-dir", stills)
    assert r.returncode == 0, r.stdout + r.stderr
    pngs = list(stills.glob("*.png"))
    assert len(pngs) == 1
    from PIL import Image
    img = np.asarray(Image.open(pngs[0]).convert("RGB")).astype(int)
    assert img.shape == (200, 200, 3)
    assert img.max() > 120   # lyric text drawn on a black frame
