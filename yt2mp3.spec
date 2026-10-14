# PyInstaller spec for the macOS app. Built by build_dmg.sh.
import glob
import os

import imageio_ffmpeg

version = os.environ.get("APP_VERSION", "0.0.0")
ffmpeg_dir = os.path.join(os.path.dirname(imageio_ffmpeg.__file__), "binaries")

a = Analysis(
    ["yt2mp3.py"],
    # yt-dlp ships as a zip next to the app so it can be swapped for newer versions
    # (see updater.py). It is still analysed here so the stdlib modules it needs get bundled.
    hiddenimports=["yt_dlp"],
    datas=[("build/yt-dlp.zip", ".")],
    binaries=[(path, "imageio_ffmpeg/binaries") for path in glob.glob(os.path.join(ffmpeg_dir, "ffmpeg-*"))],
)
# Drop the analysed copy of yt_dlp so every yt_dlp import comes from the zip, never a mix of versions.
a.pure = [entry for entry in a.pure if entry[0] != "yt_dlp" and not entry[0].startswith("yt_dlp.")]

pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="YouTube to MP3", console=False)
coll = COLLECT(exe, a.binaries, a.datas, name="YouTube to MP3")
app = BUNDLE(
    coll,
    name="YouTube to MP3.app",
    bundle_identifier="tech.jeansenekal.youtube-to-mp3",
    version=version,
    info_plist={
        "CFBundleShortVersionString": version,
        "CFBundleVersion": version,
        "NSHighResolutionCapable": True,
        "LSMinimumSystemVersion": "11.0",
    },
)
