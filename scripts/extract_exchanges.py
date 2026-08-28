"""Extract exchange timestamps from FencingVision videos.

Detects touches by finding frames where:
1. A colored line (red/green/white) appears ABOVE the FencingVision overlay bar.
   This line spans the fencer's side and indicates a touch was registered.
2. The score digit in the overlay bar changes afterward.

Outputs candidate exchange timestamps as (start, end) pairs where:
- start = light_onset - 3 seconds (to capture the action leading to the touch)
- end = score_update + 1 second (to show the result)

Usage:
    uv run python scripts/extract_exchanges.py <video_path_or_url>
    uv run python scripts/extract_exchanges.py --output <dir> <video_path_or_url>

The FencingVision overlay:
- Bottom bar (~y=665-710 in 720p): fencer names, scores, clock
- Touch indicator: colored line appears ABOVE the bar (~y=650-665)
  - Red line = left fencer's touch (valid, on-target)
  - Green line = right fencer's touch (valid, on-target)
  - White line = off-target touch
  - Both red+green = double touch
- Score digits change after the referee awards the point
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
    clip_start_s: float
    clip_end_s: float
    side: str  # "left", "right", "both", or "off_target"


def detect_exchanges(video_path: str) -> list[Exchange]:
    """Scan a video for exchanges using the FencingVision overlay.

    Detects the colored touch-indicator line above the overlay bar,
    then waits for a score change in the overlay bar itself.
    """
    container = av.open(video_path)
    stream = container.streams.video[0]
    fps = float(stream.average_rate or 25)

    exchanges: list[Exchange] = []
    light_onset_frame: int | None = None
    light_onset_side: str = ""
    cooldown_until: int = 0

    # We need a baseline of what the overlay bar looks like (for score-change diffing)
    prev_bar: np.ndarray | None = None

    # Previous frame's strip signals (for transition detection)
    prev_left_red: float | None = None
    prev_left_green: float = 0.0
    prev_right_red: float = 0.0
    prev_right_green: float | None = None

    # Baseline: collect the touch-indicator strip colors from first 50 frames
    baseline_left_strips: list[np.ndarray] = []
    baseline_right_strips: list[np.ndarray] = []

    for i, frame in enumerate(container.decode(video=0)):
        img = frame.to_ndarray(format="rgb24")
        h, w = img.shape[:2]
        sy = h / 720
        sx = w / 1280

        # --- Regions ---
        # Touch indicator strip: horizontal band just ABOVE the overlay bar
        strip_y1, strip_y2 = int(648 * sy), int(663 * sy)
        # Left half and right half of the strip
        mid_x = w // 2
        left_strip = img[strip_y1:strip_y2, int(40 * sx) : mid_x, :]
        right_strip = img[strip_y1:strip_y2, mid_x : int(1240 * sx), :]

        # Overlay bar (for score-change detection via whole-bar diff)
        bar_y1, bar_y2 = int(665 * sy), int(708 * sy)
        bar = img[bar_y1:bar_y2, int(40 * sx) : int(1240 * sx), :]

        # --- Build baseline from first 50 frames ---
        if i < 50:
            baseline_left_strips.append(left_strip.astype(np.float32))
            baseline_right_strips.append(right_strip.astype(np.float32))
            prev_bar = bar.copy()
            continue

        if i == 50:
            # Compute separate baselines for left and right strips
            left_mean = np.mean(baseline_left_strips, axis=0)
            right_mean = np.mean(baseline_right_strips, axis=0)
            baseline_left_r = float(np.mean(left_mean[:, :, 0]))
            baseline_left_g = float(np.mean(left_mean[:, :, 1]))
            baseline_right_r = float(np.mean(right_mean[:, :, 0]))
            baseline_right_g = float(np.mean(right_mean[:, :, 1]))

        if i < cooldown_until:
            prev_bar = bar.copy()
            continue

        # --- Detect touch indicator line ---
        # Check for strong color signal in the strip that differs from baseline
        # Red line: R channel much higher than baseline
        # Green line: G channel much higher than baseline
        # White line: all channels much higher than baseline

        def strip_signal(strip: np.ndarray) -> tuple[float, float]:
            """Compute red and green signal strength in a strip.

            Returns (red_pct, green_pct) — fraction of pixels where that
            color channel dominates.
            """
            r = strip[:, :, 0].astype(np.float32)
            g = strip[:, :, 1].astype(np.float32)
            total = strip.shape[0] * strip.shape[1]
            red_pct = float(np.sum((r - g) > 50)) / total
            green_pct = float(np.sum((g - r) > 50)) / total
            return red_pct, green_pct

        left_red, left_green = strip_signal(left_strip)
        right_red, right_green = strip_signal(right_strip)

        # Detect TRANSITIONS: compare against previous frame's signal
        left_color = ""
        right_color = ""

        if prev_left_red is not None:
            # Red touch line APPEARS: left red jumps by >20% from previous frame
            if left_red - prev_left_red > 0.20:
                left_color = "red"
            # Green touch line APPEARS on the right side
            if right_green - prev_right_green > 0.20:
                right_color = "green"

        prev_left_red = left_red
        prev_left_green = left_green
        prev_right_red = right_red
        prev_right_green = right_green

        # Determine if a touch happened (only on-target: red or green)
        touch_detected = False
        touch_side = ""

        if left_color == "red" and right_color == "green":
            touch_detected = True
            touch_side = "both"
        elif left_color == "red":
            touch_detected = True
            touch_side = "left"
        elif right_color == "green":
            touch_detected = True
            touch_side = "right"

        if touch_detected:
            light_s = i / fps
            # Clip: 3s before touch to 5s after (captures action + referee decision)
            clip_start = max(0, light_s - 3.0)
            clip_end = light_s + 5.0

            exchanges.append(
                Exchange(
                    light_onset_frame=i,
                    score_update_frame=i + int(5 * fps),  # approximate
                    light_onset_s=light_s,
                    score_update_s=light_s + 5.0,
                    clip_start_s=clip_start,
                    clip_end_s=clip_end,
                    side=touch_side,
                )
            )

            # Cooldown: skip 6s after touch (covers the reset period)
            cooldown_until = i + int(6 * fps)

        prev_bar = bar.copy()

    container.close()
    return exchanges


def download_video(url: str) -> str:
    """Download a full video from YouTube to a temp file.

    Downloads without --download-sections to avoid keyframe-snapping errors.
    """
    tmp = tempfile.mktemp(suffix=".mp4")
    print(f"Downloading full video from {url}...")
    cmd = [
        "yt-dlp",
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
    size_mb = Path(tmp).stat().st_size / (1024 * 1024)
    print(f"Downloaded ({size_mb:.0f} MB)")
    return tmp


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract exchange timestamps from fencing video")
    parser.add_argument("video", help="Local video path or YouTube URL")
    parser.add_argument("--output", type=Path, default=None, help="Output directory for trimmed clips")
    args = parser.parse_args()

    video_path = args.video
    is_url = video_path.startswith("http")

    if is_url:
        video_path = download_video(video_path)

    print(f"Scanning for exchanges...")
    exchanges = detect_exchanges(video_path)

    if not exchanges:
        print("No exchanges detected.")
        if is_url:
            Path(video_path).unlink(missing_ok=True)
        return

    print(f"\nFound {len(exchanges)} exchange(s):\n")
    print(f"{'#':>3}  {'Light (s)':>10}  {'Score (s)':>10}  {'Clip start':>10}  {'Clip end':>10}  Side")
    print("-" * 70)
    for j, ex in enumerate(exchanges):
        print(
            f"{j + 1:3d}  {ex.light_onset_s:10.2f}  {ex.score_update_s:10.2f}  "
            f"{ex.clip_start_s:10.2f}  {ex.clip_end_s:10.2f}  {ex.side}"
        )

    # Trim clips if output dir specified
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        for j, ex in enumerate(exchanges):
            out_path = args.output / f"exchange_{j + 1:03d}_{ex.side}.mp4"
            duration = ex.clip_end_s - ex.clip_start_s
            print(f"\nTrimming exchange {j + 1} to {out_path}...")
            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                video_path,
                "-ss",
                str(ex.clip_start_s),
                "-t",
                str(duration),
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
            subprocess.run(cmd, capture_output=True, check=True)
            size_mb = out_path.stat().st_size / (1024 * 1024)
            print(f"  {size_mb:.1f} MB")

    if is_url:
        Path(video_path).unlink(missing_ok=True)


if __name__ == "__main__":
    main()
