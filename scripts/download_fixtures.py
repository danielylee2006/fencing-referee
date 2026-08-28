"""Download and trim fixture clips from the manifest.

Usage: uv run python scripts/download_fixtures.py

Each clip is trimmed to the [start_s, end_s] window specified in
tests/fixtures/manifest.yaml using yt-dlp's built-in section support.

NOTE: URLs and timestamps in the manifest must be manually verified before
running this script. See the `notes` field in each manifest entry.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


MANIFEST = Path("tests/fixtures/manifest.yaml")
OUTPUT_DIR = Path("tests/fixtures/clips")


def download_and_trim(clip: dict[str, object]) -> None:
    clip_id = clip["id"]
    url = str(clip["url"])
    start = float(str(clip["start_s"]))
    end = float(str(clip["end_s"]))
    out_path = OUTPUT_DIR / f"{clip_id}.mp4"

    if out_path.exists():
        print(f"  {clip_id}: already exists, skipping")
        return

    duration = end - start
    print(f"  {clip_id}: downloading {duration:.1f}s from {url}")

    # Download and trim in one pass with yt-dlp's built-in section support.
    # --force-keyframes-at-cuts ensures clean boundaries without re-encoding
    # the full video.
    cmd = [
        "yt-dlp",
        "--download-sections",
        f"*{start}-{end}",
        "--force-keyframes-at-cuts",
        "-f",
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "--merge-output-format",
        "mp4",
        "-o",
        str(out_path),
        "--no-playlist",
        "--quiet",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR downloading {clip_id}: {result.stderr}", file=sys.stderr)
        return

    # Warn if the clip is unexpectedly large (target is <2 MB for a 720p 8-s clip).
    size_mb = out_path.stat().st_size / (1024 * 1024)
    if size_mb > 2.0:
        print(f"  WARNING: {clip_id} is {size_mb:.1f} MB (target <2 MB per clip)")


def main() -> None:
    if not MANIFEST.exists():
        print(f"Manifest not found: {MANIFEST}", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST) as f:
        manifest = yaml.safe_load(f)

    clips: list[dict[str, object]] = manifest["clips"]
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(clips)} fixture clips...")
    for clip in clips:
        download_and_trim(clip)

    print("Done.")


if __name__ == "__main__":
    main()
