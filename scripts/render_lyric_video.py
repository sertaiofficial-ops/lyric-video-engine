#!/usr/bin/env python3
"""
Lyric Video Renderer
Renders timed lyrics over a background video with beat-synced kinetic typography:
per-line fonts and colors, animated gradients, line-to-line color blends,
karaoke-style word sweeps, entry/exit animations, colored glow and auto-fit.

Usage:
    python3 scripts/render_lyric_video.py <video> <audio> <lyrics.json> [output.mp4]
        [--preset layout.json] [--preset look.json]
        [--start S] [--duration D]
        [--stills 1.5,4.2,9.0 --stills-dir frames/]
        [--keep-metadata]

Arguments:
    video         Background video (any format ffmpeg reads)
    audio         Song audio (mp3, wav, ...) or a video file with audio; "none" for silent
    lyrics.json   Timed lyrics and settings (see references/lyrics_format.md)
    output        Output MP4 (default: lyric_video.mp4)

Settings are merged in this order: built-in defaults < lyrics.json < each --preset
(later presets win). Old lyrics.json files from earlier versions render unchanged.

Built by SERTAI LAB. MIT License.
"""

import argparse
import colorsys
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from functools import lru_cache

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(REPO_DIR, "fonts")

# Fonts bundled in fonts/ (SIL Open Font License, see each folder's OFL.txt)
FONT_ALIASES = {
    "bebas-neue": "bebas-neue/BebasNeue-Regular.ttf",
    "anton": "anton/Anton-Regular.ttf",
    "montserrat": "montserrat/Montserrat-SemiBold.ttf",
    "montserrat-semibold": "montserrat/Montserrat-SemiBold.ttf",
}

SYSTEM_FONTS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]

STYLES = {
    "dark": {
        "text_normal": "#DCDCDC", "text_emphasis": "#FFFFFF",
        "glow_color": "#C8C8C8", "glow_strength": 0.55, "glow_radius": 8,
        "backdrop_opacity": 0.6, "shadow": True,
    },
    "neon": {
        "text_normal": "#B4F0F0", "text_emphasis": "#00FFFF",
        "glow_color": "#00FFFF", "glow_strength": 0.9, "glow_radius": 12,
        "backdrop_opacity": 0.4, "shadow": False,
    },
    "minimal": {
        "text_normal": "#C8C8C8", "text_emphasis": "#FFFFFF",
        "glow_color": "#FFFFFF", "glow_strength": 0.0, "glow_radius": 0,
        "backdrop_opacity": 0.3, "shadow": True,
    },
}

DEFAULTS = {
    "style": "dark",
    "width": 720, "height": 720, "fps": 30,
    "font_size_emphasis": 64, "font_size_normal": 46,
    "text_y": 400, "band_top": 380, "band_height": 180, "band": True,
    "punch_duration": 0.35, "shake_intensity": 8, "fade_start": 0.85,
    # newer settings (all optional)
    "safe_width": 0.9, "min_font_scale": 0.72, "wrap": True, "line_spacing": 1.1,
    "letter_spacing": 0, "animation_in": "pop", "animation_out": "fade",
    "entry_duration": None, "exit_duration": None,
    "rise": 0.35, "blur_amount": 14, "tracking": 0.3, "punch": 0.0,
    "breathe": True, "glow_normal": 0.0,
    "gradient_speed": 0.0, "gradient_angle": 0.0, "hue_shift": 0.0,
    "color_blend": 0.0, "sweep": True, "sweep_dim": 0.42, "sweep_softness": 28,
    "shadow_opacity": 0.75, "x264_preset": "medium", "crf": 17,
}

# Keys a single line may override
LINE_KEYS = ["font", "font_size", "letter_spacing", "animation_in", "animation_out",
             "entry_duration", "exit_duration", "rise", "blur_amount", "tracking", "punch",
             "breathe", "gradient_speed", "gradient_angle", "hue_shift", "color_blend",
             "sweep", "sweep_dim", "sweep_softness", "glow_color", "glow_strength",
             "glow_radius", "shadow", "shadow_opacity", "backdrop_opacity", "fade_start",
             "y", "band_top", "band_height", "band", "wrap", "safe_width"]

