# Install notes

## ffmpeg

| OS | Command |
|----|---------|
| Debian / Ubuntu | `sudo apt-get install ffmpeg fonts-liberation` |
| macOS (Homebrew) | `brew install ffmpeg` |
| Windows (winget) | `winget install --id Gyan.FFmpeg -e` (then open a new terminal) |
| Windows (Chocolatey) | `choco install ffmpeg` |

Check: `ffmpeg -version` and `ffprobe -version` must both work.

Fonts: Bebas Neue, Anton and Montserrat SemiBold are bundled in `fonts/` and are used by name (`"font_emphasis": "bebas-neue"`). When no font is set, Linux uses Liberation Sans Bold, macOS Arial Bold, Windows `arialbd.ttf`, and the bundled Montserrat as a last resort. Any `.ttf`/`.otf` works via `"font_path"`, `"font_normal"`, `"font_emphasis"`, a line's `"font"`, or the `LYRIC_FONT` environment variable.

## Python packages

Use a virtual environment. Recent Linux distributions and Homebrew Python refuse a plain
`pip install` with `error: externally-managed-environment`; a venv avoids that and keeps
librosa's dependencies away from your system Python.

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Afterwards, run the scripts with the venv active (or call `.venv/bin/python scripts/...` directly).

### The renderer does not need librosa

`render_lyric_video.py` only uses Pillow and NumPy. If librosa fails to install, you can still render:

```bash
pip install pillow numpy
```

librosa is only used by `detect_beats.py`. Without it, time lines by ear (that is the recommended method anyway) and skip `snap_to_beats.py`.

### librosa pitfalls

- **Newest Python versions:** librosa depends on `numba`, which often lags behind new Python releases. If install fails, use Python 3.10–3.12 in a virtual environment.
- **MP3 or video loading errors** (`NoBackendError`, `Format not recognised`): `detect_beats.py` now extracts the audio with ffmpeg automatically when a file cannot be read directly, so video files (`.mp4`, `.mov`, ...) work as input. If it still fails, convert by hand: `ffmpeg -i song.mp3 song.wav`.
- **Apple Silicon:** install inside a fresh venv; if `numba`/`llvmlite` fails, `pip install --upgrade pip` then retry.
- **Slow first run:** numba compiles on first use; the second run is much faster.

Built by SERTAI LAB.
