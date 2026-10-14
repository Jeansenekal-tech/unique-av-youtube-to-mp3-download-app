#!/usr/bin/env python3
"""YouTube to MP3 — download a list of YouTube links, in order, as MP3 files.

Run with no arguments for the window, or from Terminal:
    python3 yt2mp3.py --cli links.txt [-o ~/Music/YouTube MP3] [-q 320]
"""

import argparse
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("yt-dlp is not installed. Run ./install.sh first.")

DEFAULT_OUTPUT = Path.home() / "Music" / "YouTube MP3"
QUALITIES = ["320", "256", "192", "128"]


def parse_links(text):
    """Return the links in text, one per line, in order. Blank lines and # comments are skipped."""
    links = []
    for line in text.splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            links.append(line)
    return links


class _QuietLogger:
    def debug(self, msg):
        pass

    warning = error = debug


def find_ffmpeg():
    """Finder-launched apps get a minimal PATH, so also look in Homebrew's usual places."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    for candidate in ("/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"):
        if os.path.exists(candidate):
            return candidate
    return None


def download_all(links, output_dir, quality, log, progress, should_stop=lambda: False, numbered=True):
    """Download links one at a time, in order. Returns the list of links that failed."""
    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg was not found. Install it with: brew install ffmpeg")

    output_dir = Path(output_dir).expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    width = max(2, len(str(len(links))))
    failed = []

    for index, link in enumerate(links, start=1):
        if should_stop():
            log("Stopped.")
            break

        prefix = f"{index:0{width}d} - " if numbered else ""
        log(f"[{index}/{len(links)}] {link}")

        def hook(d, index=index):
            if d["status"] == "downloading":
                total = d.get("total_bytes") or d.get("total_bytes_estimate")
                if total:
                    progress(index, d.get("downloaded_bytes", 0) / total)
            elif d["status"] == "finished":
                progress(index, 1.0)
                log("    converting to MP3…")

        options = {
            "format": "bestaudio/best",
            "outtmpl": str(output_dir / f"{prefix}%(title)s.%(ext)s"),
            "noplaylist": True,
            "ffmpeg_location": ffmpeg,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": quality},
                {"key": "FFmpegMetadata"},
            ],
            "progress_hooks": [hook],
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "logger": _QuietLogger(),  # errors are reported once, below
        }

        try:
            with yt_dlp.YoutubeDL(options) as ydl:
                info = ydl.extract_info(link, download=True)
            log(f"    done: {prefix}{info.get('title', link)}.mp3")
        except Exception as error:  # keep going with the rest of the list
            message = re.sub(r"\x1b\[[0-9;]*m", "", str(error))
            log(f"    FAILED: {message}")
            failed.append(link)

    return failed


def run_cli(args):
    text = Path(args.cli).read_text() if args.cli != "-" else sys.stdin.read()
    links = parse_links(text)
    if not links:
        sys.exit("No links found.")

    def progress(index, fraction):
        print(f"\r    {fraction:4.0%}", end="", flush=True)
        if fraction >= 1:
            print()

    failed = download_all(links, args.output, args.quality, print, progress, numbered=not args.no_numbers)
    print(f"\nFinished: {len(links) - len(failed)} of {len(links)} saved to {Path(args.output).expanduser()}")
    if failed:
        print("Failed links:\n  " + "\n  ".join(failed))
        sys.exit(1)


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
    from tkinter.scrolledtext import ScrolledText

    root = tk.Tk()
    root.title("YouTube to MP3")
    root.geometry("720x620")
    root.minsize(520, 480)

    events = queue.Queue()
    stop_flag = threading.Event()
    output_var = tk.StringVar(value=str(DEFAULT_OUTPUT))
    quality_var = tk.StringVar(value="320")
    numbered_var = tk.BooleanVar(value=True)
    status_var = tk.StringVar(value="Paste YouTube links below, one per line.")

    frame = ttk.Frame(root, padding=12)
    frame.pack(fill="both", expand=True)

    ttk.Label(frame, text="YouTube links (one per line, downloaded top to bottom):").pack(anchor="w")
    links_box = ScrolledText(frame, height=12, wrap="none", undo=True)
    links_box.pack(fill="both", expand=True, pady=(4, 8))

    def load_file():
        path = filedialog.askopenfilename(filetypes=[("Text files", "*.txt"), ("All files", "*")])
        if path:
            links_box.delete("1.0", "end")
            links_box.insert("1.0", Path(path).read_text())

    def choose_folder():
        path = filedialog.askdirectory(initialdir=output_vartrim())
        if path:
            output_var.set(path)

    def output_vartrim():
        return output_var.get().strip()

    row = ttk.Frame(frame)
    row.pack(fill="x")
    ttk.Button(row, text="Load list from file…", command=load_file).pack(side="left")
    ttk.Button(row, text="Clear", command=lambda: links_box.delete("1.0", "end")).pack(side="left", padx=6)

    folder_row = ttk.Frame(frame)
    folder_row.pack(fill="x", pady=8)
    ttk.Label(folder_row, text="Save to:").pack(side="left")
    ttk.Entry(folder_row, textvariable=output_var).pack(side="left", fill="x", expand=True, padx=6)
    ttk.Button(folder_row, text="Choose…", command=choose_folder).pack(side="left")

    options_row = ttk.Frame(frame)
    options_row.pack(fill="x")
    ttk.Label(options_row, text="MP3 quality (kbps):").pack(side="left")
    ttk.Combobox(options_row, textvariable=quality_var, values=QUALITIES, width=5, state="readonly").pack(
        side="left", padx=6
    )
    ttk.Checkbutton(options_row, text="Number files in list order (01 - …)", variable=numbered_var).pack(
        side="left", padx=12
    )

    button_row = ttk.Frame(frame)
    button_row.pack(fill="x", pady=8)
    start_button = ttk.Button(button_row, text="Download MP3s")
    start_button.pack(side="left")
    stop_button = ttk.Button(button_row, text="Stop after current", state="disabled")
    stop_button.pack(side="left", padx=6)
    open_button = ttk.Button(
        button_row,
        text="Open folder",
        command=lambda: subprocess.run(["open", str(Path(output_vartrim()).expanduser())]),
    )
    open_button.pack(side="right")

    progress_bar = ttk.Progressbar(frame, maximum=1.0)
    progress_bar.pack(fill="x")
    ttk.Label(frame, textvariable=status_var).pack(anchor="w", pady=(4, 4))

    log_box = ScrolledText(frame, height=10, state="disabled")
    log_box.pack(fill="both", expand=True)

    def append_log(message):
        log_box.configure(state="normal")
        log_box.insert("end", message + "\n")
        log_box.see("end")
        log_box.configure(state="disabled")

    def start():
        links = parse_links(links_box.get("1.0", "end"))
        if not links:
            messagebox.showinfo("YouTube to MP3", "Paste at least one YouTube link first.")
            return
        output = output_vartrim()
        quality = quality_var.get()
        numbered = numbered_var.get()
        total = len(links)

        stop_flag.clear()
        start_button.configure(state="disabled")
        stop_button.configure(state="normal")
        log_box.configure(state="normal")
        log_box.delete("1.0", "end")
        log_box.configure(state="disabled")

        def worker():
            try:
                failed = download_all(
                    links,
                    output,
                    quality,
                    log=lambda m: events.put(("log", m)),
                    progress=lambda i, f: events.put(("progress", (i - 1 + f) / total, f"Song {i} of {total}")),
                    should_stop=stop_flag.is_set,
                    numbered=numbered,
                )
                events.put(("done", failed, total))
            except Exception as error:
                events.put(("error", str(error)))

        threading.Thread(target=worker, daemon=True).start()

    def finish():
        start_button.configure(state="normal")
        stop_button.configure(state="disabled")

    def poll():
        try:
            while True:
                event = events.get_nowait()
                kind = event[0]
                if kind == "log":
                    append_log(event[1])
                elif kind == "progress":
                    progress_bar["value"] = event[1]
                    status_var.set(event[2])
                elif kind == "done":
                    failed, total = event[1], event[2]
                    finish()
                    status_var.set(f"Finished: {total - len(failed)} of {total} saved.")
                    if failed:
                        append_log("\nFailed links:\n  " + "\n  ".join(failed))
                elif kind == "error":
                    finish()
                    status_var.set("Error.")
                    messagebox.showerror("YouTube to MP3", event[1])
        except queue.Empty:
            pass
        root.after(100, poll)

    start_button.configure(command=start)
    stop_button.configure(command=lambda: (stop_flag.set(), status_var.set("Stopping after this song…")))
    poll()
    root.mainloop()


def main():
    parser = argparse.ArgumentParser(description="Download a list of YouTube links, in order, as MP3 files.")
    parser.add_argument("--cli", metavar="FILE", help="text file with one link per line (use - for stdin); skips the window")
    parser.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT), help="output folder")
    parser.add_argument("-q", "--quality", default="320", choices=QUALITIES, help="MP3 bitrate in kbps")
    parser.add_argument("--no-numbers", action="store_true", help="don't prefix files with 01, 02, …")
    args = parser.parse_args()

    if args.cli:
        run_cli(args)
    else:
        run_gui()


if __name__ == "__main__":
    main()