ANIM_IN = {"pop", "fade", "fade_rise", "blur_in", "tracking_in", "typewriter", "none"}
ANIM_OUT = {"fade", "fade_rise", "blur_out", "none"}


# ---------------------------------------------------------------- helpers

def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(r.stderr[-2000:])
        sys.exit(f"Command failed: {' '.join(cmd[:3])} ...")
    return r


def clamp(v, lo=0.0, hi=1.0):
    return lo if v < lo else hi if v > hi else v


def ease_out(t):
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    return t * t * (3 - 2 * t)


def parse_color(c):
    if isinstance(c, str):
        h = c.lstrip("#")
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)
    return np.array(c[:3], dtype=np.float32)


def parse_gradient(spec):
    """'#fff' | [r,g,b] | ['#a', '#b', ...] | [[r,g,b], ...] -> (N,3) float array."""
    if spec is None:
        return None
    if isinstance(spec, str) or (isinstance(spec, (list, tuple)) and spec
                                 and isinstance(spec[0], (int, float))):
        return parse_color(spec)[None, :]
    return np.stack([parse_color(c) for c in spec])


def resample(stops, n):
    if len(stops) == n:
        return stops
    if len(stops) == 1:
        return np.repeat(stops, n, axis=0)
    src = np.linspace(0, 1, len(stops))
    dst = np.linspace(0, 1, n)
    return np.stack([np.interp(dst, src, stops[:, k]) for k in range(3)], axis=1)


def blend_stops(a, b, k):
    n = max(len(a), len(b))
    return resample(a, n) * (1 - k) + resample(b, n) * k


def hue_rotate(stops, degrees):
    if not degrees:
        return stops
    out = []
    for r, g, b in stops / 255.0:
        h, l, s = colorsys.rgb_to_hls(r, g, b)
        out.append(colorsys.hls_to_rgb((h + degrees / 360.0) % 1.0, l, s))
    return np.array(out, dtype=np.float32) * 255.0


def sample_gradient(stops, u):
    """u: array in [0,1] -> (..., 3)"""
    if len(stops) == 1:
        return np.broadcast_to(stops[0], u.shape + (3,)).astype(np.float32)
    pos = np.linspace(0, 1, len(stops))
    return np.stack([np.interp(u, pos, stops[:, k]) for k in range(3)], axis=-1).astype(np.float32)


def stable_seed(text, step):
    return int(hashlib.md5(text.encode("utf-8")).hexdigest()[:8], 16) + step


def resolve_font(name, base_dirs):
    """Alias, absolute path, path relative to the lyrics/preset file or repo, or a file in fonts/."""
    if not name:
        return None
    if name in FONT_ALIASES:
        return os.path.join(FONT_DIR, FONT_ALIASES[name])
    if os.path.isabs(name):
        return name if os.path.exists(name) else None
    for d in list(base_dirs) + [REPO_DIR, FONT_DIR]:
        p = os.path.join(d, name)
        if os.path.exists(p):
            return p
    return None


@lru_cache(maxsize=256)
def load_font(path, size):
    return ImageFont.truetype(path, max(6, int(size)))


@lru_cache(maxsize=4096)
def text_len(path, size, s):
    return load_font(path, size).getlength(s)


# ---------------------------------------------------------------- one lyric line

