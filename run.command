#!/usr/bin/env bash
# ReelGeek launcher for macOS -- double-click this file.
cd "$(dirname "$0")" || exit 1
PY=$(command -v python3 || command -v python)
if [ -z "$PY" ]; then
  echo "Python 3 is not installed. Get it from https://www.python.org/downloads/"
  read -r -p "Press return to close."; exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is missing. Install it with:  brew install ffmpeg"
  read -r -p "Press return to close."; exit 1
fi
"$PY" -m pip install --quiet --disable-pip-version-check -r requirements.txt 2>/dev/null
"$PY" -m reelgeek
read -r -p "ReelGeek has stopped. Press return to close."
