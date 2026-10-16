# Example: dark sample

A 9-second trial render in the `dark` style. Background and beat are generated
with ffmpeg (no third-party footage or music); the lyrics are placeholder lines.

| File | What it is |
|------|------------|
| [`make_inputs.sh`](make_inputs.sh) | Generates `background.mp4` (drifting dark gradient) and `beat.mp3` (120 BPM test beat) |
| [`lyrics.json`](lyrics.json) | Timed lines; the two hooks use `emphasis` and `shake` |
| [`beats.json`](beats.json) | Output of `detect_beats.py` on `beat.mp3` |
| [`sample.mp4`](sample.mp4) | Rendered result, 720x720, 30 fps, with audio |
| [`sample.gif`](sample.gif) | Silent preview of the same render |

Reproduce from the repo root:

```bash
./examples/dark-sample/make_inputs.sh
python3 scripts/detect_beats.py examples/dark-sample/beat.mp3 examples/dark-sample/beats.json
python3 scripts/render_lyric_video.py examples/dark-sample/background.mp4 examples/dark-sample/beat.mp3 examples/dark-sample/lyrics.json examples/dark-sample/sample.mp4
```
