# YouTube to MP3 (macOS)

Paste a list of YouTube links, click **Download MP3s**, and get one MP3 per link,
downloaded in order and numbered `01 - Title.mp3`, `02 - Title.mp3`, … so they stay
in that order in Finder and music players.

Built on [yt-dlp](https://github.com/yt-dlp/yt-dlp) and ffmpeg.

## Setup (once)

1. Install [Homebrew](https://brew.sh) if you don't have it.
2. Download this folder, open Terminal in it and run:
   ```bash
   chmod +x install.sh "YouTube to MP3.command"
   ./install.sh
   ```

## Use

Double-click **`YouTube to MP3.command`**. (If macOS blocks it the first time,
right-click it → **Open**.)

- Paste links, one per line, or **Load list from file…** (see `links-example.txt`).
- Choose the save folder (default `~/Music/YouTube MP3`) and quality (default 320 kbps).
- One bad link doesn't stop the batch; failed links are listed at the end.

### From Terminal

```bash
.venv/bin/python yt2mp3.py --cli links.txt -o ~/Desktop/mp3s -q 256
```

## If downloads stop working

YouTube changes frequently. Run `./update.sh` to get the latest yt-dlp.

Only download content you own or have permission to download.
