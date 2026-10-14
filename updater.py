"""Auto-update for YouTube to MP3.

Two things update independently:
  * yt-dlp (the downloader engine) — YouTube changes often, so the newest yt-dlp
    release is fetched in the background on every launch and stored in
    ~/Library/Application Support. It's a zip that Python can import from directly.
  * the app itself — new versions are published as DMGs on this repo's GitHub
    Releases. When one is found the user is asked, then the DMG is downloaded and
    a small script swaps the new .app in after the app quits, and relaunches it.
"""

import hashlib
import json
import os
import platform
import re
import shutil
import ssl
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

try:
    from _version import __version__
except ImportError:  # running from source without a build
    __version__ = "0.0.0-dev"

GITHUB_REPO = "Jeansenekal-tech/unique-av-youtube-to-mp3-download-app"
SUPPORT_DIR = Path.home() / "Library" / "Application Support" / "YouTube to MP3"
CACHED_YTDLP = SUPPORT_DIR / "yt-dlp.zip"
FROZEN = getattr(sys, "frozen", False)
BUNDLED_YTDLP = Path(getattr(sys, "_MEIPASS", ".")) / "yt-dlp.zip" if FROZEN else None


def _ssl_context():
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


def _get(url, timeout=20):
    request = urllib.request.Request(url, headers={"User-Agent": f"YouTube-to-MP3/{__version__}"})
    return urllib.request.urlopen(request, timeout=timeout, context=_ssl_context())


def _get_json(url):
    with _get(url) as response:
        return json.load(response)


def version_tuple(text):
    """'v1.2.3' / '2026.10.01' / '2026.10.01.1' -> comparable tuple of ints."""
    return tuple(int(part) for part in re.findall(r"\d+", text or ""))


# ---------------------------------------------------------------- yt-dlp engine


def zip_ytdlp_version(path):
    """Read the yt-dlp version out of a yt-dlp zipapp, or None if it isn't one."""
    try:
        with zipfile.ZipFile(path) as archive:
            source = archive.read("yt_dlp/version.py").decode()
        match = re.search(r"__version__\s*=\s*['\"]([^'\"]+)", source)
        return match.group(1) if match else None
    except (OSError, KeyError, zipfile.BadZipFile):
        return None


def activate_ytdlp():
    """Put the newest available yt-dlp first on sys.path. Call before importing yt_dlp."""
    candidates = []
    for path in (CACHED_YTDLP, BUNDLED_YTDLP):
        if path and path.exists():
            version = zip_ytdlp_version(path)
            if version:
                candidates.append((version_tuple(version), str(path)))
    if candidates:
        sys.path.insert(0, max(candidates)[1])


def current_ytdlp_version():
    import yt_dlp.version

    return yt_dlp.version.__version__


def update_ytdlp(log=print):
    """Download the latest yt-dlp release if it's newer than the one in use. Returns the new version or None."""
    current = current_ytdlp_version()
    release = _get_json("https://api.github.com/repos/yt-dlp/yt-dlp/releases/latest")
    latest = release["tag_name"]
    if version_tuple(latest) <= version_tuple(current):
        return None

    assets = {asset["name"]: asset["browser_download_url"] for asset in release["assets"]}
    if "yt-dlp" not in assets or "SHA2-256SUMS" not in assets:
        return None
    with _get(assets["SHA2-256SUMS"]) as response:
        sums = dict(reversed(line.split()) for line in response.read().decode().splitlines() if line.strip())

    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp = CACHED_YTDLP.with_suffix(".download")
    with _get(assets["yt-dlp"], timeout=120) as response, open(temp, "wb") as out:
        shutil.copyfileobj(response, out)

    digest = hashlib.sha256(temp.read_bytes()).hexdigest()
    if digest != sums.get("yt-dlp") or zip_ytdlp_version(temp) is None:
        temp.unlink(missing_ok=True)
        raise RuntimeError("downloaded yt-dlp failed verification")
    os.replace(temp, CACHED_YTDLP)

    # If yt_dlp hasn't been imported yet this session, the new one is used straight away.
    sys.path.insert(0, str(CACHED_YTDLP))
    return latest


# ---------------------------------------------------------------- the app itself


def check_app_update():
    """Return (version, dmg_url) if a newer app release exists for this Mac's CPU, else None."""
    release = _get_json(f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest")
    latest = release["tag_name"].lstrip("v")
    if version_tuple(latest) <= version_tuple(__version__):
        return None
    arch = "arm64" if platform.machine() == "arm64" else "x86_64"
    for asset in release["assets"]:
        if asset["name"].endswith(f"-{arch}.dmg"):
            return latest, asset["browser_download_url"]
    return None


def app_bundle_path():
    """The running .app bundle, or None when running from source."""
    if not FROZEN:
        return None
    path = Path(sys.executable).resolve()
    for parent in path.parents:
        if parent.suffix == ".app":
            return parent
    return None


def download_dmg(url, progress=lambda fraction: None):
    target = Path(tempfile.gettempdir()) / Path(url).name
    with _get(url, timeout=120) as response, open(target, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        done = 0
        while chunk := response.read(256 * 1024):
            out.write(chunk)
            done += len(chunk)
            if total:
                progress(done / total)
    return target


_INSTALL_SCRIPT = r"""#!/bin/bash
APP="$1"; DMG="$2"; PID="$3"
while kill -0 "$PID" 2>/dev/null; do sleep 0.5; done
MNT="$(mktemp -d)"
if hdiutil attach -nobrowse -readonly -mountpoint "$MNT" "$DMG"; then
  NEW="$(find "$MNT" -maxdepth 1 -name '*.app' | head -n 1)"
  if [ -n "$NEW" ] && ditto "$NEW" "$APP.updating"; then
    rm -rf "$APP" && mv "$APP.updating" "$APP"
    xattr -dr com.apple.quarantine "$APP" 2>/dev/null
  fi
  rm -rf "$APP.updating"
  hdiutil detach "$MNT" -quiet
fi
rm -f "$DMG" "$0"
open "$APP"
"""


def can_self_install():
    """True when the running .app can be replaced in place (not on the DMG or in a read-only spot)."""
    app = app_bundle_path()
    return bool(app) and not str(app).startswith("/Volumes/") and os.access(app.parent, os.W_OK)


def install_and_relaunch(dmg_path):
    """Start the swap-in script, which waits for this process to exit. Caller should then quit."""
    app = app_bundle_path()
    script = Path(tempfile.gettempdir()) / "yt2mp3-install-update.sh"
    script.write_text(_INSTALL_SCRIPT)
    script.chmod(0o755)
    subprocess.Popen(
        ["/bin/bash", str(script), str(app), str(dmg_path), str(os.getpid())],
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
