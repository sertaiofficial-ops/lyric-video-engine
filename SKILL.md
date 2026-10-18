---
name: lyric-video
description: >-
  Use when making a dark lyric video: timed lines, punch or shake on the hook,
  type over a background clip.
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

## Styles

| Preset | Use when | Look |
|--------|----------|------|
| `dark` | Noir, melancholy, rap ballads | Gray glow, 60% band, white type |
| `neon` | Electronic, energetic | Cyan glow, 40% band, electric type |
| `minimal` | Clean, editorial | No glow, 30% band, clean type |

## Render (optional automation)

Needs Python 3, ffmpeg, and `pip install -r requirements.txt`.

1. Beats: `python3 scripts/detect_beats.py song.mp3 beats.json` (BPM, beat and onset times to snap lines to)
2. Write `lyrics.json`
3. Render: `python3 scripts/render_lyric_video.py background.mp4 song.mp3 lyrics.json output.mp4`

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

Then tighten timings to real hits: `python3 scripts/snap_to_beats.py lyrics.json beats.json`

## Formats

Use `presets/vertical_9x16.json` for Reels/Shorts/TikTok, `square_1x1.json` for feed posts, `landscape_16x9.json` for YouTube.

## Notes

- Auto-captioning tools often fail on rap, slow tempos and non-English lyrics. Time the lines by ear.
- Keep the type below any template watermark: move `text_y` and `band_top` down.
- Songs longer than about three minutes: render in two parts to save memory.
- Do not call a render finished until the MP4 exists and plays.
