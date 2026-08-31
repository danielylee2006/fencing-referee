"""Extract exchange timestamps from FencingVision videos.

Only the old (dark blue) FencingVision overlay is supported. Videos using
the new (grey) overlay are rejected immediately with a warning.

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

The old FencingVision overlay (dark blue bar, y=615-650 at 720p):
- Touch indicator strip: y=654-669
  - Red line = left fencer's touch (valid, on-target)
  - Green line = right fencer's touch (valid, on-target)
  - White line = off-target touch
  - Both red+green = double touch
- Off-target square: small white square at y=670-700 below the bar
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

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from a1.apparatus.score_tracker import is_old_overlay


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
    cooldown_until: int = 0

    # Previous frame's strip signals (for transition detection)
    prev_left_red: float | None = None
    prev_left_green: float = 0.0
    prev_right_red: float = 0.0
    prev_right_green: float | None = None
    # For white: track mean brightness of just the bright-neutral pixels
    prev_left_white_bright: float = 0.0
    prev_right_white_bright: float = 0.0

    # Baseline: collect the touch-indicator strip from first 50 frames
    baseline_left_strips: list[np.ndarray] = []
    baseline_right_strips: list[np.ndarray] = []

    # Pending touch awaiting second-light check (FIE 300ms lockout window)
    pending_touch: dict | None = None

    # Previous frame's off-target square signals
    prev_left_offtarget: float = 0.0
    prev_right_offtarget: float = 0.0

    def strip_signal(strip: np.ndarray) -> tuple[float, float, float]:
        """Compute red, green, and white-bright signal strength in a strip.

        Returns (red_pct, green_pct, white_bright_pct):
        - red_pct: fraction of pixels where R dominates G by >50
        - green_pct: fraction of pixels where G dominates R by >50
        - white_bright_pct: fraction of pixels that are bright (>200)
          AND neutral (no strong color). The off-target (white) indicator
          is very bright white; ambient grey overlay is 100-180.
        """
        r = strip[:, :, 0].astype(np.float32)
        g = strip[:, :, 1].astype(np.float32)
        b = strip[:, :, 2].astype(np.float32)
        total = strip.shape[0] * strip.shape[1]
        red_pct = float(np.sum((r - g) > 50)) / total
        green_pct = float(np.sum((g - r) > 50)) / total
        # White indicator: very bright AND color-neutral
        # Threshold 200 (not 180) avoids false positives from grey overlay
        bright = (r > 200) & (g > 200) & (b > 200)
        neutral = (np.abs(r - g) < 40) & (np.abs(g - b) < 40)
        white_pct = float(np.sum(bright & neutral)) / total
        return red_pct, green_pct, white_pct

    for i, frame in enumerate(container.decode(video=0)):
        img = frame.to_ndarray(format="rgb24")
        h, w = img.shape[:2]
        sy = h / 720
        sx = w / 1280

        # --- Gate: reject unsupported overlay on frame 0 ---
        if i == 0:
            if not is_old_overlay(img):
                print("Skipping: unsupported overlay (not old FencingVision)")
                container.close()
                return []

        # --- Regions ---
        # Touch indicator strip: colored line below the overlay bar (old overlay only)
        # Old overlay strip: y=654-669 at 720p reference
        strip_y1, strip_y2 = int(654 * sy), int(669 * sy)
        # Left half and right half of the strip
        mid_x = w // 2
        left_strip = img[strip_y1:strip_y2, int(40 * sx) : mid_x, :]
        right_strip = img[strip_y1:strip_y2, mid_x : int(1240 * sx), :]

        # --- Build baseline from first 50 frames ---
        if i < 50:
            baseline_left_strips.append(left_strip.astype(np.float32))
            baseline_right_strips.append(right_strip.astype(np.float32))
            continue

        if i == 50:
            # Compute separate baselines for left and right strips
            left_mean = np.mean(baseline_left_strips, axis=0)
            right_mean = np.mean(baseline_right_strips, axis=0)
            baseline_left_r = float(np.mean(left_mean[:, :, 0]))
            baseline_left_g = float(np.mean(left_mean[:, :, 1]))
            baseline_right_r = float(np.mean(right_mean[:, :, 0]))
            baseline_right_g = float(np.mean(right_mean[:, :, 1]))

        left_red, left_green, left_white = strip_signal(left_strip)
        right_red, right_green, right_white = strip_signal(right_strip)

        # Off-target square region: small white square below the bar at y=670-700.
        # Computed each frame, checked during touch lookahead.
        ot_y1, ot_y2 = int(670 * sy), int(700 * sy)
        _, _, cur_left_offtarget = strip_signal(
            img[ot_y1:ot_y2, int(40 * sx) : mid_x, :]
        )
        _, _, cur_right_offtarget = strip_signal(
            img[ot_y1:ot_y2, mid_x : int(1240 * sx), :]
        )

        # --- Check pending touch for second light ---
        # FIE allows 300ms (≈8 frames at 25fps) between first and second hit.
        # Check if the other light appears within this window.
        if pending_touch is not None:
            pt = pending_touch
            if pt["remaining"] > 0:
                # Check for second light appearing during the lookahead window.
                # For red/green: absolute color dominance (these are near-zero at rest).
                # For white: use TRANSITION from the baseline captured when the first
                # touch fired — the right strip has permanent bright-neutral pixels
                # (~0.09–0.38) that would always exceed an absolute threshold.
                right_white_delta = right_white - pt["baseline_right_white"]
                left_white_delta = left_white - pt["baseline_left_white"]
                if pt["side"] == "left" and (right_green > 0.15 or right_white_delta > 0.08):
                    pt["side"] = "both"
                elif pt["side"] == "right" and (left_red > 0.15 or left_white_delta > 0.08):
                    pt["side"] = "both"

                # Off-target square: small white square at y=670-700, below the
                # touch strip. Too small to trigger the 8% strip threshold.
                # Check this region with a lower threshold (3%).
                if pt["side"] != "both":
                    if pt["side"] == "left":
                        if cur_right_offtarget - pt["baseline_right_offtarget"] > 0.03:
                            pt["side"] = "both"
                    elif pt["side"] == "right":
                        if cur_left_offtarget - pt["baseline_left_offtarget"] > 0.03:
                            pt["side"] = "both"
                pt["remaining"] -= 1

                if pt["remaining"] > 0 and pt["side"] != "both":
                    prev_left_red = left_red
                    prev_right_green = right_green
                    prev_left_white_bright = left_white
                    prev_right_white_bright = right_white
                    prev_left_offtarget = cur_left_offtarget
                    prev_right_offtarget = cur_right_offtarget
                    continue

            # Window expired or second light found — commit the exchange
            exchanges.append(
                Exchange(
                    light_onset_frame=pt["onset_frame"],
                    score_update_frame=pt["onset_frame"] + int(5 * fps),
                    light_onset_s=pt["light_s"],
                    score_update_s=pt["light_s"] + 5.0,
                    clip_start_s=pt["clip_start"],
                    clip_end_s=pt["clip_end"],
                    side=pt["side"],
                )
            )
            cooldown_until = pt["onset_frame"] + int(6 * fps)
            pending_touch = None

        if i < cooldown_until:
            prev_left_red = left_red
            prev_right_green = right_green
            prev_left_white_bright = left_white
            prev_right_white_bright = right_white
            prev_left_offtarget = cur_left_offtarget
            prev_right_offtarget = cur_right_offtarget
            continue

        # --- Detect touch indicator line ---
        # Detect TRANSITIONS: compare against previous frame's signal.
        # Red/green: color dominance transition (>20% jump)
        # White: bright-neutral pixel fraction transition (>8% jump,
        #   with higher brightness threshold of 200 to avoid false positives)
        left_color = ""
        right_color = ""

        if prev_left_red is not None:
            # Red touch line on left side
            if left_red - prev_left_red > 0.20:
                left_color = "red"
            # White (off-target) on left side
            elif left_white - prev_left_white_bright > 0.08:
                left_color = "white"
            # Green touch line on right side
            if right_green - prev_right_green > 0.20:
                right_color = "green"
            # White (off-target) on right side
            elif right_white - prev_right_white_bright > 0.08:
                right_color = "white"

        prev_left_red = left_red
        prev_left_green = left_green
        prev_right_red = right_red
        prev_right_green = right_green
        prev_left_white_bright = left_white
        prev_right_white_bright = right_white
        prev_left_offtarget = cur_left_offtarget
        prev_right_offtarget = cur_right_offtarget

        # Determine if a touch happened (red, green, or white)
        touch_detected = False
        touch_side = ""

        has_left = left_color in ("red", "white")
        has_right = right_color in ("green", "white")

        if has_left and has_right:
            touch_detected = True
            touch_side = "both"
        elif has_left:
            touch_detected = True
            touch_side = "left"
        elif has_right:
            touch_detected = True
            touch_side = "right"

        if touch_detected:
            light_s = i / fps
            clip_start = max(0, light_s - 3.0)
            clip_end = light_s + 5.0

            if touch_side == "both":
                # Both lights on same frame — commit immediately
                exchanges.append(
                    Exchange(
                        light_onset_frame=i,
                        score_update_frame=i + int(5 * fps),
                        light_onset_s=light_s,
                        score_update_s=light_s + 5.0,
                        clip_start_s=clip_start,
                        clip_end_s=clip_end,
                        side="both",
                    )
                )
                cooldown_until = i + int(6 * fps)
            else:
                # Buffer touch — check next 8 frames for second light.
                # Capture white baselines so lookahead uses transition detection.
                #
                # Off-target square: also check immediately. The square can appear
                # on the same frame as the touch or 1 frame before, making
                # transition detection during lookahead impossible. If the off-target
                # region currently has bright-neutral pixels above a low absolute
                # threshold, the square is already present.
                if touch_side == "left" and cur_right_offtarget > 0.02:
                    touch_side = "both"
                elif touch_side == "right" and cur_left_offtarget > 0.02:
                    touch_side = "both"
                if touch_side == "both":
                    exchanges.append(
                        Exchange(
                            light_onset_frame=i,
                            score_update_frame=i + int(5 * fps),
                            light_onset_s=light_s,
                            score_update_s=light_s + 5.0,
                            clip_start_s=clip_start,
                            clip_end_s=clip_end,
                            side="both",
                        )
                    )
                    cooldown_until = i + int(6 * fps)
                    prev_left_red = left_red
                    prev_right_green = right_green
                    prev_left_white_bright = left_white
                    prev_right_white_bright = right_white
                    prev_left_offtarget = cur_left_offtarget
                    prev_right_offtarget = cur_right_offtarget
                    continue

                pending_touch = {
                    "onset_frame": i,
                    "side": touch_side,
                    "light_s": light_s,
                    "clip_start": clip_start,
                    "clip_end": clip_end,
                    "remaining": 8,
                    "baseline_left_white": left_white,
                    "baseline_right_white": right_white,
                    "baseline_left_offtarget": prev_left_offtarget,
                    "baseline_right_offtarget": prev_right_offtarget,
                }

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
