"""Exchange quality filters for the corpus acquisition pipeline.

Each filter returns a flag (string) if the exchange should be flagged,
or None if it passes. Flagged exchanges are included in the corpus
but marked for review. Only clock_paused is a hard rejection — the
rest are quality warnings.

Filters:
    - clock_paused: bout clock not running before the touch (blade test)
    - no_score_change: no score digit changed after the touch
    - score_change_too_late: score changed but very late (possible misattribution)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from a1.apparatus.score_tracker import (
    OverlayRegions,
    ScoreChange,
    clock_is_running,
    detect_score_change,
    extract_region,
)


@dataclass
class ExchangeQuality:
    """Quality assessment for a detected exchange."""

    # Hard reject — do not include in corpus
    reject: bool = False
    reject_reason: str = ""

    # Soft flags — include but mark for review
    flags: list[str] = field(default_factory=list)

    # Detected label from score change
    label: str = ""  # "LEFT", "RIGHT", "NONE"

    # Score change details
    score_change: ScoreChange | None = None

    # Clock state
    clock_running_before: bool = True


def assess_exchange(
    frames: list[np.ndarray],
    touch_frame: int,
    fps: float,
    weapon: str = "foil",
) -> ExchangeQuality:
    """Assess the quality of a detected exchange.

    Args:
        frames: all video frames as numpy arrays
        touch_frame: frame where the touch light was detected
        fps: video frame rate
        weapon: "foil", "sabre", or "epee"

    Returns:
        ExchangeQuality with reject/flag decisions and detected label
    """
    result = ExchangeQuality()

    if not frames or touch_frame < 0 or touch_frame >= len(frames):
        result.reject = True
        result.reject_reason = "invalid_frame_data"
        return result

    # --- Step 1: Detect overlay and score regions ---
    detect_start = max(0, touch_frame - 30)
    detect_end = min(len(frames), touch_frame + 10)
    regions = OverlayRegions.detect(frames[detect_start:detect_end])

    if regions is None:
        result.reject = True
        result.reject_reason = "overlay_not_detected"
        return result

    # --- Step 2: Check clock before touch ---
    clock_start = max(0, touch_frame - 50)
    clock_end = touch_frame
    clock_frames = [
        extract_region(frames[i], regions.clock)
        for i in range(clock_start, min(clock_end, len(frames)))
    ]
    result.clock_running_before = clock_is_running(clock_frames)

    if not result.clock_running_before:
        result.reject = True
        result.reject_reason = "clock_paused"
        return result

    # --- Step 3: Detect score change ---
    result.score_change = detect_score_change(
        frames, touch_frame, fps, regions, lookback_frames=25, lookahead_frames=100
    )

    # --- Step 4: Determine label ---
    sc = result.score_change

    if weapon == "epee":
        # Epee has no priority — label is always NONE regardless of score
        result.label = "NONE"
        if sc.side == "none":
            result.flags.append("epee_no_score_change")
    elif sc.side == "none":
        # Foil/sabre: light fired but no point awarded
        # Could be off-target, annulment, or blade test that slipped through
        result.label = "NONE"
        result.flags.append("no_score_change")
    elif sc.side in ("left", "right"):
        result.label = sc.side.upper()

        # Check if score change was very late (>4 seconds after touch)
        delay = sc.change_time_s - (touch_frame / fps)
        if delay > 4.0:
            result.flags.append("late_score_change")
    elif sc.side == "both":
        # Both scores changed — unusual, might be a detection error
        result.label = "NONE"
        result.flags.append("both_scores_changed")

    return result
