# Lyric Video Configuration Format

## JSON structure

```json
{
    "style": "dark",
    "width": 720,
    "height": 720,
    "fps": 30,
    "font_size_emphasis": 64,
    "font_size_normal": 46,
    "text_y": 400,
    "band_top": 380,
    "band_height": 180,
    "punch_duration": 0.35,
    "shake_intensity": 8,
    "fade_start": 0.85,
    "font_path": "/path/to/Font-Bold.ttf",
    "lyrics": [
        {"start": 0.2, "text": "tired of hearing you", "emphasis": false, "shake": 0},
        {"start": 2.0, "text": "THE PILLOW IS WET", "emphasis": true, "shake": 4},
        {"start": 3.5, "text": "but not from tears", "emphasis": false, "shake": 0}
    ]
}
```

## Parameters

| Parameter | Default | Range | Description |
|-----------|---------|-------|-------------|
| `style` | `"dark"` | dark / neon / minimal | Visual style preset |
| `width` / `height` | 720 | 480-1080 | Output resolution (the background is scaled and cropped to fit) |
| `fps` | 30 | 24 / 30 / 60 | Frame rate |
| `font_size_emphasis` | 64 | 48-96 | Emphasis line font size |
| `font_size_normal` | 46 | 32-60 | Normal line font size |
| `text_y` | 400 | 0-height | Vertical position of the text |
| `band_top` | 380 | 0-height | Top of the dark backdrop band |
| `band_height` | 180 | 120-240 | Height of the backdrop band |
| `punch_duration` | 0.35 | 0.2-0.6 | Punch-in animation length (seconds) |
| `shake_intensity` | 8 | 4-12 | Shake multiplier |
| `fade_start` | 0.85 | 0.7-0.95 | Point in the line (0-1) where fade-out begins |
| `font_path` | Liberation Sans Bold | any .ttf | Optional. Also settable with the `LYRIC_FONT` environment variable |

## Lyrics array

Each entry:
- `start` (float): time in seconds when the line appears. A line stays until the next one starts.
- `text` (string): the lyric line. Use `" "` to clear the screen.
- `emphasis` (bool): `true` = bigger type, glow, breathing drift; `false` = smaller, subtle.
- `shake` (int 0-5): shake strength during the punch-in (0 = none, 5 = maximum).

## Style presets

| Style | Text color | Glow | Backdrop | Vibe |
|-------|-----------|------|----------|------|
| `dark` | White | Gray, radius 8 | 60% | Noir, cold |
| `neon` | Cyan | Bright, radius 12 | 40% | Electric |
| `minimal` | White | None | 30% | Clean, editorial |
