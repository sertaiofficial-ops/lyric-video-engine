# Layout presets

Ready layouts for the three formats a release usually needs. Merge one into your `lyrics.json`, or pass it to the importer:

```bash
python3 scripts/import_subtitles.py song.srt lyrics.json --style dark --preset presets/vertical_9x16.json
```

| Preset | Size | For | Safe zone |
|--------|------|-----|-----------|
| `vertical_9x16.json` | 1080×1920 | Reels, Shorts, TikTok, Stories | Text band at about 60–65% height, clear of the top header and the bottom caption/buttons area |
| `square_1x1.json` | 1080×1080 | Feed posts | Band slightly below center |
| `landscape_16x9.json` | 1920×1080 | YouTube | Band in the lower third |

Vertical tips: keep lines to about 4 words (break long lines into two cues), and keep `text_y` between 55% and 65% of the height so platform UI never covers the hook.

Note: these presets are 1080p and render about 2–4× slower than the 720 default. Do a short test render first.

Built by SERTAI LAB.
