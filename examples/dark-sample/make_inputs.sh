#!/usr/bin/env bash
# Generates a synthetic background clip and a 120 BPM test beat, so the
# example renders without any copyrighted footage or music.
set -euo pipefail
cd "$(dirname "$0")"
ffmpeg -y -loglevel error -f lavfi \
  -i "gradients=s=720x720:d=9:r=30:c0=0x020306:c1=0x2a3550:c2=0x07090f:n=3:speed=0.03,vignette=PI/4" \
  -c:v libx264 -pix_fmt yuv420p background.mp4
ffmpeg -y -loglevel error -f lavfi \
  -i "aevalsrc='0.9*sin(2*PI*52*t)*exp(-14*mod(t,0.5))+0.25*sin(2*PI*110*t)*exp(-2*mod(t,2))+0.08*(random(0)-0.5)*exp(-40*mod(t+0.25,0.5))':s=44100:d=9" \
  -c:a libmp3lame -b:a 192k beat.mp3
echo "Created background.mp4 and beat.mp3"
