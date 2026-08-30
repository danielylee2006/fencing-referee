"""S0 corpus acquisition — download, detect, assess, trim, label.

Pipeline per video:
1. Download full bout video (temporary)
2. Run exchange detection (touch lights in FencingVision overlay)
3. Trim each exchange to a clip
4. Assess quality: score change detection, clock check, label assignment
5. Reject blade tests, flag quality issues, keep good exchanges
6. Delete the full video

Exchange clips are saved to data/corpus/clips/<video_id>_<exchange_num>.mp4.
A manifest tracks all processed videos and their exchanges with labels.

Resumable: skips videos already processed. Safe to interrupt and restart.

Usage:
    uv run python scripts/acquire_corpus.py
    uv run python scripts/acquire_corpus.py --dry-run     # list videos without downloading
    uv run python scripts/acquire_corpus.py --playlist 0   # process only the first playlist
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
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
from a1.apparatus.score_tracker import detect_overlay_era

MANIFEST_PATH = Path("data/manifests/source_channels.yaml")
CLIPS_DIR = Path("data/corpus/clips")
TEMP_DIR = Path("data/corpus/.tmp")
CORPUS_MANIFEST = Path("data/manifests/corpus_manifest.yaml")

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


def enumerate_playlist(url: str) -> list[dict[str, str]]:
    """List all videos in a YouTube playlist via yt-dlp."""
    cmd = [
        "yt-dlp",
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
    """Download a video to a temp directory. Returns the path or None on failure."""
    out_path = TEMP_DIR / f"{video_id}.mp4"
    if out_path.exists():
        return out_path

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [
        "yt-dlp",
        "-f",
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "--merge-output-format",
        "mp4",
        "-o",
        str(out_path),
        "--no-playlist",
        "--quiet",
        "--progress",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if result.returncode != 0:
        print(f"    download FAILED: {result.stderr[:200]}", file=sys.stderr)
        out_path.unlink(missing_ok=True)
        return None

    return out_path


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
    exchanges = detect_exchanges(str(video_path))
    if not exchanges:
        print(f"    no exchanges detected, deleting")
        video_path.unlink(missing_ok=True)
        return []

    # Get video fps and detect overlay era
    container = av.open(str(video_path))
    fps = float(container.streams.video[0].average_rate or 25)
    # Detect overlay era from frame ~2 seconds in
    era = "2025"
    for fi, fr in enumerate(container.decode(video=0)):
        if fi == int(2 * fps):
            era = detect_overlay_era(fr.to_ndarray(format="rgb24"))
            break
    container.close()

    print(f"    {len(exchanges)} touches found ({era} overlay), assessing quality...")

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
                                  lookahead_frames=lookahead, era=era)

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


def main() -> None:
    parser = argparse.ArgumentParser(description="S0 corpus acquisition")
    parser.add_argument("--dry-run", action="store_true", help="List videos without downloading")
    parser.add_argument("--playlist", type=int, default=None, help="Only process this playlist index")
    args = parser.parse_args()

    if not MANIFEST_PATH.exists():
        print(f"Source manifest not found: {MANIFEST_PATH}", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST_PATH) as f:
        config = yaml.safe_load(f)

    channel = config["channels"][0]  # FencingVision
    playlists = channel["playlists"]

    if args.playlist is not None:
        playlists = [playlists[args.playlist]]

    # Load existing manifest for resumability
    manifest = load_existing_manifest()

    total_enumerated = 0
    total_excluded = 0
    total_processed = 0
    total_cached = 0
    total_failed = 0
    total_exchanges = 0

    for i, pl in enumerate(playlists):
        pl_name = pl["name"]
        pl_weapon = pl["weapon"]
        print(f"\n[{i + 1}/{len(playlists)}] {pl_name} ({pl_weapon})")

        videos = enumerate_playlist(pl["url"])
        print(f"  {len(videos)} videos found")

        for v in videos:
            vid_id = v["id"]
            title = v["title"]
            total_enumerated += 1

            # Filter excluded titles
            if EXCLUDE_RE.search(title):
                total_excluded += 1
                continue

            # Skip already-processed videos
            if vid_id in manifest["videos"] and manifest["videos"][vid_id].get("processed", False):
                total_cached += 1
                continue

            # Parse metadata from title
            meta = parse_title(title)

            if args.dry_run:
                parsed = "OK" if meta else "NO_PARSE"
                print(f"  [PENDING] [{parsed}] {title}")
                continue

            print(f"  [{total_processed + total_cached + 1}] {title[:70]}")

            # Process: download → detect → trim → delete
            exchange_entries = process_video(vid_id, v.get("url", f"https://www.youtube.com/watch?v={vid_id}"), meta, pl_weapon)

            # Update manifest
            video_entry = {
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
                "processed": True,
                "exchange_count": len(exchange_entries),
            }

            manifest["videos"][vid_id] = video_entry
            manifest["exchanges"].extend(exchange_entries)

            if exchange_entries:
                total_processed += 1
                total_exchanges += len(exchange_entries)
            else:
                total_failed += 1

            # Save after each video for resumability
            save_manifest(manifest)

    # Final save
    if not args.dry_run:
        save_manifest(manifest)

    print(f"\n{'=' * 60}")
    print(f"Enumerated:  {total_enumerated}")
    print(f"Excluded:    {total_excluded} (podium/final/semi/team)")
    print(f"Cached:      {total_cached} (already processed)")
    print(f"Processed:   {total_processed}")
    print(f"Failed:      {total_failed}")
    print(f"Exchanges:   {total_exchanges} new clips")
    print(f"Manifest:    {len(manifest['videos'])} videos, {len(manifest['exchanges'])} exchanges in {CORPUS_MANIFEST}")

    if not args.dry_run and CLIPS_DIR.exists():
        corpus_size = sum(f.stat().st_size for f in CLIPS_DIR.glob("*.mp4")) / (1024 * 1024 * 1024)
        print(f"Disk usage:  {corpus_size:.1f} GB in {CLIPS_DIR}")


if __name__ == "__main__":
    main()
