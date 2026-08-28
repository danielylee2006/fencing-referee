"""Extract exchange timestamps from FencingVision videos.

Detects touches by finding frames where:
1. The light indicator (red/green filled circle) appears in the overlay
2. The score digit changes afterward

Outputs candidate exchange timestamps as (start, end) pairs where:
- start = light_onset - 2 seconds (to capture the action)
- end = score_update + 0.5 seconds

Usage:
    uv run python scripts/extract_exchanges.py <video_path_or_url> [--output <dir>]
    uv run python scripts/extract_exchanges.py --url <youtube_url> [--duration 300]

The FencingVision overlay convention:
- Bottom bar: left fencer (red side) | clock | right fencer (green side)
- Light indicator: filled red circle at ~x=55-75 (left) or colored indicator at right side
- Score digits: white numbers in the bottom bar
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import av
import numpy as np


@dataclass
class Exchange:
    """A detected exchange with timestamps."""

    light_onset_frame: int
    score_update_frame: int
    light_onset_s: float
    score_update_s: float
    clip_start_s: float  # light_onset - 2s
    clip_end_s: float  # score_update + 0.5s
    side: str  # "left" or "right" or "both"


def detect_exchanges(video_path: str, fps: float | None = None) -> list[Exchange]:
    """Scan a video for exchange timestamps using overlay light detection.

    Detects score changes in the FencingVision overlay by monitoring the
    bottom bar for pixel changes in the score digit regions.

    Args:
        video_path: Path to the video file.
        fps: Override FPS (auto-detected if None).

    Returns:
        List of detected Exchange objects.
    """
    container = av.open(video_path)
    stream = container.streams.video[0]
    detected_fps = float(stream.average_rate or 25)
    if fps is not None:
        detected_fps = fps

    # Regions in the FencingVision overlay (720p)
    # Bottom bar is at y ~660-710
    # Left score digit: approximately x=330-365, y=670-695
    # Right score digit: approximately x=665-700, y=670-695
    # Left light indicator: x=50-80, y=670-695
    # Right light indicator: x=1200-1230, y=670-695
    # These are for 1280x720. Scale if different resolution.

    prev_left_score_region: np.ndarray | None = None
    prev_right_score_region: np.ndarray | None = None
    prev_frame_img: np.ndarray | None = None

    # State machine
    exchanges: list[Exchange] = []
    light_onset_frame: int | None = None
    light_onset_side: str = ""
    cooldown_until = 0  # ignore frames until this frame (post-score-change)

    # Baseline: sample first 50 frames to get "no light" baseline
    baseline_left_lights: list[float] = []
    baseline_right_lights: list[float] = []

    for i, frame in enumerate(container.decode(video=0)):
        img = frame.to_ndarray(format="rgb24")
        h, w = img.shape[:2]

        # Scale regions for non-720p
        sy = h / 720
        sx = w / 1280

        # Extract overlay regions
        bar_y1, bar_y2 = int(670 * sy), int(698 * sy)

        left_light = img[bar_y1:bar_y2, int(50 * sx) : int(80 * sx), :]
        right_light = img[bar_y1:bar_y2, int(1200 * sx) : int(1230 * sx), :]
        left_score = img[bar_y1:bar_y2, int(330 * sx) : int(370 * sx), :]
        right_score = img[bar_y1:bar_y2, int(660 * sx) : int(700 * sx), :]

        # Light detection: check if the red/green channel dominates
        # Left light: red filled circle → red channel >> green, blue
        left_r = float(np.mean(left_light[:, :, 0]))
        left_g = float(np.mean(left_light[:, :, 1]))
        left_b = float(np.mean(left_light[:, :, 2]))
        left_red_signal = left_r - (left_g + left_b) / 2

        right_r = float(np.mean(right_light[:, :, 0]))
        right_g = float(np.mean(right_light[:, :, 1]))
        right_b = float(np.mean(right_light[:, :, 2]))
        right_green_signal = right_g - (right_r + right_b) / 2

        # Build baseline from first 50 frames
        if i < 50:
            baseline_left_lights.append(left_red_signal)
            baseline_right_lights.append(right_green_signal)
            prev_left_score_region = left_score.copy()
            prev_right_score_region = right_score.copy()
            prev_frame_img = img.copy()
            continue

        if i == 50:
            left_threshold = float(np.mean(baseline_left_lights)) + 3 * float(
                np.std(baseline_left_lights) + 1
            )
            right_threshold = float(np.mean(baseline_right_lights)) + 3 * float(
                np.std(baseline_right_lights) + 1
            )

        if i < cooldown_until:
            prev_left_score_region = left_score.copy()
            prev_right_score_region = right_score.copy()
            prev_frame_img = img.copy()
            continue

        # Detect light onset
        left_lit = left_red_signal > left_threshold
        right_lit = right_green_signal > right_threshold

        if light_onset_frame is None and (left_lit or right_lit):
            light_onset_frame = i
            if left_lit and right_lit:
                light_onset_side = "both"
            elif left_lit:
                light_onset_side = "left"
            else:
                light_onset_side = "right"

        # After light onset, look for score change (pixel diff in score region)
        if light_onset_frame is not None and prev_left_score_region is not None:
            left_diff = float(
                np.mean(np.abs(left_score.astype(float) - prev_left_score_region.astype(float)))
            )
            right_diff = float(
                np.mean(np.abs(right_score.astype(float) - prev_right_score_region.astype(float)))
            )

            # Score change threshold — digits changing cause a big pixel diff
            frames_since_light = i - light_onset_frame
            if (left_diff > 12 or right_diff > 12) and frames_since_light > 10:
                # Score changed — this is the end of the exchange
                light_s = light_onset_frame / detected_fps
                score_s = i / detected_fps
                clip_start = max(0, light_s - 2.0)
                clip_end = score_s + 0.5

                exchanges.append(
                    Exchange(
                        light_onset_frame=light_onset_frame,
                        score_update_frame=i,
                        light_onset_s=light_s,
                        score_update_s=score_s,
                        clip_start_s=clip_start,
                        clip_end_s=clip_end,
                        side=light_onset_side,
                    )
                )

                # Reset and cooldown for 3 seconds (fencers reset)
                light_onset_frame = None
                light_onset_side = ""
                cooldown_until = i + int(3 * detected_fps)

            # Timeout: if no score change within 8 seconds, it was a false trigger
            # (equipment test, halt, etc.)
            elif frames_since_light > int(8 * detected_fps):
                light_onset_frame = None
                light_onset_side = ""

        prev_left_score_region = left_score.copy()
        prev_right_score_region = right_score.copy()
        prev_frame_img = img.copy()

    container.close()
    return exchanges


def download_video(url: str, duration: int = 300) -> str:
    """Download a video from YouTube to a temp file."""
    tmp = tempfile.mktemp(suffix=".mp4")
    print(f"Downloading {duration}s from {url}...")
    cmd = [
        "yt-dlp",
        "--download-sections",
        f"*0-{duration}",
        "--force-keyframes-at-cuts",
        "-f",
        "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "--merge-output-format",
        "mp4",
        "-o",
        tmp,
        "--no-playlist",
        "--quiet",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    return tmp


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract exchange timestamps from fencing video")
    parser.add_argument("video", help="Local video path or YouTube URL")
    parser.add_argument("--duration", type=int, default=300, help="Seconds to download (default 300)")
    parser.add_argument("--output", type=Path, default=None, help="Output directory for trimmed clips")
    args = parser.parse_args()

    video_path = args.video
    is_url = video_path.startswith("http")

    if is_url:
        video_path = download_video(video_path, args.duration)

    print(f"Scanning {video_path} for exchanges...")
    exchanges = detect_exchanges(video_path)

    if not exchanges:
        print("No exchanges detected.")
        return

    print(f"\nFound {len(exchanges)} exchange(s):\n")
    print(f"{'#':>3}  {'Light (s)':>10}  {'Score (s)':>10}  {'Clip start':>10}  {'Clip end':>10}  Side")
    print("-" * 65)
    for j, ex in enumerate(exchanges):
        print(
            f"{j + 1:3d}  {ex.light_onset_s:10.2f}  {ex.score_update_s:10.2f}  "
            f"{ex.clip_start_s:10.2f}  {ex.clip_end_s:10.2f}  {ex.side}"
        )

    # If output dir specified, trim clips
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        for j, ex in enumerate(exchanges):
            out_path = args.output / f"exchange_{j + 1:03d}.mp4"
            print(f"\nTrimming exchange {j + 1} to {out_path}...")
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-ss",
                str(ex.clip_start_s),
                "-to",
                str(ex.clip_end_s),
                "-c",
                "copy",
                str(out_path),
            ]
            subprocess.run(cmd, capture_output=True, check=True)

    # Clean up temp file
    if is_url:
        Path(video_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
