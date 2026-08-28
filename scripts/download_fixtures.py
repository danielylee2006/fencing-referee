"""Download and trim fixture clips from the manifest.

Usage: uv run python scripts/download_fixtures.py

Two-step process per clip:
1. Download the FULL video via yt-dlp (no --download-sections, which causes
   keyframe-snapping timestamp errors).
2. Trim to exact timestamps using ffmpeg -ss (input) + -t for frame accuracy.

Videos are cached in tests/fixtures/clips/.cache/ so multiple clips from the
same source video don't require re-downloading.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


MANIFEST = Path("tests/fixtures/manifest.yaml")
OUTPUT_DIR = Path("tests/fixtures/clips")
CACHE_DIR = OUTPUT_DIR / ".cache"


def get_cached_video(url: str) -> Path:
    """Download a full video to the cache, or return the cached path."""
    # Use the video ID as the cache key
    video_id = url.split("v=")[-1].split("&")[0]
    cached = CACHE_DIR / f"{video_id}.mp4"

    if cached.exists():
        return cached

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"    Downloading full video {video_id}...")

    cmd = [
        "yt-dlp",
        "-f",
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "--merge-output-format",
        "mp4",
        "-o",
        str(cached),
        "--no-playlist",
        "--quiet",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ERROR downloading {video_id}: {result.stderr}", file=sys.stderr)
        cached.unlink(missing_ok=True)
        return cached  # will not exist, caller checks

    size_mb = cached.stat().st_size / (1024 * 1024)
    print(f"    Cached {video_id} ({size_mb:.0f} MB)")
    return cached


def trim_clip(source: Path, start_s: float, duration_s: float, out_path: Path) -> bool:
    """Frame-accurate trim using ffmpeg with re-encoding."""
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        str(start_s),
        "-i",
        str(source),
        "-t",
        str(duration_s),
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        "23",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"    ERROR trimming: {result.stderr[:200]}", file=sys.stderr)
        out_path.unlink(missing_ok=True)
        return False
    return True


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
    print(f"  {clip_id}: {duration:.1f}s from {url} [{start:.1f}s - {end:.1f}s]")

    # Step 1: Get the full video (cached)
    cached = get_cached_video(url)
    if not cached.exists():
        print(f"  {clip_id}: FAILED (could not download source)")
        return

    # Step 2: Frame-accurate trim
    if not trim_clip(cached, start, duration, out_path):
        print(f"  {clip_id}: FAILED (trim error)")
        return

    size_mb = out_path.stat().st_size / (1024 * 1024)
    print(f"  {clip_id}: OK ({size_mb:.1f} MB)")
    if size_mb > 2.0:
        print(f"    WARNING: {size_mb:.1f} MB (target <2 MB per clip)")


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

    # Offer to clean the cache
    if CACHE_DIR.exists():
        cache_size = sum(f.stat().st_size for f in CACHE_DIR.glob("*.mp4")) / (1024 * 1024)
        print(f"\nCache: {cache_size:.0f} MB in {CACHE_DIR}")
        print("Run: rm -rf tests/fixtures/clips/.cache to free space")

    print("Done.")


if __name__ == "__main__":
    main()
