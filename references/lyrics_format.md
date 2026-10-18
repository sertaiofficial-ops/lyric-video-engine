# Lyric Video Configuration Format

One JSON file describes the whole edit: global settings plus a `lyrics` array.
Every setting is optional. Files written for earlier versions (only `start`, `text`,
`emphasis`, `shake` and the layout keys) still render as before.

Settings are merged in this order: built-in defaults < `lyrics.json` < each `--preset`
file passed to the renderer (later presets win). Most per-look settings can also be
set on a single line, which wins over everything else.

## Minimal file

```json
{
    "style": "dark",
    "lyrics": [
        {"start": 0.2, "text": "tired of hearing you", "emphasis": false, "shake": 0},
        {"start": 2.0, "text": "THE PILLOW IS WET", "emphasis": true, "shake": 4},
        {"start": 3.5, "text": "but not from tears"}
    ]
}
```

## Full example (one verse line, one hook with a word sweep)

```json
{
    "width": 1080, "height": 1920, "fps": 30,
    "font_normal": "montserrat", "font_size_normal": 64,
    "font_emphasis": "bebas-neue", "font_size_emphasis": 150,
    "text_center_y": 1590, "band_top": 1480, "band_height": 220,
    "gradient_normal": ["#2EE6FF", "#8A5CFF"],
    "gradient_emphasis": ["#FF2E97", "#D61EFF"],
    "gradient_speed": 0.12, "color_blend": 0.45,
    "glow_color": "text", "glow_strength": 0.7, "glow_radius": 14,
    "animation_in": "fade_rise", "animation_out": "fade", "exit_duration": 0.35,
    "lyrics": [
        {"start": 5.22, "text": "before your voice fades,"},
        {"start": 13.97, "text": "UNFORGETTABLE,", "emphasis": true, "shake": 3,
         "animation_in": "tracking_in", "punch": 0.05,
         "color_to": ["#D61EFF", "#33E9FF"],
         "words": [{"start": 13.96, "end": 14.78}]}
    ]
}
```

## Layout and output

| Parameter | Default | Description |
|-----------|---------|-------------|
| `width` / `height` | 720 | Output size. The background is scaled and cropped to fill it |
| `fps` | 30 | Frame rate (24 / 30 / 60) |
| `text_y` | 400 | Top of the text (older layout key). Text is centred at `text_y + font size / 2` |
| `text_center_y` | none | Vertical centre of the text. Wins over `text_y` |
| `band_top` / `band_height` | 380 / 180 | Soft dark backdrop band behind the text |
| `band` | true | `false` turns the band off |
| `backdrop_opacity` | per style | Band strength, 0–1 |
| `safe_width` | 0.9 | Max text width, as a fraction of the width (or pixels if > 1) |
| `min_font_scale` | 0.72 | A long line shrinks down to this scale; below it, the line wraps onto two rows (then shrinks again if needed) |
| `wrap` | true | `false` = only shrink, never wrap |
| `line_spacing` | 1.1 | Row spacing for wrapped lines, as a multiple of the font size |
| `x264_preset` / `crf` | medium / 17 | Encoder speed and quality |

## Fonts

| Parameter | Default | Description |
|-----------|---------|-------------|
| `font_normal` / `font_emphasis` | none | Font for verse lines and for hooks |
| `font_size_normal` / `font_size_emphasis` | 46 / 64 | Sizes in pixels |
| `font_path` | Liberation Sans Bold | Fallback font for everything (older key). Also settable with `LYRIC_FONT` |
| `letter_spacing` | 0 | Extra pixels between letters |

A font is a bundled name (`bebas-neue`, `anton`, `montserrat`), an absolute path, or a path
relative to the lyrics/preset file, the repo, or `fonts/`. Bundled fonts are under the SIL
Open Font License (see `fonts/`).

## Colour