class Line:
    def __init__(self, idx, item, cfg, style, base_dirs, W, H):
        self.idx = idx
        self.item = item
        self.text = item.get("text", "")
        self.blank = not self.text.strip()
        self.start = float(item["start"])
        self.emp = bool(item.get("emphasis", False))
        self.shake = float(item.get("shake", 0))
        g = lambda k: item.get(k, cfg.get(k))
        self.g = g
        self.W, self.H = W, H
        if self.blank:
            return

        # font
        font_name = item.get("font") or (cfg.get("font_emphasis") if self.emp else cfg.get("font_normal"))
        path = resolve_font(font_name, base_dirs) if font_name else None
        if font_name and not path:
            print(f"Warning: font '{font_name}' not found, using default")
        self.font_path = path or cfg["_default_font"]
        base_size = item.get("font_size") or (cfg["font_size_emphasis"] if self.emp else cfg["font_size_normal"])
        self.base_size = base_size

        # colors
        grad = item.get("color", item.get("gradient"))
        if grad is None:
            grad = cfg.get("gradient_emphasis" if self.emp else "gradient_normal")
        if grad is None:
            grad = style["text_emphasis"] if self.emp else style["text_normal"]
        self.stops = parse_gradient(grad)
        self.stops_to = parse_gradient(item.get("color_to"))
        gc = g("glow_color")
        self.glow_from_text = (gc == "text")
        self.glow_color = None if self.glow_from_text else parse_color(gc or style["glow_color"])
        if "glow_strength" in item:
            self.glow_strength = float(item["glow_strength"])
        elif self.emp:
            self.glow_strength = float(cfg.get("glow_strength", style["glow_strength"]))
        else:
            self.glow_strength = float(cfg.get("glow_normal") or 0.0)
        self.glow_radius = float(g("glow_radius") if g("glow_radius") is not None else style["glow_radius"])
        sh = g("shadow")
        self.shadow = style["shadow"] if sh is None else bool(sh)
        bo = g("backdrop_opacity")
        self.backdrop = style["backdrop_opacity"] if bo is None else float(bo)

        # animation
        self.anim_in = g("animation_in") or "pop"
        self.anim_out = g("animation_out") or "fade"
        if self.anim_in not in ANIM_IN:
            print(f"Warning: unknown animation_in '{self.anim_in}', using fade_rise")
            self.anim_in = "fade_rise"
        if self.anim_out not in ANIM_OUT:
            print(f"Warning: unknown animation_out '{self.anim_out}', using fade")
            self.anim_out = "fade"
        self.spacing0 = float(g("letter_spacing") or 0)
        self.track = float(g("tracking")) * base_size if self.anim_in == "tracking_in" else 0.0

        # layout: fit / wrap to the safe width
        sw = float(g("safe_width"))
        self.max_w = sw * W if sw <= 1 else sw
        self.layout(bool(g("wrap")), float(cfg["min_font_scale"]), float(cfg["line_spacing"]))

        # placement
        if item.get("y") is not None:
            self.cy = float(item["y"])
            bh = item.get("band_height", cfg["band_height"])
            self.band = (int(self.cy - bh / 2), int(bh))
        else:
            self.cy = float(cfg["text_center_y"]) if cfg.get("text_center_y") is not None \
                else cfg["text_y"] + base_size / 2
            bt = item.get("band_top", cfg["band_top"])
            bh = item.get("band_height", cfg["band_height"])
            self.band = (int(bt), int(bh))
        if len(self.rows) > 1 and item.get("band_height") is None:
            need = int(self.size * self.lsp * len(self.rows) + self.size * 0.6)
            if need > self.band[1]:
                self.band = (int(self.band[0] - (need - self.band[1]) / 2), need)

        # word timings for the sweep
        self.word_times = []
        words = item.get("words")
        if words:
            for w in words:
                if isinstance(w, dict):
                    self.word_times.append((float(w["start"]), w.get("end")))
                else:
                    self.word_times.append((float(w), None))
        self.cache = {}
        full, boxes = self.build(self.spacing0, None)
        bb = full.getbbox() or (0, 0, full.width, full.height)
        self.ink = bb
        self.anchor = ((bb[0] + bb[2]) / 2.0, (bb[1] + bb[3]) / 2.0)
        self.nchars = sum(len(r) for r in self.rows)

    def row_width(self, row, size, spacing):
        return text_len(self.font_path, size, row) + spacing * max(0, len(row) - 1)

    def layout(self, wrap, min_scale, lsp):
        size, text = self.base_size, self.text
        self.lsp = lsp
        rows = [text]
        w = self.row_width(text, size, self.spacing0)
        words = text.split()
        if w > self.max_w:
            need = self.max_w / w
            if need >= min_scale or not wrap or len(words) < 2:
                size = int(size * need)
            else:
                best = None
                for k in range(1, len(words)):
                    r = [" ".join(words[:k]), " ".join(words[k:])]
                    m = max(self.row_width(x, size, self.spacing0) for x in r)
                    if best is None or m < best[0]:
                        best = (m, r)
                rows = best[1]
                if best[0] > self.max_w:
                    size = int(size * self.max_w / best[0])
        self.size, self.rows = size, rows
        font = load_font(self.font_path, size)
        asc, desc = font.getmetrics()
        self.asc, self.desc = asc, desc
        if self.track:  # keep tracked-out letters inside the frame
            room = []
            for r in rows:
                gaps = max(1, len(r) - 1)
                room.append((self.W * 0.96 / (1 + float(self.g("punch") or 0)) - self.row_width(r, size, self.spacing0)) / gaps)
            self.track = max(0.0, min(self.track, min(room)))
        spacing_max = self.spacing0 + self.track
        self.content_w = max(self.row_width(r, size, spacing_max) for r in rows)
        self.pad = int(self.size * 0.25 + 30)
        self.box_w = int(self.content_w + 2 * self.pad)
        self.box_h = int(size * lsp * (len(rows) - 1) + asc + desc + 2 * self.pad)

    def build(self, spacing, reveal):
        key = (round(spacing, 1), reveal)
        if key in self.cache:
            return self.cache[key]
        font = load_font(self.font_path, self.size)
        img = Image.new("L", (self.box_w, self.box_h), 0)
        d = ImageDraw.Draw(img)
        boxes = []  # (x0, x1, y0, y1) per word, in order
        count = 0
        for r, row in enumerate(self.rows):
            y = self.pad + r * self.size * self.lsp
            x0 = (self.box_w - self.row_width(row, self.size, spacing)) / 2.0
            i = 0
            for word in row.split(" "):
                if word:
                    j = row.index(word, i)
                    wx0 = x0 + text_len(self.font_path, self.size, row[:j]) + j * spacing
                    wx1 = x0 + text_len(self.font_path, self.size, row[:j + len(word)]) + (j + len(word) - 1) * spacing
                    boxes.append((wx0, wx1, y, y + self.asc + self.desc))
                    i = j + len(word)
            for i, ch in enumerate(row):
                if reveal is not None and count >= reveal:
                    break
                if ch != " ":
                    x = x0 + text_len(self.font_path, self.size, row[:i]) + i * spacing
                    d.text((x, y), ch, font=font, fill=255)
                count += 1
        self.cache[key] = (img, boxes)
        if len(self.cache) > 64:
            self.cache.pop(next(iter(self.cache)))
        return img, boxes

    def end_stops(self):
        return self.stops_to if self.stops_to is not None else self.stops


