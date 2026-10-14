# YouTube to MP3 (macOS)

Paste a list of YouTube links, click **Download MP3s**, and get one MP3 per link,
downloaded in order and numbered `01 - Title.mp3`, `02 - Title.mp3`, … so they stay
in that order in Finder and music players.

## Install

1. Go to the [latest release](https://github.com/Jeansenekal-tech/unique-av-youtube-to-mp3-download-app/releases/latest)
   and download the DMG for your Mac:
   - **`…-arm64.dmg`** for Apple Silicon (M1/M2/M3/M4…)
   - **`…-x86_64.dmg`** for Intel Macs

   (Not sure? Apple menu → About This Mac: "Chip: Apple…" means arm64.)
2. Open the DMG and drag **YouTube to MP3** into **Applications**.
3. The first time, macOS will say it can't verify the developer (the app isn't
   Apple-notarized). Open **System Settings → Privacy & Security**, scroll down and
   click **Open Anyway**. You only need to do this once.

Everything it needs (yt-dlp and ffmpeg) is built in — no Homebrew or Python required.

## Use

- Paste links, one per line, or **Load list from file…** (see `links-example.txt`).
- Choose the save folder (default `~/Music/YouTube MP3`) and quality (default 320 kbps).
- One bad link doesn't stop the batch; failed links are listed at the end.

## Auto-update

Every time the app opens it checks, in the background:

- **The downloader engine (yt-dlp).** YouTube changes often, so the newest yt-dlp is
  downloaded automatically (checksum-verified) and used straight away.
- **The app.** If a newer release is on GitHub, it asks you; say yes and it downloads
  the new version, replaces itself and reopens. (If the app isn't in a writable
  place like Applications, it opens the new DMG for you to drag over instead.)

There's also a **Check for updates** button at the bottom of the window.

## Publishing a new version

Change the number in `VERSION` (e.g. `1.0.1`) and push it to `main`. GitHub Actions
builds the DMGs on Apple Silicon and Intel Macs, checks that each one can really
make an MP3, and publishes a release. Installed apps then offer the update.

Every push to any branch also builds the DMGs; you can download them from the
workflow run's **Artifacts** section without publishing a release.

To build locally on a Mac: `./build_dmg.sh 1.0.1` (output in `dist/`).

## Run from source

```bash
python3 -m venv .venv
.venv/bin/pip install yt-dlp imageio-ffmpeg certifi
.venv/bin/python yt2mp3.py                      # window
.venv/bin/python yt2mp3.py --cli links.txt -q 256   # Terminal
```

Only download content you own or have permission to download.
