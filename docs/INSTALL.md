# Install notes

## ffmpeg

| OS | Command |
|----|---------|
| Debian / Ubuntu | `sudo apt-get install ffmpeg fonts-liberation` |
| macOS (Homebrew) | `brew install ffmpeg` |
| Windows (winget) | `winget install --id Gyan.FFmpeg -e` (then open a new terminal) |
| Windows (Chocolatey) | `choco install ffmpeg` |

Check: `ffmpeg -version` and `ffprobe -version` must both work.

Fonts: Linux uses Liberation Sans Bold, macOS falls back to Arial Bold, Windows to `arialbd.ttf`. Any bold `.ttf` works via `"font_path"` or the `LYRIC_FONT` environment variable.

## Python packages

```bash
pip install -r requirements.txt
```

### The renderer does not need librosa

`render_lyric_video.py` only uses Pillow and NumPy. If librosa fails to install, you can still render:

```bash
pip install pillow numpy
```

librosa is only used by `detect_beats.py`. Without it, time lines by ear (that is the recommended method anyway) and skip `snap_to_beats.py`.

### librosa pitfalls

- **Newest Python versions:** librosa depends on `numba`, which often lags behind new Python releases. If install fails, use Python 3.10–3.12 in a virtual environment.
- **MP3 loading errors** (`NoBackendError` / audioread): convert first with `ffmpeg -i song.mp3 song.wav` and run beat detection on the WAV.
- **Apple Silicon:** install inside a fresh venv; if `numba`/`llvmlite` fails, `pip install --upgrade pip` then retry.
- **Slow first run:** numba compiles on first use; the second run is much faster.

Virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Built by SERTAI LAB.
