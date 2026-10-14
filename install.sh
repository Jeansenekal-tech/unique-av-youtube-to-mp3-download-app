#!/bin/bash
# One-time setup for YouTube to MP3 on macOS.
set -e
cd "$(dirname "$0")"

if ! command -v brew >/dev/null 2>&1; then
  echo "Homebrew is required. Install it from https://brew.sh, then run this again."
  exit 1
fi

echo "Installing Python, Tk and ffmpeg with Homebrew…"
brew install python python-tk ffmpeg

PYTHON="$(brew --prefix)/bin/python3"
echo "Creating private Python environment in .venv…"
"$PYTHON" -m venv .venv
.venv/bin/pip install --upgrade pip yt-dlp

chmod +x "YouTube to MP3.command" yt2mp3.py
echo
echo "Done. Double-click \"YouTube to MP3.command\" to start."
