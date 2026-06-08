#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"
OUT_DIR="${ROOT_DIR}/output/smoke"

mkdir -p "${OUT_DIR}"

"${VENV_DIR}/bin/edge-tts" \
  --file "${ROOT_DIR}/samples/demo_narration.txt" \
  --voice "zh-CN-XiaoxiaoNeural" \
  --rate "+0%" \
  --write-media "${OUT_DIR}/demo_narration.mp3" \
  --write-subtitles "${OUT_DIR}/demo_narration.vtt"

cp "${OUT_DIR}/demo_narration.vtt" "${OUT_DIR}/demo_narration.srt"

"${VENV_DIR}/bin/python" "${ROOT_DIR}/scripts/render_smoke_video.py"

"${VENV_DIR}/bin/auto-editor" \
  "${OUT_DIR}/demo_video.mp4" \
  -o "${OUT_DIR}/demo_video_auto.mp4" \
  --no-open

echo "Smoke test complete:"
echo "  ${OUT_DIR}/demo_video.mp4"
echo "  ${OUT_DIR}/demo_video_auto.mp4"
