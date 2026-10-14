#!/bin/bash
# Double-click this file in Finder to open YouTube to MP3.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "First run: setting things up…"
  ./install.sh || { read -p "Setup failed. Press Return to close."; exit 1; }
fi
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"
.venv/bin/python yt2mp3.py "$@"
