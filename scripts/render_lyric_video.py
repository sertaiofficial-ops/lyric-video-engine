#!/usr/bin/env python3
"""
Lyric Video Renderer
Renders timed lyrics over a background video with beat-synced kinetic typography.

Usage:
    python3 scripts/render_lyric_video.py <video_input> <audio_input> <lyrics_json> [output]

Arguments:
    video_input   Background video file (mp4)
    audio_input   Song audio file (mp3, wav, ...)
    lyrics_json   JSON file with timed lyrics (see references/lyrics_format.md)
    output        Output video path (default: lyric_video.mp4)
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np
from PIL import Image, ImageDraw, ImageFont

DEFAULT_FONTS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

STYLES = {
    "dark": {
        "glow_radius": 8, "glow_start": 20, "glow_step": 3,
        "backdrop_opacity": 0.6, "text_main": (255, 255, 255),
        "text_normal": (220, 220, 220), "shadow": True,
    },
    "neon": {
        "glow_radius": 12, "glow_start": 50, "glow_step": 4,
        "backdrop_opacity": 0.4, "text_main": (0, 255, 255),
        "text_normal": (180, 240, 240), "shadow": False,
    },
    "minimal": {
        "glow_radius": 0, "glow_start": 0, "glow_step": 0,
        "backdrop_opacity": 0.3, "text_main": (255, 255, 255),
        "text_normal": (200, 200, 200), "shadow": True,
    },
}


def run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(result.stderr[-2000:])
        sys.exit(f"Command failed: {' '.join(cmd[:3])} ...")
    return result


def find_font(config):
    candidates = [config.get("font_path"), os.environ.get("LYRIC_FONT")] + DEFAULT_FONTS
    for path in candidates:
        if path and os.path.exists(path):
            return path
    sys.exit("No font found. Set \"font_path\" in lyrics.json, set LYRIC_FONT, "
             "or install fonts-liberation (sudo apt-get install fonts-liberation).")


def stable_seed(text, step):
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16) + step


def main():
    if len(sys.argv) < 4:
        print("Usage: python3 scripts/render_lyric_video.py <video> <audio> <lyrics_json> [output]")
        sys.exit(1)

    video_input, audio_input, lyrics_file = sys.argv[1:4]
    output = sys.argv[4] if len(sys.argv) > 4 else "lyric_video.mp4"

    with open(lyrics_file, encoding="utf-8") as f:
        config = json.load(f)

    style = STYLES.get(config.get("style", "dark"), STYLES["dark"])
    W = config.get("width", 720)
    H = config.get("height", 720)
    fps = config.get("fps", 30)
    font_size_emp = config.get("font_size_emphasis", 64)
    font_size_norm = config.get("font_size_normal", 46)
    text_y = config.get("text_y", 400)
    band_top = max(0, config.get("band_top", 380))
    band_h = max(1, min(config.get("band_height", 180), H - band_top))
    punch_dur = config.get("punch_duration", 0.35)
    shake_mult = config.get("shake_intensity", 8)
    glow_r = style["glow_radius"]
    fade_start = config.get("fade_start", 0.85)
    lyrics = sorted(config["lyrics"], key=lambda x: x["start"])

    font_path = find_font(config)
    font_big = ImageFont.truetype(font_path, font_size_emp)
    font_normal = ImageFont.truetype(font_path, font_size_norm)

    work = tempfile.mkdtemp(prefix="lyric_video_")
    raw_dir = os.path.join(work, "raw")
    out_dir = os.path.join(work, "out")
    os.makedirs(raw_dir)
    os.makedirs(out_dir)
    audio_sync = os.path.join(work, "audio.m4a")

    try:
        print("Extracting frames...")
        run(["ffmpeg", "-y", "-i", video_input,
             "-vf", f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}",
             os.path.join(raw_dir, "frame_%05d.png")])
        frame_files = sorted(os.listdir(raw_dir))
        total = len(frame_files)
        print(f"Extracted {total} frames")

        vid_dur = run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                       "-of", "csv=p=0", video_input]).stdout.strip()
        run(["ffmpeg", "-y", "-i", audio_input, "-ss", "0", "-t", vid_dur,
             "-c:a", "aac", "-b:a", "192k", audio_sync])

        # Precompute the backdrop band mask
        t = np.arange(band_h) / band_h
        darken = np.exp(-2.5 * (t - 0.5) ** 2) * style["backdrop_opacity"]
        band_mask = (1.0 - darken)[:, None, None]

        print("Rendering...")
        for i, fname in enumerate(frame_files):
            ct = i / fps
            frame = Image.open(os.path.join(raw_dir, fname)).convert("RGB")

            active, end_time = None, None
            for j, item in enumerate(lyrics):
                e = lyrics[j + 1]["start"] if j + 1 < len(lyrics) else float(vid_dur)
                if item["start"] <= ct < e:
                    active, end_time = item, e
                    break

            if active:
                txt = active["text"]
                emp = active.get("emphasis", False)
                sh = active.get("shake", 0)
                line_dur = max(1e-6, end_time - active["start"])
                progress = (ct - active["start"]) / line_dur
                pp = min(1.0, (ct - active["start"]) / punch_dur)
                font = font_big if emp else font_normal

                # Punch-in with shake, then a slow breathing drift on emphasis lines
                if progress < punch_dur / line_dur:
                    scale = 0.3 + 0.7 * pp
                    rng = np.random.default_rng(stable_seed(txt, int(pp * 50)))
                    sf = max(0.0, 1.0 - pp) * sh
                    dx = int(rng.standard_normal() * sf * shake_mult)
                    dy = int(rng.standard_normal() * sf * shake_mult)
                else:
                    scale, dx, dy = 1.0, 0, 0
                    if emp:
                        scale = 1.0 + 0.015 * np.sin(ct * 2.0)
                        dx = int(np.sin(ct * 1.5) * 2)
                        dy = int(np.cos(ct * 1.2) * 1.5)
                font_scaled = ImageFont.truetype(font_path, max(8, int(font.size * scale)))

                arr = np.array(frame).astype(np.float32)
                arr[band_top:band_top + band_h] *= band_mask
                frame = Image.fromarray(arr.astype(np.uint8))
                draw = ImageDraw.Draw(frame)

                bbox = draw.textbbox((0, 0), txt, font=font_scaled)
                tw = bbox[2] - bbox[0]
                th = bbox[3] - bbox[1]
                text_x = (W - tw) // 2 + dx
                text_y_pos = text_y + dy + (font.size - th) // 2

                if emp and glow_r > 0:
                    for off in range(glow_r, 0, -1):
                        ga = max(20, style["glow_start"] - off * style["glow_step"])
                        for ox, oy in [(-off, 0), (off, 0), (0, -off), (0, off),
                                       (-off, -off), (off, -off), (-off, off), (off, off)]:
                            draw.text((text_x + ox, text_y_pos + oy), txt, font=font_scaled, fill=(ga, ga, ga))
                    draw.text((text_x, text_y_pos), txt, font=font_scaled, fill=style["text_main"])
                elif style["shadow"]:
                    for off in range(3, 0, -1):
                        draw.text((text_x + off, text_y_pos + off), txt, font=font_scaled, fill=(0, 0, 0))
                    draw.text((text_x, text_y_pos), txt, font=font_scaled, fill=style["text_normal"])
                else:
                    draw.text((text_x, text_y_pos), txt, font=font_scaled, fill=style["text_main"])

                if progress > fade_start:
                    fade = 1.0 - (progress - fade_start) / (1.0 - fade_start)
                    arr = np.array(frame).astype(np.float32)
                    arr[band_top:band_top + band_h] *= fade
                    frame = Image.fromarray(arr.astype(np.uint8))

            frame.save(os.path.join(out_dir, f"frame_{i:05d}.png"))
            if i % 300 == 0:
                print(f"  {i}/{total}")

        print(f"All {total} frames done. Encoding...")
        run(["ffmpeg", "-y", "-framerate", str(fps),
             "-i", os.path.join(out_dir, "frame_%05d.png"), "-i", audio_sync,
             "-c:v", "libx264", "-preset", "fast", "-crf", "17",
             "-c:a", "aac", "-b:a", "192k", "-shortest", "-pix_fmt", "yuv420p",
             "-movflags", "+faststart", output])
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if not os.path.exists(output) or os.path.getsize(output) == 0:
        sys.exit("Render failed: output file was not created.")
    print(f"Done. Output: {output}")


if __name__ == "__main__":
    main()
