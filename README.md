# 🎤 Lyric Video Engine: Dark Kinetic Lyric Videos, Beat-Synced

> Give it a background clip, a song and timed lyrics. Get back an MP4 where every line lands on the vocal, hooks punch in with shake and coloured glow, words light up as they are sung, and colours flow from line to line over your footage.

[![Studio: SERTAI LAB](https://img.shields.io/badge/Studio-SERTAI%20LAB-black)](https://sertaiofficial.com)
[![Website: sertaiofficial.com](https://img.shields.io/badge/Website-sertaiofficial.com-blue)](https://sertaiofficial.com)
[![Output: Lyric Video MP4](https://img.shields.io/badge/Output-Lyric%20Video%20MP4-purple)](#example-dark-sample)
[![YouTube: @sertai.official](https://img.shields.io/badge/YouTube-%40sertai.official-red)](https://www.youtube.com/@sertai.official)
[![License: MIT](https://img.shields.io/badge/License-MIT-green)](LICENSE)

<p align="center">
  <a href="examples/destiny-poison/"><img src="examples/destiny-poison/preview.gif" alt="Destiny Poison lyric video: condensed hook font with a pink to cyan word sweep under the cover art" width="270"></a>
  &nbsp;&nbsp;
  <a href="examples/dark-sample/sample.mp4"><img src="examples/dark-sample/sample.gif" alt="Dark-style lyric video sample: timed lines, punch and shake on the hook" width="320"></a>
</p>

<p align="center"><em>Left: <a href="examples/destiny-poison/">Destiny Poison</a> promo (9:16, gradients, word sweep, two fonts). Right: 9-second <code>dark</code> style sample (<a href="examples/dark-sample/sample.mp4">MP4 with audio</a>).</em></p>

**One JSON file is the whole edit.** Each lyric line gets a start time, an emphasis flag and a shake level, and can optionally carry its own font, colours, animation and word timings. The renderer brings each line in at its timestamp, shakes and glows the hooks, sweeps colour across the words as they are sung, blends colours from one line into the next, fades lines out before the next one lands, and encodes the result with the original audio. No timeline editor, no auto-captions that miss rap flows or non-English lyrics. Built by SERTAI LAB for independent artists who release their own videos.

## Easiest way to use it (no API, no code)

Open [`SKILL.md`](SKILL.md), copy the text and paste it into any AI chat assistant you already use.
Paste your lyrics and tell it where the hooks are.
It returns a timed `lyrics.json` with emphasis and shake marked, ready for the renderer, or as a cue sheet you can follow in any video editor.
The script steps below are optional, for people who want the render automated.

## Quick start (automated render)

Requirements: Python 3.9+ and ffmpeg. Three free display and text fonts are bundled in [`fonts/`](fonts/) (SIL Open Font License); any `.ttf` works too. librosa is only needed for beat detection; the renderer runs on Pillow and NumPy alone. Install help, including a virtual environment for systems that block `pip install`: [`docs/INSTALL.md`](docs/INSTALL.md).

```bash
git clone https://github.com/sertaiofficial-ops/lyric-video-engine.git
cd lyric-video-engine
pip install -r requirements.txt
# Debian/Ubuntu: sudo apt-get install ffmpeg fonts-liberation
# macOS: brew install ffmpeg   ·   Windows: winget install --id Gyan.FFmpeg -e
# librosa trouble? The renderer only needs: pip install pillow numpy (see docs/INSTALL.md)

# 1. Read the song's tempo, beats and onsets (an .mp4 works too: the audio is extracted)
python3 scripts/detect_beats.py song.mp3 beats.json

# 2. Write lyrics.json (see references/lyrics_format.md)
#    or import an .srt/.lrc you already have, with a format preset:
python3 scripts/import_subtitles.py song.srt lyrics.json --style dark --preset presets/vertical_9x16.json
#    optional: tighten line starts to real hits (moves lines only within 0.12 s);
#    verses to vocal onsets, hooks to the beat
python3 scripts/snap_to_beats.py lyrics.json beats.json --hook-grid beats

# 3. Render (stack a layout preset and a look preset; later presets win)
python3 scripts/render_lyric_video.py background.mp4 song.mp3 lyrics.json output.mp4 \
  --preset presets/vertical_9x16.json --preset presets/look_neon_gradient.json

# Quick checks before a full render
python3 scripts/render_lyric_video.py background.mp4 song.mp3 lyrics.json --stills 2.0,14.5 --stills-dir stills
python3 scripts/render_lyric_video.py background.mp4 song.mp3 lyrics.json test.mp4 --start 12 --duration 6
```

The audio can also be the background video itself (`background.mp4 background.mp4 ...`) when the clip already carries the song.

## How it works

1. **Beats.** [`detect_beats.py`](scripts/detect_beats.py) returns BPM, beat times and onset times, so you can snap each line to a real hit instead of a guessed grid.
2. **Timing.** In `lyrics.json` every line has `start`, `text`, `emphasis` and `shake`. A line stays on screen until the next one starts.
3. **Render.** [`render_lyric_video.py`](scripts/render_lyric_video.py) streams the background frames through memory (no temporary image files), darkens a soft band behind the text, and animates each line:
   - **Fonts:** one font and size for verses, another for hooks, or any font per line. Lines wider than the safe width shrink, then wrap onto two rows.
   - **Colour:** solid colours or gradients, a gradient that drifts across the line, a colour transition over the line (`color_to`), and a smooth blend from the previous line's colours (`color_blend`).
   - **Word sweep:** with word timings, each word lights up from left to right as it is sung, karaoke style.
   - **Entry:** `pop` (the original scale-in), `fade`, `fade_rise`, `blur_in`, `tracking_in` (letters close in from wide spacing) or `typewriter`, plus optional `punch` overshoot and `shake`.
   - **Glow:** a real coloured glow, in a fixed colour or the text's own colours, with adjustable strength and size.
   - **Exit:** `fade`, `fade_rise` or `blur_out`. Exits fade the text and band only; the footage underneath is never darkened.
4. **Encode.** Frames are piped straight into ffmpeg with the audio (trimmed to the clip length) to an H.264/AAC MP4 with fast start. Encoder tags and metadata are stripped from the file (`--keep-metadata` keeps them).

### Style presets

| Preset | Use when | Look |
|--------|----------|------|
| `dark` | Noir, melancholy, rap ballads | Gray glow, 60% band, white type |
| `neon` | Electronic, energetic | Cyan glow, 40% band, electric type |
| `minimal` | Clean, editorial | No glow, 30% band, clean type |

Look presets build on these: [`look_neon_gradient.json`](presets/look_neon_gradient.json) (Montserrat verses in a cyan to violet gradient, Bebas Neue hooks in pink to magenta with glow) and [`look_clean_cinematic.json`](presets/look_clean_cinematic.json) (white editorial type, Anton hooks, blur-in).

Every parameter (fonts, colours, gradients, glow, animations, word sweep, fit and wrap, band position, shake) is listed in [`references/lyrics_format.md`](references/lyrics_format.md).

### Formats

| Preset | Size | For |
|--------|------|-----|
| [`vertical_9x16.json`](presets/vertical_9x16.json) | 1080×1920 | Reels, Shorts, TikTok, Stories (text clear of platform UI) |
| [`square_1x1.json`](presets/square_1x1.json) | 1080×1080 | Feed posts |
| [`landscape_16x9.json`](presets/landscape_16x9.json) | 1920×1080 | YouTube |

### Fonts

| Name in JSON | Font | Use |
|--------------|------|-----|
| `bebas-neue` | Bebas Neue | Condensed all-caps display, hooks |
| `anton` | Anton | Heavy condensed display, hooks |
| `montserrat` | Montserrat SemiBold | Clean sans, verses |

All three are under the SIL Open Font License 1.1; license files sit next to each font in [`fonts/`](fonts/).

Details and vertical tips: [`presets/README.md`](presets/README.md).

## Example: Destiny Poison

A 19-second vertical promo: verses in Montserrat with a cyan to violet gradient that shifts a little on every line, hooks in Bebas Neue that track in on the beat and sweep from pink through magenta to cyan as each word is sung. The opening line sits in the empty top area while the cover title slides in, then the lyrics move under the title, clear of the album art and the bottom 12% platform UI. Settings, timings and notes: [`examples/destiny-poison/`](examples/destiny-poison/).

```json
{"start": 16.173, "text": "IRREPLACEABLE SPARK.", "emphasis": true, "shake": 4,
 "animation_in": "tracking_in", "punch": 0.05, "color_to": ["#D61EFF", "#33E9FF"],
 "words": [{"start": 16.2, "end": 17.3}, {"start": 17.3, "end": 17.9}]}
```

## Example: dark sample

The GIF above was rendered with the scripts in this repo. Background and beat are generated with ffmpeg, so the example is fully reproducible and contains no third-party media.

```json
{"start": 1.5, "text": "but I am still awake", "emphasis": false, "shake": 1},
{"start": 3.0, "text": "NO WAY BACK",          "emphasis": true,  "shake": 4},
{"start": 4.5, "text": "lights go out",         "emphasis": false, "shake": 0},
{"start": 6.0, "text": "HEAR THE SIGNAL",      "emphasis": true,  "shake": 5}
```

| Input | Output |
|-------|--------|
| [`lyrics.json`](examples/dark-sample/lyrics.json): 6 lines, 2 hooks | [`sample.mp4`](examples/dark-sample/sample.mp4): 9 s, 720×720, 30 fps |
| [`make_inputs.sh`](examples/dark-sample/make_inputs.sh): dark gradient clip + 120 BPM beat | [`beats.json`](examples/dark-sample/beats.json): 120.2 BPM, 17 beats |

Reproduce it: see [`examples/dark-sample/README.md`](examples/dark-sample/README.md).

## Repository layout

```
lyric-video-engine/
├── SKILL.md                     # Timing rules and workflow (paste into any AI chat)
├── references/
│   └── lyrics_format.md         # Full lyrics.json parameter reference
├── scripts/
│   ├── detect_beats.py          # Tempo, beat and onset detection (audio or video)
│   ├── import_subtitles.py      # SRT/LRC to lyrics.json, hook marking, LRC word timings
│   ├── snap_to_beats.py         # Tighten line starts to nearby beats/onsets
│   └── render_lyric_video.py    # Kinetic typography renderer
├── presets/                     # 9:16, 1:1, 16:9 layouts + look presets
├── fonts/                       # Bundled OFL fonts with their licenses
├── docs/
│   └── INSTALL.md               # ffmpeg per OS, librosa pitfalls
├── examples/
│   ├── destiny-poison/          # 9:16 promo: lyrics.json, preset, preview GIF
│   └── dark-sample/             # Trial render: inputs, lyrics.json, MP4, GIF
├── requirements.txt
└── LICENSE
```

## Tips

- Keep the type out of anything already on your background (titles, logos, faces): set `text_center_y` and `band_top`, or give one line its own `y` while the background is busy.
- Check a few frames with `--stills` before every full render; it takes seconds.
- Keep effects for the hook. Calm verses (`fade_rise`, soft gradient) make the hook's sweep and glow land harder.
- Memory use stays flat with song length, since frames are streamed.
- End with a `" "` line to clear the screen before the outro.

## License

Built by SERTAI LAB · [sertaiofficial.com](https://sertaiofficial.com) · YouTube [@sertai.official](https://www.youtube.com/@sertai.official)

Released under the [MIT License](LICENSE). © 2026 SERTAI LAB.