# ---------------------------------------------------------------- frame composition

@lru_cache(maxsize=32)
def band_profile(h, opacity):
    # soft window: full strength in the middle, feathered to zero at both edges
    t = (np.arange(h) + 0.5) / max(1, h)
    return (np.sin(np.pi * t) ** 1.2 * opacity).astype(np.float32)[:, None, None]


def blur(img, r):
    if r <= 0.5:
        return img
    if r > 6:  # blur at half size for big radii (same look, much faster)
        w, h = img.size
        small = img.resize((max(1, w // 2), max(1, h // 2)), Image.BILINEAR)
        return small.filter(ImageFilter.GaussianBlur(r / 2)).resize((w, h), Image.BILINEAR)
    return img.filter(ImageFilter.GaussianBlur(r))


def draw_line(frame, ln, ct, end, prev, cfg):
    """Composite one lyric line onto frame (H,W,3 float32) at time ct."""
    g = ln.g
    t = ct - ln.start
    dur = max(1e-3, end - ln.start)
    progress = clamp(t / dur)
    punch_dur = float(cfg["punch_duration"])

    ein = g("entry_duration")
    if ein is None:
        ein = punch_dur if ln.anim_in == "pop" else \
            min(dur * 0.6, max(0.3, ln.nchars * 0.045)) if ln.anim_in == "typewriter" else 0.4
    ein = max(1e-3, float(ein))
    pin = clamp(t / ein)
    ei = ease_out(pin)

    eout = g("exit_duration")
    out_start = dur - float(eout) if eout is not None else dur * float(g("fade_start"))
    pout = clamp((t - out_start) / max(1e-3, dur - out_start)) if ln.anim_out != "none" else 0.0
    eo = ease_in_out(pout)

    alpha, scale, dx, dy, blur_r = 1.0, 1.0, 0.0, 0.0, 0.0
    spacing, reveal = ln.spacing0, None
    size = ln.size
    a_in = ln.anim_in
    if a_in == "pop":
        scale = 0.3 + 0.7 * pin
    elif a_in == "fade":
        alpha = ei
    elif a_in == "fade_rise":
        alpha, dy = ei, (1 - ei) * float(g("rise")) * size
    elif a_in == "blur_in":
        alpha, blur_r, scale = ei, (1 - ei) * float(g("blur_amount")), 1.0 + 0.05 * (1 - ei)
    elif a_in == "tracking_in":
        alpha, spacing = ei ** 0.7, ln.spacing0 + (1 - ei) * ln.track
    elif a_in == "typewriter":
        reveal = int(math.ceil(pin * ln.nchars)) if pin < 1 else None

    punch = float(g("punch") or 0)
    if punch and t < punch_dur * 1.5:
        scale *= 1 + punch * (1 - ease_out(clamp(t / (punch_dur * 1.5))))
    if ln.shake and t < punch_dur:
        pp = clamp(t / punch_dur)
        rng = np.random.default_rng(stable_seed(ln.text, int(pp * 50)))
        sf = (1 - pp) * ln.shake * float(cfg["shake_intensity"])
        dx += rng.standard_normal() * sf
        dy += rng.standard_normal() * sf
    if ln.emp and g("breathe") and pin >= 1 and t >= punch_dur:
        scale *= 1.0 + 0.015 * math.sin(ct * 2.0)
        dx += math.sin(ct * 1.5) * 2
        dy += math.cos(ct * 1.2) * 1.5

    a_out = ln.anim_out
    alpha *= 1 - eo
    if a_out == "fade_rise":
        dy -= eo * float(g("rise")) * size * 0.6
    elif a_out == "blur_out":
        blur_r += eo * float(g("blur_amount"))
    if alpha <= 0.003:
        return

    H, W = frame.shape[:2]
    # backdrop band (fades with the text, background stays untouched)
    if ln.g("band") and ln.backdrop > 0:
        bt, bh = ln.band
        y0, y1 = max(0, bt), min(H, bt + bh)
        if y1 > y0:
            band_a = alpha if a_in not in ("pop", "typewriter", "none") else (1 - eo)
            prof = band_profile(bh, ln.backdrop)[y0 - bt:y1 - bt]
            frame[y0:y1] *= 1.0 - prof * band_a

    mask_img, boxes = ln.build(spacing, reveal)
    bw, bh_ = mask_img.size
    a = np.asarray(mask_img, dtype=np.float32) / 255.0

    # colour field: temporal transition, line-to-line blend, hue drift, moving gradient
    stops = ln.stops
    if ln.stops_to is not None:
        stops = blend_stops(stops, ln.stops_to, ease_in_out(progress))
    cb = float(g("color_blend") or 0)
    if cb > 0 and prev is not None:
        k = ease_in_out(clamp(t / cb))
        if k < 1:
            stops = blend_stops(prev.end_stops(), stops, k)
    stops = hue_rotate(stops, float(g("hue_shift") or 0) * ct)
    ix0, iy0, ix1, iy1 = ln.ink
    ang = math.radians(float(g("gradient_angle") or 0))
    xs = (np.arange(bw, dtype=np.float32) - ix0) / max(1, ix1 - ix0)
    ys = (np.arange(bh_, dtype=np.float32) - iy0) / max(1, iy1 - iy0)
    u = xs[None, :] * math.cos(ang) + ys[:, None] * math.sin(ang)
    spd = float(g("gradient_speed") or 0)
    if spd:
        v = (u + spd * ct) % 2.0
        u = 1.0 - np.abs(v - 1.0)  # ping-pong so the moving gradient has no seam
    color = sample_gradient(stops, np.clip(u, 0, 1))

    # karaoke sweep
    if ln.word_times and g("sweep") and boxes:
        soft = float(g("sweep_softness"))
        hl = np.zeros((bh_, bw), dtype=np.float32)
        for k, (x0, x1, y0b, y1b) in enumerate(boxes):
            if k >= len(ln.word_times):
                hl[int(y0b) - 4:int(y1b) + 8, max(0, int(x0) - 20):int(x1) + 20] = 1.0
                continue
            ws, we = ln.word_times[k]
            if we is None:
                we = ln.word_times[k + 1][0] if k + 1 < len(ln.word_times) else ln.start + dur * 0.9
            f = clamp((ct - ws) / max(1e-3, float(we) - ws))
            sx = x0 + f * (x1 - x0 + soft) - soft * 0.5
            cols = np.arange(max(0, int(x0) - 20), min(bw, int(x1) + 20), dtype=np.float32)
            ramp = np.clip((sx - cols) / soft + 0.5, 0, 1) if f > 0 else np.zeros_like(cols)
            hl[max(0, int(y0b) - 10):min(bh_, int(y1b) + 10), cols.astype(int)] = \
                np.maximum(hl[max(0, int(y0b) - 10):min(bh_, int(y1b) + 10), cols.astype(int)], ramp[None, :])
        lum = color.mean(axis=2, keepdims=True)
        dim = (color * 0.5 + lum * 0.5) * float(g("sweep_dim"))
        color = dim + (color - dim) * hl[:, :, None]

    prem = color * a[:, :, None]
    rgb_img = Image.fromarray(np.clip(prem, 0, 255).astype(np.uint8), "RGB")
    a_img = mask_img

    if abs(scale - 1.0) > 1e-3:
        nw, nh = max(1, int(bw * scale)), max(1, int(bh_ * scale))
        rgb_img = rgb_img.resize((nw, nh), Image.BICUBIC)
        a_img = a_img.resize((nw, nh), Image.BICUBIC)
    if blur_r > 0.5:
        rgb_img, a_img = blur(rgb_img, blur_r), blur(a_img, blur_r)
    sw_, sh_ = a_img.size
    px = int(round(W / 2 - ln.anchor[0] * scale + dx))
    py = int(round(ln.cy - ln.anchor[1] * scale + dy))

    # clip to frame
    fx0, fy0 = max(0, px), max(0, py)
    fx1, fy1 = min(W, px + sw_), min(H, py + sh_)
    if fx1 <= fx0 or fy1 <= fy0:
        return
    sl = (slice(fy0 - py, fy1 - py), slice(fx0 - px, fx1 - px))
    region = frame[fy0:fy1, fx0:fx1]
    A = (np.asarray(a_img, dtype=np.float32) / 255.0)[sl][:, :, None] * alpha
    P = np.asarray(rgb_img, dtype=np.float32)[sl] * alpha

    if ln.shadow:
        so = float(g("shadow_opacity"))
        sa = np.asarray(blur(a_img, max(2.0, ln.size * 0.04)), dtype=np.float32) / 255.0
        off = max(2, int(ln.size * 0.04))
        sa = np.roll(np.roll(sa, off, 0), off, 1)[sl][:, :, None]
        region *= 1.0 - sa * so * alpha
    if ln.glow_strength > 0 and ln.glow_radius > 0:
        r = ln.glow_radius * (ln.size / 64.0) ** 0.5
        if ln.glow_from_text:
            gl = np.asarray(blur(rgb_img, r), dtype=np.float32)[sl]
        else:
            ga = np.asarray(blur(a_img, r), dtype=np.float32)[sl] / 255.0
            gl = ga[:, :, None] * ln.glow_color
        gl = np.clip(gl * ln.glow_strength * 1.6 * alpha, 0, 255)
        region[:] = 255.0 - (255.0 - region) * (1.0 - gl / 255.0)
    region[:] = region * (1.0 - A) + P


# ---------------------------------------------------------------- I/O

def probe_duration(path):
    out = run(["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
               "-of", "csv=p=0", path]).stdout.strip()
    return float(out)


def load_config(lyrics_file, presets):
    cfg = dict(DEFAULTS)
    base_dirs = []
    with open(lyrics_file, encoding="utf-8") as f:
        data = json.load(f)
    base_dirs.append(os.path.dirname(os.path.abspath(lyrics_file)))
    cfg.update({k: v for k, v in data.items() if not k.startswith("_")})
    for p in presets or []:
        with open(p, encoding="utf-8") as f:
            pd = json.load(f)
        base_dirs.append(os.path.dirname(os.path.abspath(p)))
        cfg.update({k: v for k, v in pd.items() if not k.startswith("_") and k != "lyrics"})
    if "lyrics" not in cfg:
        sys.exit("lyrics.json has no \"lyrics\" array")
    style = dict(STYLES.get(cfg.get("style", "dark"), STYLES["dark"]))
    # older keys still work: text_main = emphasis colour
    if "text_main" in cfg:
        style["text_emphasis"] = cfg["text_main"]
    for k in ("text_normal", "text_emphasis", "glow_color", "glow_radius", "glow_strength",
              "backdrop_opacity", "shadow"):
        if k in cfg and cfg[k] is not None:
            style[k] = cfg[k]
    if "glow_strength" not in cfg:
        cfg["glow_strength"] = style["glow_strength"]
    if cfg.get("glow_radius") is None:
        cfg["glow_radius"] = style["glow_radius"]
    if cfg.get("glow_color") is None:
        cfg["glow_color"] = style["glow_color"]
    candidates = [resolve_font(cfg.get("font_path"), base_dirs), os.environ.get("LYRIC_FONT")] + SYSTEM_FONTS \
        + [os.path.join(FONT_DIR, FONT_ALIASES["montserrat"])]
    for c in candidates:
        if c and os.path.exists(c):
            cfg["_default_font"] = c
            break
    else:
        sys.exit("No font found. Set \"font_path\" in lyrics.json, set LYRIC_FONT, "
                 "or install fonts-liberation (sudo apt-get install fonts-liberation).")
    return cfg, style, base_dirs


def active_line(lines, ct, total):
    for j, ln in enumerate(lines):
        nxt = lines[j + 1].start if j + 1 < len(lines) else total
        end = ln.item.get("end")
        end = min(nxt, float(end)) if end is not None else nxt
        if ln.start <= ct < end:
            prev = next((p for p in reversed(lines[:j]) if not p.blank), None)
            return ln, end, prev
    return None, None, None


def render_frame(frame_u8, lines, ct, total, cfg):
    ln, end, prev = active_line(lines, ct, total)
    if ln is None or ln.blank:
        return frame_u8
    f = frame_u8.astype(np.float32)
    draw_line(f, ln, ct, end, prev, cfg)
    return np.clip(f, 0, 255).astype(np.uint8)


def main():
    ap = argparse.ArgumentParser(description="Render a kinetic lyric video.")
    ap.add_argument("video")
    ap.add_argument("audio")
    ap.add_argument("lyrics")
    ap.add_argument("output", nargs="?", default="lyric_video.mp4")
    ap.add_argument("--preset", action="append", help="Layout/look JSON merged over lyrics.json (repeatable)")
    ap.add_argument("--start", type=float, default=0.0, help="Render from this time (s)")
    ap.add_argument("--duration", type=float, help="Render only this many seconds")
    ap.add_argument("--stills", help="Comma-separated times: save PNG frames instead of a video")
    ap.add_argument("--stills-dir", default="stills")
    ap.add_argument("--keep-metadata", action="store_true", help="Keep encoder tags in the MP4")
    a = ap.parse_args()

    cfg, style, base_dirs = load_config(a.lyrics, a.preset)
    W, H, fps = int(cfg["width"]), int(cfg["height"]), cfg["fps"]
    items = sorted(cfg["lyrics"], key=lambda x: x["start"])
    lines = [Line(i, it, cfg, style, base_dirs, W, H) for i, it in enumerate(items)]
    total = probe_duration(a.video)
    vf = f"fps={fps},scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    fsize = W * H * 3

    if a.stills:
        os.makedirs(a.stills_dir, exist_ok=True)
        for ts in [float(x) for x in a.stills.split(",") if x.strip()]:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{ts:.3f}", "-i", a.video, "-vf", vf,
                                  "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                                 capture_output=True).stdout
            if len(raw) < fsize:
                print(f"  no frame at {ts}s")
                continue
            fr = np.frombuffer(raw[:fsize], np.uint8).reshape(H, W, 3)
            out = render_frame(fr, lines, ts, total, cfg)
            p = os.path.join(a.stills_dir, f"still_{ts:06.2f}.png")
            Image.fromarray(out).save(p)
            print(f"  {p}")
        return

    start = max(0.0, a.start)
    span = (a.duration if a.duration else total - start)
    span = min(span, total - start)
    work = tempfile.mkdtemp(prefix="lyric_video_")
    err_path = os.path.join(work, "enc.log")
    try:
        dec = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-t", f"{span:.3f}",
                                "-i", a.video, "-vf", vf, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                               stdout=subprocess.PIPE)
        enc_cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                   "-s", f"{W}x{H}", "-r", str(fps), "-i", "-"]
        has_audio = a.audio.lower() != "none"
        if has_audio:
            enc_cmd += ["-ss", f"{start:.3f}", "-t", f"{span:.3f}", "-i", a.audio,
                        "-map", "0:v:0", "-map", "1:a:0?", "-c:a", "aac", "-b:a", "192k", "-shortest"]
        enc_cmd += ["-c:v", "libx264", "-preset", str(cfg["x264_preset"]), "-crf", str(cfg["crf"]),
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart"]
        if not a.keep_metadata:
            enc_cmd += ["-flags:v", "+bitexact", "-flags:a", "+bitexact"]
        encoded = a.output if a.keep_metadata else os.path.join(work, "encoded.mp4")
        enc_cmd.append(encoded)
        with open(err_path, "w") as errf:
            enc = subprocess.Popen(enc_cmd, stdin=subprocess.PIPE, stderr=errf)
            n, t0 = 0, time.time()
            print(f"Rendering {W}x{H} @ {fps} fps, {span:.1f}s ...")
            while True:
                raw = dec.stdout.read(fsize)
                if len(raw) < fsize:
                    break
                fr = np.frombuffer(raw, np.uint8).reshape(H, W, 3)
                ct = start + n / fps
                try:
                    enc.stdin.write(render_frame(fr, lines, ct, total, cfg).tobytes())
                except BrokenPipeError:
                    break
                n += 1
                if n % (fps * 5) == 0:
                    print(f"  {n / fps:5.1f}s  ({n / (time.time() - t0):.1f} frames/s)")
            enc.stdin.close()
            enc.wait()
            dec.wait()
        if enc.returncode != 0:
            print(open(err_path).read()[-2000:])
            sys.exit("Encoding failed.")
        if not a.keep_metadata:
            # Stream-copy remux: drops container tags, encoder strings and the
            # x264 settings block, so the file carries no tool fingerprints.
            strip = ["ffmpeg", "-y", "-v", "error", "-i", encoded, "-map", "0", "-c", "copy",
                     "-map_metadata", "-1", "-map_chapters", "-1", "-fflags", "+bitexact",
                     "-flags:v", "+bitexact", "-flags:a", "+bitexact", "-movflags", "+faststart"]
            r = subprocess.run(strip + ["-bsf:v", "filter_units=remove_types=6", a.output],
                               capture_output=True, text=True)
            if r.returncode != 0:  # older ffmpeg without filter_units
                run(strip + [a.output])
    finally:
        shutil.rmtree(work, ignore_errors=True)

    if not os.path.exists(a.output) or os.path.getsize(a.output) == 0:
        sys.exit("Render failed: output file was not created.")
    print(f"Done. {n} frames in {time.time() - t0:.1f}s. Output: {a.output}")


if __name__ == "__main__":
    main()
