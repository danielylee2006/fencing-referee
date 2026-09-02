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
    lookahead_frames: int | None = None,
) -> ExchangeQuality:
    """Assess the quality of a detected exchange.

    Args:
        frames: all video frames as numpy arrays
        touch_frame: frame where the touch light was detected
        fps: video frame rate
        weapon: "foil", "sabre", or "epee"
        lookahead_frames: max frames to scan for score change (default: all remaining)

    Returns:
        ExchangeQuality with reject/flag decisions and detected label
    """
    result = ExchangeQuality()

    if not frames or touch_frame < 0 or touch_frame >= len(frames):
        result.reject = True
        result.reject_reason = "invalid_frame_data"
        return result

    h, w = frames[0].shape[:2]
    regions = OverlayRegions.from_frame_size(h, w)

    # --- Step 1: Check clock before touch ---
    # Sabre does not use a running bout clock between touches — the clock
    # stays paused. Skip the clock check entirely for sabre.
    if weapon != "sabre":
        clock_start = max(0, touch_frame - 50)
        clock_end = touch_frame
        result.clock_running_before = clock_is_running(
            frames, regions, clock_start, clock_end,
        )

        if not result.clock_running_before:
            result.reject = True
            result.reject_reason = "clock_paused"
            return result

    # --- Step 2: Detect score change via OCR ---
    # Skip the clock check inside detect_score_change since we already
    # verified it above.
    la = lookahead_frames if lookahead_frames is not None else len(frames) - touch_frame
    result.score_change = detect_score_change(
        frames, touch_frame, fps, regions, lookback_frames=25,
        lookahead_frames=la,
        skip_clock_check=True,
    )

    # --- Step 3: Determine label ---
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

        # Check if score change was very late (>6 seconds after touch)
        # 4-5s delays are normal — referee watches replay, discusses
        delay = sc.change_time_s - (touch_frame / fps)
        if delay > 6.0:
            result.flags.append("late_score_change")
    elif sc.side == "both":
        # Both scores changed. Common cause: the bout-winning touch
        # makes one score go up while the overlay resets the other to 0.
        # If one side went up and the other went down (or to 0), the
        # side that went up is the real point.
        left_up = (
            sc.left_before is not None
            and sc.left_after is not None
            and sc.left_after > sc.left_before
        )
        right_up = (
            sc.right_before is not None
            and sc.right_after is not None
            and sc.right_after > sc.right_before
        )
        if left_up and not right_up:
            result.label = "LEFT"
            result.flags.append("both_scores_changed")
        elif right_up and not left_up:
            result.label = "RIGHT"
            result.flags.append("both_scores_changed")
        else:
            # Both went up or can't determine — flag for review
            result.label = "NONE"
            result.flags.append("both_scores_changed")

    return result
