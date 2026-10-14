#!/bin/bash
# Build "YouTube to MP3.app" and wrap it in a DMG. Runs on macOS (locally or in GitHub Actions).
#   ./build_dmg.sh 1.0.0
set -euo pipefail
cd "$(dirname "$0")"

VERSION="${1:-0.0.0}"
ARCH="$(uname -m)"
DMG="dist/YouTube-to-MP3-$VERSION-$ARCH.dmg"

rm -rf build dist
mkdir -p build
python3 -m venv build/venv
build/venv/bin/pip install --quiet --upgrade pip
build/venv/bin/pip install --quiet -r requirements-build.txt

echo "__version__ = \"$VERSION\"" > _version.py
curl -fsSL -o build/yt-dlp.zip https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp

APP_VERSION="$VERSION" build/venv/bin/pyinstaller --noconfirm --clean --distpath dist --workpath build/pyinstaller yt2mp3.spec

# Prove the bundled yt-dlp + ffmpeg really make an MP3 before shipping.
"dist/YouTube to MP3.app/Contents/MacOS/YouTube to MP3" --self-test

mkdir -p build/dmg
cp -R "dist/YouTube to MP3.app" build/dmg/
ln -s /Applications build/dmg/Applications
hdiutil create -volname "YouTube to MP3" -srcfolder build/dmg -ov -format UDZO "$DMG"
echo "Built $DMG"
