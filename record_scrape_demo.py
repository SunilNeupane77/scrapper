"""
Records the same navigation flow as scraper.py and writes recording.mp4 at the
project root (Playwright captures WebM first; transcode via imageio-ffmpeg).
"""
from __future__ import annotations

import glob
import os
import subprocess
import tempfile

import imageio_ffmpeg
from playwright.sync_api import sync_playwright


def _webm_to_mp4(webm_path: str, mp4_path: str) -> None:
    ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        webm_path,
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-pix_fmt",
        "yuv420p",
        "-an",
        "-movflags",
        "+faststart",
        mp4_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True)


def main() -> None:
    root = os.path.dirname(os.path.abspath(__file__))
    mp4_out = os.path.join(root, "recording.mp4")

    with tempfile.TemporaryDirectory() as tmp:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(
                record_video_dir=tmp,
                record_video_size={"width": 1280, "height": 720},
                viewport={"width": 1280, "height": 720},
            )
            page = context.new_page()

            page.goto("https://ekantipur.com/entertainment")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(2000)
            page.wait_for_selector("a[href*='/entertainment/']")

            page.goto("https://ekantipur.com")
            page.wait_for_load_state("networkidle")
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)

            context.close()
            browser.close()

        generated = sorted(glob.glob(os.path.join(tmp, "*.webm")))
        if not generated:
            print("No WebM produced; MP4 not written.")
            return
        webm_path = generated[-1]
        _webm_to_mp4(webm_path, mp4_out)

    print(f"Saved: {mp4_out}")


if __name__ == "__main__":
    main()
