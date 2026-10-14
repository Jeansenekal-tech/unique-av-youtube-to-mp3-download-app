#!/bin/bash
# YouTube changes often; run this if downloads start failing.
cd "$(dirname "$0")"
.venv/bin/pip install --upgrade yt-dlp
