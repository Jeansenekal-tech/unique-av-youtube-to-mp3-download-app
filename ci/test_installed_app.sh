#!/bin/bash
# Install the DMG the way a person would, then exercise the installed app. Runs on GitHub's macOS runners.
#   ci/test_installed_app.sh path/to/YouTube-to-MP3.dmg
set -uo pipefail
DMG="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
APP="/Applications/YouTube to MP3.app"
BIN="$APP/Contents/MacOS/YouTube to MP3"
OUT="${RUNNER_TEMP:-/tmp}/install-test"
mkdir -p "$OUT"
FAIL=0
step() { echo; echo "=== $* ==="; }
check() { if "$@"; then echo "PASS"; else echo "FAIL"; FAIL=1; fi; }

step "Install: mount DMG and copy app to /Applications"
MNT="$(mktemp -d)"
hdiutil attach -nobrowse -readonly -mountpoint "$MNT" "$DMG" >/dev/null
ls -la "$MNT"
rm -rf "$APP"
ditto "$MNT/YouTube to MP3.app" "$APP"
hdiutil detach "$MNT" -quiet
check test -x "$BIN"
/usr/libexec/PlistBuddy -c "Print :CFBundleShortVersionString" "$APP/Contents/Info.plist"
codesign --verify --deep --verbose=1 "$APP" && echo "signature OK (ad-hoc)"

step "Installed app converts audio (offline self-test)"
check "$BIN" --self-test

step "Launch the window like a double-click and take a screenshot"
open "$APP"
sleep 12
if pgrep -f "YouTube to MP3.app/Contents/MacOS" >/dev/null; then echo "PASS: app is running"; else echo "FAIL: app not running"; FAIL=1; fi
screencapture -x "$OUT/app-window.png" && echo "screenshot saved" || echo "(screenshot not permitted on this runner)"
pkill -f "YouTube to MP3.app/Contents/MacOS"; sleep 2

step "Real YouTube download (YouTube often blocks cloud servers, so this is informational)"
printf 'https://www.youtube.com/watch?v=jNQXAC9IVRw\n' > "$OUT/links.txt"
if "$BIN" --cli "$OUT/links.txt" -o "$OUT/mp3" -q 128; then
  ls -la "$OUT/mp3"; file "$OUT"/mp3/*.mp3
  echo "YOUTUBE: PASS"
else
  echo "YOUTUBE: did not complete (see message above)"
fi

step "Self-update: app replaces itself from a DMG and relaunches"
touch "$APP/Contents/Resources/old-install-marker"
"$BIN" --install-update "$(cp "$DMG" "$OUT/update.dmg" && echo "$OUT/update.dmg")"
for _ in $(seq 1 60); do
  [ ! -e "$APP/Contents/Resources/old-install-marker" ] && pgrep -f "YouTube to MP3.app/Contents/MacOS" >/dev/null && break
  sleep 1
done
check test ! -e "$APP/Contents/Resources/old-install-marker"
if pgrep -f "YouTube to MP3.app/Contents/MacOS" >/dev/null; then echo "PASS: relaunched after update"; else echo "FAIL: not relaunched"; FAIL=1; fi
check test -x "$BIN"
sleep 3
screencapture -x "$OUT/after-update.png" || true
pkill -f "YouTube to MP3.app/Contents/MacOS"

echo
[ "$FAIL" = 0 ] && echo "ALL INSTALL TESTS PASSED" || echo "SOME INSTALL TESTS FAILED"
exit $FAIL
