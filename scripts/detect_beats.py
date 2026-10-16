#!/usr/bin/env python3
"""
Beat detection for lyric video timing.
Analyzes audio file and outputs beat timestamps + tempo.

Usage:
    python3 detect_beats.py <audio_file> [output_json]

Output:
    JSON with tempo_bpm, beat_times, onset_times, duration
"""

import sys
import json
import numpy as np

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 detect_beats.py <audio.mp3> [output.json]")
        sys.exit(1)

    audio = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else "beats.json"

    import librosa
    import librosa.beat

    y, sr = librosa.load(audio, sr=None)
    tempo_vals, beats_frames = librosa.beat.beat_track(y=y, sr=sr)
    tempo = tempo_vals[0] if isinstance(tempo_vals, np.ndarray) else tempo_vals
    beat_times = librosa.frames_to_time(beats_frames, sr=sr)

    onset_frames = librosa.onset.onset_detect(y=y, sr=sr, backtrack=True)
    onset_times = librosa.frames_to_time(onset_frames, sr=sr)

    result = {
        "tempo_bpm": float(tempo),
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

if __name__ == "__main__":
    main()
