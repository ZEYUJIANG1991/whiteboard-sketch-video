#!/bin/bash
# Bootstrap the Python venv for the whiteboard engine. Run once; safe to re-run.
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV="$DIR/.venv"
if [ ! -x "$VENV/bin/python" ]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/pip" install -q -i https://pypi.tuna.tsinghua.edu.cn/simple \
  opencv-python-headless scikit-image scipy numpy pillow \
  || "$VENV/bin/pip" install -q opencv-python-headless scikit-image scipy numpy pillow
"$VENV/bin/python" -c "import cv2, skimage, scipy, PIL; print('venv ok:', '$VENV')"
