---
name: lyric-video
description: >-
  Use when making a dark lyric video: timed lines, punch or shake on the hook,
  fonts, colour gradients and word-by-word highlights, type over a background clip.
---

# Lyric Video

Build a dark, beat-synced lyric video: kinetic type over a background clip.
Inputs are a background video, the song audio, and timed lyrics. Output is an MP4.

## Timing

Listen and place each line at the vocal entry, not on a guessed grid. A line usually holds 1.5 to 3 seconds.

- Chorus, peaks and punchlines: `"emphasis": true`
- Aggressive or emotional lines: `"shake": 3` to `5`
- Verse filler: `"emphasis": false`, `"shake": 0` or `1`
- To clear the screen at the end, add a last entry with `"text": " "`

## lyrics.json

```json
{"style": "dark", "lyrics": [
  {"start": 0.2, "text": "intro line", "emphasis": false, "shake": 0},
  {"start": 2.0, "text": "THE HOOK LINE", "emphasis": true, "shake": 4},
  {"start": 3.5, "text": "next verse line", "emphasis": false, "shake": 0}
]}
```

Full parameter reference: [references/lyrics_format.md](references/lyrics_format.md).

## Look: fonts, colour and motion

Pick the look before timing details; it decides how much room each line needs.

- **Two fonts, one job each.** A clean sans for verses (`"font_normal": "montserrat"`), a condensed display face for hooks (`"font_emphasis": "bebas-neue"` or `"anton"`). Condensed faces need about 1.5x the usual hook size.
- **Colour from the footage.** Take two or three colours from the background (title, neon, lighting) and use them as `gradient_normal` and `gradient_emphasis`. Verses get a calm two-colour gradient; hooks get the hottest colours.
- **Colour that moves with the song.** Shift each verse line's `color` slightly along the same family (cyan, then bluer, then violet) and set `"color_blend": 0.4` so each line flows out of the last. On hooks, `color_to` turns the line into a second gradient as it plays.
- **Word sweep on hooks.** Add `words` with each word's start (and end) time; the hook lights up left to right as it is sung. Use it on hooks only, so it stays special.
- **Entries.** Verses: `fade_rise`. A new section: `blur_in`. Hooks: `tracking_in` with `"punch": 0.05` and `shake` 3–4 on the downbeat. `typewriter` suits spoken or slow lines. `pop` is the original scale-in.
- **Exits.** `fade` with `"exit_duration": 0.35` for most lines; `blur_out` for the last hook into the outro.
- **Glow.** `"glow_color": "text"` glows in the text's own colours; keep `glow_strength` around 0.5–0.8, and `glow_normal` at 0.2 or less for verses.
- **Avoid gimmicks.** One moving effect per line is enough. If a frame looks busy, drop `gradient_speed` or `hue_shift` first.

## Styles

| Preset | Use when | Look |
|--------|----------|------|
| `dark` | Noir, melancholy, rap ballads | Gray glow, 60% band, white type |
| `neon` | Electronic, energetic | Cyan glow, 40% band, electric type |
| `minimal` | Clean, editorial | No glow, 30% band, clean type |

## Layout: find the empty zone

Look at the background first. Put the text where nothing important lives (no title, logo or face), and keep it out of the top ~10% and bottom ~12% on vertical video, where platform buttons sit.

- Set `text_center_y`, `band_top` and `band_height` for that zone.
- If the background is busy in that zone for a moment (a title sliding in), give the lines in that moment their own `"y"` in another empty zone, or start them after it settles.
- Long lines shrink to `safe_width`, then wrap to two rows. On vertical video, split anything longer than about 5 words into two cues instead.

## Render (optional automation)

Needs Python 3, ffmpeg, and `pip install -r requirements.txt` (see docs/INSTALL.md for a virtual environment).

1. Beats: `python3 scripts/detect_beats.py song.mp3 beats.json` (BPM, beat and onset times; video files work too)
2. Write `lyrics.json`
3. Check frames: `python3 scripts/render_lyric_video.py background.mp4 song.mp3 lyrics.json --stills 3,9,15 --preset presets/vertical_9x16.json`
4. Render: `python3 scripts/render_lyric_video.py background.mp4 song.mp3 lyrics.json output.mp4 --preset presets/vertical_9x16.json --preset presets/look_neon_gradient.json`

## Hook punch rules

- The first time the hook appears: `emphasis: true`, `shake: 3`. Repeats: `shake: 4`. The final chorus: `shake: 5`.
- Never put two `shake: 5` lines back to back; the second one loses impact. Separate them with a calm line.
- Land the hook on the downbeat or the first strong onset of the bar, even if the vocal starts a hair earlier.
- Write hook lines in CAPS and verse lines in lowercase; the contrast alone signals the hook.
- Short lines hit harder: split any hook longer than about 5 words into two cues.
- Clear the screen (`" "`) for instrumental breaks longer than about 2 seconds.

## Already have timed lyrics?

If you have an `.srt` or `.lrc` file (from a subtitle editor, a lyrics site or your distributor), convert it instead of timing from scratch:

`python3 scripts/import_subtitles.py song.lrc lyrics.json --style dark --preset presets/vertical_9x16.json`

Then tighten timings to real hits: `python3 scripts/snap_to_beats.py lyrics.json beats.json --hook-grid beats` (verses to vocal onsets, hooks to the beat). Enhanced LRC files with word tags (`<00:12.34>word`) also bring word timings for the sweep.

## Formats

Use `presets/vertical_9x16.json` for Reels/Shorts/TikTok, `square_1x1.json` for feed posts, `landscape_16x9.json` for YouTube.

## Notes

- Auto-captioning tools often fail on rap, slow tempos and non-English lyrics. Time the lines by ear.
- Keep the type clear of anything printed on the background: move `text_center_y` and `band_top`.
- Beat detection can report 2x, 1/2x or 4/3x the felt tempo; trust the beat times more than the BPM figure.
- Do not call a render finished until the MP4 exists and plays.
