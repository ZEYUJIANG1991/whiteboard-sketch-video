#!/bin/bash
# Mux silent video + voiceover + BGM. Usage: mux.sh <silent.mp4> <vo.mp3> <bgm.mp3|none> <out.mp4>
set -e
SILENT=$1; VO=$2; BGM=$3; OUT=$4
mkdir -p "$(dirname "$OUT")"
DUR=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$SILENT")
FADE_ST=$(echo "$DUR - 3" | bc)
if [ "$BGM" = "none" ]; then
  ffmpeg -y -v error -i "$SILENT" -i "$VO" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k "$OUT"
else
  ffmpeg -y -v error -i "$SILENT" -i "$VO" -i "$BGM" -filter_complex \
  "[2:a]aloop=loop=-1:size=2e9,volume=0.10,afade=t=in:d=1.5,afade=t=out:st=${FADE_ST}:d=3[b];[1:a][b]amix=inputs=2:duration=longest:dropout_transition=0,atrim=0:${DUR}[a]" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -b:a 192k "$OUT"
fi
ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT"