| Parameter | Default | Description |
|-----------|---------|-------------|
| `text_normal` / `text_emphasis` | per style | Solid colours (`"#RRGGBB"` or `[r, g, b]`). `text_main` is still accepted for the emphasis colour |
| `gradient_normal` / `gradient_emphasis` | none | Gradient across the line: a list of 2+ colours |
| `gradient_angle` | 0 | Gradient direction in degrees (0 = left to right, 90 = top to bottom) |
| `gradient_speed` | 0 | Moves the gradient across the line (cycles per second; 0.1–0.2 is subtle). Moves back and forth, so it has no seam |
| `hue_shift` | 0 | Slow hue drift in degrees per second over the whole video |
| `color_blend` | 0 | Seconds over which each line's colours blend in from the previous line's colours |
| `glow_color` | per style | Glow colour, or `"text"` to glow in the text's own colours |
| `glow_strength` | per style | Hook glow strength (0 = off, about 0.5–1.0 typical) |
| `glow_radius` | per style | Glow size in pixels (scaled with the font size) |
| `glow_normal` | 0 | Glow strength for verse lines (0 = none, as before) |
| `shadow` / `shadow_opacity` | per style / 0.75 | Soft drop shadow under the text |

## Animation

| Parameter | Default | Description |
|-----------|---------|-------------|
| `animation_in` | `pop` | `pop` (scale-in, the original effect), `fade`, `fade_rise`, `blur_in`, `tracking_in`, `typewriter`, `none` |
| `animation_out` | `fade` | `fade`, `fade_rise`, `blur_out`, `none`. Exits fade the text and band only; the background is never darkened |
| `entry_duration` | 0.4 (pop: `punch_duration`) | Entry length in seconds. Typewriter defaults to about 45 ms per letter |
| `exit_duration` | none | Exit length in seconds. If unset, the exit starts at `fade_start` |
| `fade_start` | 0.85 | Point in the line (0–1) where the exit begins, when `exit_duration` is not set |
| `punch_duration` | 0.35 | Length of the pop and of the shake |
| `punch` | 0 | Extra scale overshoot on entry, e.g. 0.05 = 5% bigger, settling to 100% |
| `shake_intensity` | 8 | Shake multiplier (pixels per shake level) |
| `rise` | 0.35 | Rise distance for `fade_rise`, as a fraction of the font size |
| `blur_amount` | 14 | Start/end blur in pixels for `blur_in` / `blur_out` |
| `tracking` | 0.3 | Starting extra letter spacing for `tracking_in`, as a fraction of the font size (kept inside the frame automatically) |
| `breathe` | true | Slow breathing drift on hooks while they hold |

## Word sweep (karaoke highlight)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `sweep` | true | Use the sweep when a line has `words` |
| `sweep_dim` | 0.42 | Brightness of the not-yet-sung part |
| `sweep_softness` | 28 | Width of the soft sweep edge in pixels |

## Lyrics array

Each entry:
- `start` (seconds): when the line appears. A line holds until the next one starts.
- `end` (seconds, optional): clear the line earlier than the next start.
- `text`: the lyric line. Use `" "` to clear the screen.
- `emphasis` (bool): hook line. Uses the emphasis font, size, colours and glow.
- `shake` (0–5): shake strength during the entry.
- `words` (optional): one entry per word, in order. Either start times (`[13.96, 14.40]`)
  or objects (`[{"start": 13.96, "end": 14.78}]`). Enables the word sweep.
- `color` (optional): this line's colour or gradient (one colour or a list).
- `color_to` (optional): colour or gradient the line transitions to over its duration.
- `font`, `font_size` (optional): this line's font and size.
- `y` (optional): vertical centre for this line only (the band follows it), e.g. to put an
  intro line in a different empty zone of the background.
- Any animation, colour, glow, shadow, band or fit setting above can also be set per line:
  `letter_spacing`, `animation_in`, `animation_out`, `entry_duration`, `exit_duration`, `rise`,
  `blur_amount`, `tracking`, `punch`, `breathe`, `gradient_speed`, `gradient_angle`, `hue_shift`,
  `color_blend`, `sweep`, `sweep_dim`, `sweep_softness`, `glow_color`, `glow_strength`,
  `glow_radius`, `shadow`, `shadow_opacity`, `backdrop_opacity`, `fade_start`, `band_top`,
  `band_height`, `band`, `wrap`, `safe_width`.

## Styles

| Style | Verse / hook colour | Glow | Band | Vibe |
|-------|---------------------|------|------|------|
| `dark` | Light gray / white | Soft gray | 60% | Noir, cold |
| `neon` | Pale cyan / cyan | Bright cyan | 40% | Electric |
| `minimal` | Gray / white | None | 30% | Clean, editorial |

A style only sets starting values; any colour, glow, band or shadow key overrides it.

Built by SERTAI LAB.
