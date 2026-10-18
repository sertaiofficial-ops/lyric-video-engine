# Presets

Two kinds of preset, stacked on the command line (later ones win over earlier ones and over `lyrics.json`):

```bash
python3 scripts/render_lyric_video.py bg.mp4 song.mp3 lyrics.json out.mp4 \
  --preset presets/vertical_9x16.json --preset presets/look_neon_gradient.json
```

The importer can also bake them into a new `lyrics.json`:

```bash
python3 scripts/import_subtitles.py song.srt lyrics.json --style dark --preset presets/vertical_9x16.json --look presets/look_neon_gradient.json
```

## Layout presets

| Preset | Size | For | Safe zone |
|--------|------|-----|-----------|
| `vertical_9x16.json` | 1080×1920 | Reels, Shorts, TikTok, Stories | Text band at about 60–65% height, clear of the top header and the bottom caption/buttons area |
| `square_1x1.json` | 1080×1080 | Feed posts | Band slightly below center |
| `landscape_16x9.json` | 1920×1080 | YouTube | Band in the lower third |

Vertical tips: keep lines to about 4 words (break long lines into two cues), keep the text between 55% and 65% of the height so platform UI never covers the hook, and keep the bottom 12% empty. Lines that are still too wide shrink to `safe_width`, then wrap.

## Look presets

| Preset | Verses | Hooks | Motion |
|--------|--------|-------|--------|
| `look_neon_gradient.json` | Montserrat, cyan to violet gradient | Bebas Neue, pink to magenta, coloured glow | Fade-rise in, fade out, colour blend between lines |
| `look_clean_cinematic.json` | Montserrat, soft white | Anton, white, no glow | Blur-in, fade out |

Bebas Neue and Anton are condensed: raise `font_size_emphasis` to about 1.5x when you use them. For per-word sweeps, add `words` timings to the hook lines in `lyrics.json` (see `references/lyrics_format.md`).

1080p renders stream frames straight into the encoder: about 20–30 frames per second at 1080×1920 on a modern CPU (the 20-second Destiny Poison example renders in under 30 seconds). Check a few frames with `--stills` first.

Built by SERTAI LAB.
