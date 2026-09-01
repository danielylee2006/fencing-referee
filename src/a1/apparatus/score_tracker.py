"""Score change detection for FencingVision overlay.

Uses OCR (EasyOCR) to read actual score digits, then compares before/after
a touch to determine which side scored. Also detects paused clock
(equipment test / blade test filter).

Only the old (dark blue) FencingVision overlay is supported:
  - Dark blue bar: y=615-650
  - Score digits: y=617-648
  - Touch indicator strip: y=654-669

X-positions:
  - Left score: x≈490-595 (widened to capture both digits of double-digit scores 0-15)
  - Right score: x≈685-790 (widened to capture both digits of double-digit scores 0-15)
  - Clock: x≈590-690

All positions scale proportionally with frame resolution.
Videos using the new (grey) overlay are rejected at the pipeline entry point.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import cv2
import numpy as np


def is_old_overlay(frame: np.ndarray) -> bool:
    """Check if a frame uses the supported old (dark blue) FencingVision overlay.

    The old overlay has a dark blue bar (brightness ~149, B > R).
    The unsupported new overlay has a neutral grey bar (brightness ~176).
    """
    h, w = frame.shape[:2]
    sy = h / 720.0
    sx = w / 1280.0
    y1, y2 = int(625 * sy), int(635 * sy)
    x1, x2 = int(320 * sx), int(960 * sx)
    bar_sample = frame[y1:y2, x1:x2, :]
    r = float(bar_sample[:, :, 0].mean())
    b = float(bar_sample[:, :, 2].mean())
    brightness = (r + float(bar_sample[:, :, 1].mean()) + b) / 3
    return brightness < 160 and b > r


def has_clock(frame: np.ndarray) -> bool:
    """Check if the overlay has a visible clock in the clock region.

    Some FencingVision old-overlay videos display no clock at all — the
    clock region is a bright blank area (~220 mean brightness). Videos
    with a clock (running or paused) have brightness ~170-184 and OCR
    can read time values like '3:00'.

    Without a clock, blade tests cannot be detected (no paused-clock
    filter), so clockless videos must be skipped.
    """
    h, w = frame.shape[:2]
    regions = OverlayRegions.from_frame_size(h, w)
    crop = extract_region(frame, regions.clock)
    brightness = float(crop.mean())
    # Clockless videos: brightness ~220. Clock present: ~170-184.
    # Threshold at 200 gives clear separation.
    if brightness > 200:
        return False
    # Double-check with OCR — if brightness is borderline, try to read it
    val = _read_clock(frame, regions.clock)
    return val is not None


@dataclass
class OverlayRegions:
    """Pixel regions for the FencingVision overlay, proportional to frame size.

    Positions are for the old (dark blue) overlay only, at 720p reference resolution:
      bar: y=615-650, score digits: y=617-648, touch strip: y=654-669

    Score x-ranges are widened to cover both digits of any score 0-15:
      left score digit "1" starts at x≈535, "5" ends at x≈649 (at score 15)
      right score digit "1" starts at x≈680, "0" ends at x≈746 (at score 10)
    """

    bar_top: int
    bar_bottom: int
    left_score: tuple[int, int, int, int]  # y1, y2, x1, x2
    right_score: tuple[int, int, int, int]
    clock: tuple[int, int, int, int]
    left_strip: tuple[int, int, int, int]  # touch indicator strip regions
    right_strip: tuple[int, int, int, int]

    @classmethod
    def from_frame_size(cls, h: int, w: int) -> "OverlayRegions":
        """Compute overlay regions from known FencingVision proportions."""
        sy = h / 720.0
        sx = w / 1280.0

        bar_top = int(615 * sy)
        bar_bottom = int(650 * sy)

        score_y1 = int(617 * sy)
        score_y2 = int(648 * sy)

        ls_x1, ls_x2 = int(490 * sx), int(595 * sx)
        rs_x1, rs_x2 = int(685 * sx), int(790 * sx)

        clock_x1, clock_x2 = int(590 * sx), int(690 * sx)

        strip_y1 = int(654 * sy)
        strip_y2 = int(669 * sy)
        mid_x = w // 2

        return cls(
            bar_top=bar_top,
            bar_bottom=bar_bottom,
            left_score=(score_y1, score_y2, ls_x1, ls_x2),
            right_score=(score_y1, score_y2, rs_x1, rs_x2),
            clock=(score_y1, score_y2, clock_x1, clock_x2),
            left_strip=(strip_y1, strip_y2, int(40 * sx), mid_x),
            right_strip=(strip_y1, strip_y2, mid_x, int(1240 * sx)),
        )


def extract_region(frame: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
    """Extract a region from a frame."""
    y1, y2, x1, x2 = region
    return frame[y1:y2, x1:x2, :]


@lru_cache(maxsize=1)
def _get_ocr_reader():  # type: ignore[no-untyped-def]
    """Lazy-load EasyOCR reader (downloads model on first call)."""
    import easyocr

    return easyocr.Reader(["en"], gpu=False, verbose=False)


def read_score(frame: np.ndarray, region: tuple[int, int, int, int]) -> int | None:
    """Read a score digit from a frame region using OCR.

    Returns the integer score, or None if OCR fails.
    """
    crop = extract_region(frame, region)
    if crop.size == 0:
        return None

    # Upscale 6x for OCR reliability on small regions.
    # 4x fails on thin digits like "7"; 6x reads all 0-15 reliably.
    big = cv2.resize(
        crop,
        (crop.shape[1] * 6, crop.shape[0] * 6),
        interpolation=cv2.INTER_CUBIC,
    )

    reader = _get_ocr_reader()
    results = reader.readtext(big, allowlist="0123456789", paragraph=False)

    if not results:
        return None

    text = results[0][1]
    try:
        return int(text)
    except ValueError:
        return None


def clock_is_running(
    frames: list[np.ndarray],
    regions: OverlayRegions,
    frame_start: int,
    frame_end: int,
) -> bool:
    """Check if the clock is running by reading the clock via OCR.

    Reads the clock at two points ~2 seconds apart. If the values
    differ, the clock is running. If they're the same, it's stopped
    (blade test / equipment check).
    """
    if frame_end - frame_start < 25:
        return True  # not enough separation to check

    # Read clock at start and end of window
    t1 = _read_clock(frames[frame_start], regions.clock)
    t2 = _read_clock(frames[min(frame_end - 1, len(frames) - 1)], regions.clock)

    if t1 is None or t2 is None:
        return True  # assume running if OCR fails

    return t1 != t2


def _read_clock(frame: np.ndarray, region: tuple[int, int, int, int]) -> str | None:
    """Read clock text from a frame region via OCR."""
    crop = extract_region(frame, region)
    if crop.size == 0:
        return None

    big = cv2.resize(
        crop,
        (crop.shape[1] * 6, crop.shape[0] * 6),
        interpolation=cv2.INTER_CUBIC,
    )

    reader = _get_ocr_reader()
    results = reader.readtext(big, allowlist="0123456789:", paragraph=False)

    if not results:
        return None

    return results[0][1]


@dataclass
class ScoreChange:
    """Result of score change detection after a touch."""

    side: str  # "left", "right", "both", "none"
    change_frame: int  # frame where the change was first detected
    change_time_s: float  # timestamp of the change
    clock_running: bool  # whether the clock was running at touch time
    left_before: int | None = None
    left_after: int | None = None
    right_before: int | None = None
    right_after: int | None = None


def detect_score_change(
    frames: list[np.ndarray],
    touch_frame: int,
    fps: float,
    regions: OverlayRegions | None = None,
    lookback_frames: int = 25,
    lookahead_frames: int = 100,
    skip_clock_check: bool = False,
) -> ScoreChange:
    """Detect which side's score changes after a touch using OCR.

    Reads the score digits before the touch, then scans forward at
    1-second intervals to find when/if the score changes.

    Args:
        frames: list of video frames as numpy arrays
        touch_frame: frame index where the touch light was detected
        fps: video frame rate
        regions: overlay regions (computed from frame size if None)
        lookback_frames: frames before touch to read baseline score
        lookahead_frames: frames after touch to scan for score change
        skip_clock_check: if True, skip the clock OCR check (caller
            already verified the clock is running)

    Returns:
        ScoreChange with the detected side, timing, and score values
    """
    if not frames:
        return ScoreChange(side="none", change_frame=-1, change_time_s=0, clock_running=True)

    h, w = frames[0].shape[:2]
    if regions is None:
        regions = OverlayRegions.from_frame_size(h, w)

    # Read baseline scores from before the touch
    baseline_frame = max(0, touch_frame - lookback_frames)
    left_before = read_score(frames[baseline_frame], regions.left_score)
    right_before = read_score(frames[baseline_frame], regions.right_score)

    # Check clock via OCR — read at two points before the touch
    if skip_clock_check:
        clock_running = True
    else:
        clock_start = max(0, touch_frame - 50)
        clock_end = touch_frame
        clock_running = clock_is_running(frames, regions, clock_start, clock_end)

    if left_before is None and right_before is None:
        return ScoreChange(
            side="none", change_frame=-1, change_time_s=0,
            clock_running=clock_running,
        )

    # Scan forward for score change, bounded by lookahead_frames.
    # The caller sets lookahead_frames to the next exchange's light
    # onset, which is the hard boundary of this exchange. Any score
    # change after the next light fires belongs to a different exchange.
    #
    # Strategy: scan at 1-second intervals. Use cheap pixel-diff to
    # detect if the score region changed, then confirm with OCR only
    # on frames where pixels actually moved. This cuts OCR calls from
    # ~20-60 per exchange down to ~2-4.
    scan_end = min(touch_frame + lookahead_frames, len(frames))
    step = max(1, int(fps))  # ~1 second intervals

    left_changed_frame = -1
    right_changed_frame = -1
    left_after = left_before
    right_after = right_before

    # Capture baseline pixel snapshots for cheap diff comparison.
    # Convert to float32 once to avoid repeated casts in the loop.
    baseline_left_pixels = extract_region(
        frames[baseline_frame], regions.left_score,
    ).astype(np.float32)
    baseline_right_pixels = extract_region(
        frames[baseline_frame], regions.right_score,
    ).astype(np.float32)

    # Pixel-diff threshold: a score digit change produces a mean
    # absolute diff of ~5.7-8.8 across the region. No-change noise
    # (overlay glow, compression) is ~2.0-4.3. Threshold at 5.0
    # sits in the gap between noise max and change min.
    PIXEL_DIFF_THRESHOLD = 5.0

    for i in range(touch_frame, scan_end, step):
        # Cheap pixel-diff gate: skip OCR if pixels haven't changed
        if left_changed_frame < 0 and left_before is not None:
            left_pixels = extract_region(
                frames[i], regions.left_score,
            ).astype(np.float32)
            left_diff = float(np.mean(np.abs(left_pixels - baseline_left_pixels)))
            if left_diff > PIXEL_DIFF_THRESHOLD:
                l = read_score(frames[i], regions.left_score)
                if l is not None and l != left_before:
                    left_changed_frame = i
                    left_after = l

        if right_changed_frame < 0 and right_before is not None:
            right_pixels = extract_region(
                frames[i], regions.right_score,
            ).astype(np.float32)
            right_diff = float(np.mean(np.abs(right_pixels - baseline_right_pixels)))
            if right_diff > PIXEL_DIFF_THRESHOLD:
                r = read_score(frames[i], regions.right_score)
                if r is not None and r != right_before:
                    right_changed_frame = i
                    right_after = r

        if left_changed_frame >= 0 and right_changed_frame >= 0:
            break

    # Determine result
    left_changed = left_changed_frame >= 0
    right_changed = right_changed_frame >= 0

    if left_changed and right_changed:
        side = "both"
        change_frame = min(left_changed_frame, right_changed_frame)
    elif left_changed:
        side = "left"
        change_frame = left_changed_frame
    elif right_changed:
        side = "right"
        change_frame = right_changed_frame
    else:
        side = "none"
        change_frame = -1

    change_time = change_frame / fps if change_frame >= 0 else 0

    return ScoreChange(
        side=side,
        change_frame=change_frame,
        change_time_s=change_time,
        clock_running=clock_running,
        left_before=left_before,
        left_after=left_after,
        right_before=right_before,
        right_after=right_after,
    )
