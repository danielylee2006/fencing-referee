"""S0 corpus acquisition — download, detect, assess, trim, label.

Two-phase pipeline to avoid YouTube rate limits:

  Phase 1 — Enumerate (fast, one-time):
    uv run python scripts/acquire_corpus.py --enumerate
    Hits YouTube to list all videos in all playlists, saves to
    data/manifests/video_queue.yaml. Run once, retry if rate-limited.

  Phase 2 — Process (slow, resumable, days-long):
    uv run python scripts/acquire_corpus.py
    Reads from the queue, downloads/processes one video at a time.
    No playlist enumeration — only individual video downloads.
    Retries with exponential backoff on rate limits.

Pipeline per video:
1. Download full bout video (temporary)
2. Run exchange detection (touch lights in FencingVision overlay)
3. Assess quality: score change detection, clock check, label assignment
4. Trim each exchange to a clip
5. Reject blade tests, flag quality issues, keep good exchanges
6. Delete the full video

Exchange clips are saved to data/corpus/clips/<video_id>_<exchange_num>.mp4.
A manifest tracks all processed videos and their exchanges with labels.

Resumable: skips videos already processed. Safe to interrupt and restart.

Usage:
    uv run python scripts/acquire_corpus.py --enumerate          # phase 1: build queue
    uv run python scripts/acquire_corpus.py                      # phase 2: process queue
    uv run python scripts/acquire_corpus.py --dry-run            # list pending videos
    uv run python scripts/acquire_corpus.py --playlist 0         # enumerate only first playlist
    uv run python scripts/acquire_corpus.py --cookies chrome     # use browser cookies
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import av
import numpy as np
import yaml

# Import the exchange detector
sys.path.insert(0, str(Path(__file__).parent))
from extract_exchanges import Exchange, detect_exchanges

# Import the quality assessment pipeline
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from a1.apparatus.exchange_filter import assess_exchange

MANIFEST_PATH = Path("data/manifests/source_channels.yaml")
VIDEO_QUEUE_PATH = Path("data/manifests/video_queue.yaml")
CLIPS_DIR = Path("data/corpus/clips")
TEMP_DIR = Path("data/corpus/.tmp")
CORPUS_MANIFEST = Path("data/manifests/corpus_manifest.yaml")

# Retry configuration
MAX_RETRIES = 5
INITIAL_BACKOFF_S = 30  # first retry after 30s
MAX_BACKOFF_S = 600  # cap at 10 minutes

# Videos with these patterns in the title are excluded (case-insensitive)
EXCLUDE_PATTERNS = [
    r"\bpodium\b",
    r"\bfinal\b",
    r"\bsemi.?final\b",
    r"\bteam\b",
]

EXCLUDE_RE = re.compile("|".join(EXCLUDE_PATTERNS), re.IGNORECASE)

# Parse FencingVision title format
TITLE_RE = re.compile(
    r"^(\d{4})\s+"  # year
    r"(\d+)\s+"  # event number
    r"(T\d+|Pool)\s+"  # round
    r"(\d+)\s+"  # match number
    r"([MF])\s+"  # gender
    r"([FSE])\s+"  # weapon (F=foil, S=sabre, E=epee)
    r"Individual\s+"  # format
    r"(.+?)\s+"  # city
    r"([A-Z]{3})\s+"  # country code
    r"GP\s+"  # grand prix
    r"(?:RED|GREEN|BLUE|YELLOW|\d+)\s+"  # piste color/number
    r"(.+?)\s+([A-Z]{3})\s+"  # athlete 1 + country
    r"vs\s+"
    r"(.+?)\s+([A-Z]{3})\s*$",  # athlete 2 + country
    re.IGNORECASE,
)

# Cookie browser name (set via --cookies flag)
_cookie_browser: str | None = None


def parse_title(title: str) -> dict[str, str] | None:
    """Extract metadata from a FencingVision video title."""
    m = TITLE_RE.match(title)
    if not m:
        return None
    weapon_map = {"F": "foil", "S": "sabre", "E": "epee"}
    gender_map = {"M": "men", "F": "women"}
    return {
        "year": m.group(1),
        "event_num": m.group(2),
        "round": m.group(3),
        "match_num": m.group(4),
        "gender": gender_map.get(m.group(5).upper(), m.group(5)),
        "weapon": weapon_map.get(m.group(6).upper(), m.group(6)),
        "city": m.group(7).strip(),
        "country": m.group(8),
        "athlete_1": m.group(9).strip(),
        "athlete_1_country": m.group(10),
        "athlete_2": m.group(11).strip(),
        "athlete_2_country": m.group(12),
    }


def _yt_dlp_base_cmd() -> list[str]:
    """Base yt-dlp command with cookie support if configured."""
    cmd = ["yt-dlp"]
    if _cookie_browser:
        cmd.extend(["--cookies-from-browser", _cookie_browser])
    return cmd


def enumerate_playlist(url: str) -> list[dict[str, str]]:
    """List all videos in a YouTube playlist via yt-dlp."""
    cmd = _yt_dlp_base_cmd() + [
        "--flat-playlist",
        "--print",
        '{"id": "%(id)s", "title": "%(title)s", "url": "%(url)s", "duration": "%(duration)s"}',
        "--no-warnings",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        print(f"  ERROR enumerating playlist: {result.stderr[:200]}", file=sys.stderr)
        return []

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            videos.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return videos


def download_video(video_id: str, url: str) -> Path | None:
    """Download a video with retry and exponential backoff.

    Returns the path or None after all retries exhausted.
    """
    out_path = TEMP_DIR / f"{video_id}.mp4"
    if out_path.exists():
        return out_path

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    cmd = _yt_dlp_base_cmd() + [
        "-f",
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "--merge-output-format",
        "mp4",
        "-o",
        str(out_path),
        "--no-playlist",
        "--quiet",
        "--progress",
        "--sleep-interval", "5",
        "--max-sleep-interval", "15",
        url,
    ]

    backoff = INITIAL_BACKOFF_S
    for attempt in range(1, MAX_RETRIES + 1):
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0 and out_path.exists():
            return out_path

        stderr = result.stderr or ""
        is_rate_limit = "429" in stderr or "Too Many Requests" in stderr

        if not is_rate_limit or attempt == MAX_RETRIES:
            print(f"    download FAILED (attempt {attempt}/{MAX_RETRIES}): "
                  f"{stderr[:200]}", file=sys.stderr)
            out_path.unlink(missing_ok=True)
            return None

        print(f"    rate limited, retrying in {backoff}s "
              f"(attempt {attempt}/{MAX_RETRIES})...")
        time.sleep(backoff)
        backoff = min(backoff * 2, MAX_BACKOFF_S)

    return None


def trim_clip(source: Path, start_s: float, duration_s: float, out_path: Path) -> bool:
    """Frame-accurate trim using ffmpeg with re-encoding."""
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-ss",
        str(start_s),
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
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        out_path.unlink(missing_ok=True)
        return False
    return True



def process_video(
    video_id: str, url: str, meta: dict[str, str] | None, playlist_weapon: str
) -> list[dict]:
    """Download video, detect exchanges, assess on full video, trim clips.

    The key insight: score changes can take 5-10 seconds after the touch
    (referee deliberation). We assess quality on the FULL video first to
    find the exact score change time, then trim clips to include it.

    Returns a list of exchange entries for the manifest.
    """
    weapon = meta["weapon"] if meta else playlist_weapon

    # Download
    video_path = download_video(video_id, url)
    if not video_path:
        return []

    size_mb = video_path.stat().st_size / (1024 * 1024)
    print(f"    downloaded ({size_mb:.0f} MB), detecting touches...")

    # Detect exchanges via touch light detection
    exchanges = detect_exchanges(str(video_path), weapon=weapon)
    if not exchanges:
        print(f"    no exchanges detected, deleting")
        video_path.unlink(missing_ok=True)
        return []

    # Get video fps
    container = av.open(str(video_path))
    fps = float(container.streams.video[0].average_rate or 25)
    container.close()

    print(f"    {len(exchanges)} touches found, assessing quality...")

    # For each exchange: load ~10 seconds of frames around the touch,
    # assess quality, then trim the final clip.
    CLIPS_DIR.mkdir(parents=True, exist_ok=True)
    exchange_entries = []
    rejected = 0

    for j, ex in enumerate(exchanges):
        # Load frames from 3s before touch up to the next exchange's onset.
        # The next exchange's light is the hard boundary — any score change
        # after that belongs to a different exchange.
        assess_start_s = max(0, ex.light_onset_s - 3.0)
        if j + 1 < len(exchanges):
            # Boundary: next exchange's light onset (don't bleed into it)
            assess_end_s = exchanges[j + 1].light_onset_s
        else:
            # Last exchange: use 60s upper bound
            assess_end_s = ex.light_onset_s + 60.0
        assess_frames = _load_frame_range(str(video_path), assess_start_s, assess_end_s)

        if not assess_frames:
            continue

        # Touch is at 3 seconds into the loaded segment
        touch_frame_local = int(3.0 * fps)
        # Lookahead bounded by next exchange
        lookahead = len(assess_frames) - touch_frame_local
        quality = assess_exchange(assess_frames, touch_frame_local, fps, weapon,
                                  lookahead_frames=lookahead)

        if quality.reject:
            rejected += 1
            del assess_frames
            continue

        # Determine clip boundaries
        clip_start_s = assess_start_s
        if quality.score_change and quality.score_change.change_frame >= 0:
            # Score change frame is relative to assess_frames
            score_change_s = assess_start_s + quality.score_change.change_frame / fps
            clip_end_s = score_change_s + 2.0
        else:
            clip_end_s = ex.light_onset_s + 5.0

        # Cap clip length at 15 seconds
        if clip_end_s - clip_start_s > 15.0:
            clip_end_s = clip_start_s + 15.0

        duration = clip_end_s - clip_start_s
        del assess_frames

        # Trim the clip
        clip_name = f"{video_id}_{j + 1:03d}.mp4"
        clip_path = CLIPS_DIR / clip_name

        if not clip_path.exists():
            if not trim_clip(video_path, clip_start_s, duration, clip_path):
                continue

        clip_size = clip_path.stat().st_size / (1024 * 1024)

        exchange_entries.append(
            {
                "clip_file": clip_name,
                "video_id": video_id,
                "exchange_num": j + 1,
                "light_onset_s": round(ex.light_onset_s, 2),
                "clip_start_s": round(clip_start_s, 2),
                "clip_end_s": round(clip_end_s, 2),
                "light_side": ex.side,
                "light_detail": ex.light_detail,
                "label": quality.label,
                "weapon": weapon,
                "size_mb": round(clip_size, 1),
                "flags": quality.flags if quality.flags else [],
                "score_change_s": round(quality.score_change.change_time_s, 2)
                if quality.score_change and quality.score_change.change_frame >= 0
                else None,
            }
        )

    # Delete the full video
    video_path.unlink(missing_ok=True)
    print(
        f"    {len(exchange_entries)} clips saved, {rejected} rejected, full video deleted"
    )

    return exchange_entries


def _load_frame_range(video_path: str, start_s: float, end_s: float) -> list[np.ndarray]:
    """Load frames from a time range of a video without loading the whole thing."""
    container = av.open(video_path)
    stream = container.streams.video[0]
    fps = float(stream.average_rate or 25)

    # Seek to start
    start_pts = int(start_s / stream.time_base)
    container.seek(start_pts, stream=stream)

    frames: list[np.ndarray] = []
    for frame in container.decode(video=0):
        t = float(frame.pts * stream.time_base) if frame.pts is not None else 0
        if t > end_s:
            break
        if t >= start_s - 0.5:  # small buffer before start
            frames.append(frame.to_ndarray(format="rgb24"))

    container.close()
    return frames


def load_existing_manifest() -> dict:
    """Load existing corpus manifest if it exists."""
    if not CORPUS_MANIFEST.exists():
        return {"videos": {}, "exchanges": []}
    with open(CORPUS_MANIFEST) as f:
        data = yaml.safe_load(f) or {}
    videos = {v["video_id"]: v for v in data.get("videos", [])}
    exchanges = data.get("exchanges", [])
    return {"videos": videos, "exchanges": exchanges}


def save_manifest(data: dict) -> None:
    """Save the corpus manifest."""
    CORPUS_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    out = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "video_count": len(data["videos"]),
        "exchange_count": len(data["exchanges"]),
        "videos": list(data["videos"].values()),
        "exchanges": data["exchanges"],
    }
    with open(CORPUS_MANIFEST, "w") as f:
        yaml.dump(out, f, default_flow_style=False, sort_keys=False, width=120)


# --- Phase 1: Enumerate ---

def enumerate_all(playlists: list[dict]) -> None:
    """Enumerate all playlists and save to video_queue.yaml."""
    queue: list[dict] = []
    existing_ids: set[str] = set()

    # Load existing queue if present (for incremental enumeration)
    if VIDEO_QUEUE_PATH.exists():
        with open(VIDEO_QUEUE_PATH) as f:
            existing = yaml.safe_load(f) or {}
        for v in existing.get("videos", []):
            existing_ids.add(v["video_id"])

    for i, pl in enumerate(playlists):
        pl_name = pl["name"]
        pl_weapon = pl["weapon"]
        print(f"\n[{i + 1}/{len(playlists)}] {pl_name} ({pl_weapon})")

        videos = enumerate_playlist(pl["url"])
        if not videos:
            print(f"  FAILED — rate limited or empty. Re-run --enumerate to retry.")
            continue

        print(f"  {len(videos)} videos found")
        added = 0
        excluded = 0

        for v in videos:
            vid_id = v["id"]
            title = v["title"]

            if EXCLUDE_RE.search(title):
                excluded += 1
                continue

            if vid_id in existing_ids:
                continue

            meta = parse_title(title)
            queue.append({
                "video_id": vid_id,
                "title": title,
                "url": f"https://www.youtube.com/watch?v={vid_id}",
                "playlist": pl_name,
                "weapon": meta["weapon"] if meta else pl_weapon,
                "round": meta["round"] if meta else "",
                "gender": meta["gender"] if meta else "",
                "athlete_1": meta["athlete_1"] if meta else "",
                "athlete_1_country": meta["athlete_1_country"] if meta else "",
                "athlete_2": meta["athlete_2"] if meta else "",
                "athlete_2_country": meta["athlete_2_country"] if meta else "",
                "year": meta["year"] if meta else "",
                "city": meta["city"] if meta else "",
                "parsed": meta is not None,
            })
            existing_ids.add(vid_id)
            added += 1

        print(f"  {added} added, {excluded} excluded (podium/final/semi/team)")

    # Merge with existing queue
    all_videos = []
    if VIDEO_QUEUE_PATH.exists():
        with open(VIDEO_QUEUE_PATH) as f:
            existing = yaml.safe_load(f) or {}
        all_videos = existing.get("videos", [])
    all_videos.extend(queue)

    out = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "total": len(all_videos),
        "videos": all_videos,
    }
    VIDEO_QUEUE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(VIDEO_QUEUE_PATH, "w") as f:
        yaml.dump(out, f, default_flow_style=False, sort_keys=False, width=120)

    print(f"\n{'=' * 60}")
    print(f"Queue saved: {len(all_videos)} videos in {VIDEO_QUEUE_PATH}")
    print(f"New this run: {len(queue)}")
    print(f"\nNext: run without --enumerate to start processing.")


# --- Phase 2: Process from queue ---

def process_from_queue(dry_run: bool = False) -> None:
    """Process videos from the queue file. No playlist enumeration needed."""
    if not VIDEO_QUEUE_PATH.exists():
        print(f"No video queue found at {VIDEO_QUEUE_PATH}", file=sys.stderr)
        print(f"Run with --enumerate first to build the queue.", file=sys.stderr)
        sys.exit(1)

    with open(VIDEO_QUEUE_PATH) as f:
        queue_data = yaml.safe_load(f) or {}
    queue = queue_data.get("videos", [])

    if not queue:
        print("Queue is empty.")
        return

    # Load existing manifest for resumability
    manifest = load_existing_manifest()

    total = len(queue)
    pending = 0
    cached = 0
    processed = 0
    failed = 0
    total_exchanges = 0

    for i, v in enumerate(queue):
        vid_id = v["video_id"]
        title = v["title"]
        weapon = v["weapon"]

        # Skip already-processed videos
        if vid_id in manifest["videos"] and manifest["videos"][vid_id].get("processed", False):
            cached += 1
            continue

        pending += 1

        if dry_run:
            parsed = "OK" if v.get("parsed", False) else "NO_PARSE"
            print(f"  [PENDING] [{parsed}] {title}")
            continue

        print(f"\n  [{cached + processed + failed + 1}/{total}] {title[:70]}")

        meta = {
            "weapon": v["weapon"],
            "round": v.get("round", ""),
            "gender": v.get("gender", ""),
            "athlete_1": v.get("athlete_1", ""),
            "athlete_1_country": v.get("athlete_1_country", ""),
            "athlete_2": v.get("athlete_2", ""),
            "athlete_2_country": v.get("athlete_2_country", ""),
            "year": v.get("year", ""),
            "city": v.get("city", ""),
        }

        exchange_entries = process_video(vid_id, v["url"], meta, weapon)

        # Update manifest
        video_entry = {
            "video_id": vid_id,
            "title": title,
            "url": v["url"],
            "playlist": v.get("playlist", ""),
            **meta,
            "processed": True,
            "exchange_count": len(exchange_entries),
        }

        manifest["videos"][vid_id] = video_entry
        manifest["exchanges"].extend(exchange_entries)

        if exchange_entries:
            processed += 1
            total_exchanges += len(exchange_entries)
        else:
            failed += 1

        # Save after each video for resumability
        save_manifest(manifest)

    if dry_run:
        print(f"\n{'=' * 60}")
        print(f"Total in queue: {total}")
        print(f"Already processed: {cached}")
        print(f"Pending: {pending}")
        return

    # Final save
    save_manifest(manifest)

    print(f"\n{'=' * 60}")
    print(f"Queue:       {total} videos")
    print(f"Cached:      {cached} (already processed)")
    print(f"Processed:   {processed}")
    print(f"Failed:      {failed}")
    print(f"Exchanges:   {total_exchanges} new clips")
    print(f"Manifest:    {len(manifest['videos'])} videos, "
          f"{len(manifest['exchanges'])} exchanges in {CORPUS_MANIFEST}")

    if CLIPS_DIR.exists():
        corpus_size = sum(f.stat().st_size for f in CLIPS_DIR.glob("*.mp4")) / (1024 * 1024 * 1024)
        print(f"Disk usage:  {corpus_size:.1f} GB in {CLIPS_DIR}")


def main() -> None:
    parser = argparse.ArgumentParser(description="S0 corpus acquisition")
    parser.add_argument("--enumerate", action="store_true",
                        help="Phase 1: enumerate playlists and build video queue")
    parser.add_argument("--dry-run", action="store_true",
                        help="List pending videos without downloading")
    parser.add_argument("--playlist", type=int, default=None,
                        help="Only process this playlist index (for --enumerate)")
    parser.add_argument("--cookies", type=str, default=None,
                        help="Browser to read cookies from (e.g. chrome, firefox)")
    args = parser.parse_args()

    global _cookie_browser
    _cookie_browser = args.cookies

    if not MANIFEST_PATH.exists():
        print(f"Source manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        config = yaml.safe_load(f)

    channel = config["channels"][0]  # FencingVision
    playlists = channel["playlists"]

    if args.playlist is not None:
        playlists = [playlists[args.playlist]]

    if args.enumerate:
        enumerate_all(playlists)
    else:
        process_from_queue(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
