#!/usr/bin/env python3
"""
Beat detection for lyric video timing.
Analyzes an audio file (or the audio track of a video) and outputs beat
timestamps, onset timestamps and tempo.

Usage:
    python3 scripts/detect_beats.py <audio_or_video> [output_json]

Accepts mp3, wav, flac, ... and video files such as mp4/mov/mkv/webm: if the
file cannot be read directly, its audio is extracted with ffmpeg first.

Output:
    JSON with tempo_bpm, beat_times, onset_times, duration

Built by SERTAI LAB. MIT License.
"""

import os
import subprocess
import sys
import tempfile

import numpy as np

VIDEO_EXT = {".mp4", ".mov", ".m4v", ".mkv", ".webm", ".avi"}


def load_audio(path, librosa):
    if os.path.splitext(path)[1].lower() not in VIDEO_EXT:
        try:
            return librosa.load(path, sr=None)
        except Exception as e:  # unsupported container or missing decoder
            print(f"Direct load failed ({type(e).__name__}); extracting audio with ffmpeg")
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    try:
        r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-vn", "-ac", "1",
                            "-ar", "44100", tmp.name], capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit(f"ffmpeg could not read audio from {path}:\n{r.stderr[-800:]}")
        return librosa.load(tmp.name, sr=None)
    finally:
        os.unlink(tmp.name)


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/detect_beats.py <audio_or_video> [output.json]")
        sys.exit(1)

    audio = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "beats.json"

    import json
    import librosa
    import librosa.beat

    y, sr = load_audio(audio, librosa)
    tempo_vals, beats_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = float(np.atleast_1d(tempo_vals)[0])
    beat_times = librosa.frames_to_time(beats_frames, sr=sr)

    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    result = {
        "tempo_bpm": tempo,
        "beat_times": [round(float(t), 3) for t in beat_times],
        "onset_times": [round(float(t), 3) for t in onset_times],
        "duration": float(len(y) / sr)
    }

    with open(output, "w") as f:
        json.dump(result, f, indent=2)

    print(f"Tempo: {tempo:.1f} BPM")
    print(f"Beats: {len(beat_times)}")
    print(f"Duration: {result['duration']:.2f}s")
    print(f"Saved: {output}")
    print("Note: tempo can read as 2x, 1/2x or 4/3x of the felt tempo; check it by ear.")


if __name__ == "__main__":
    main()
