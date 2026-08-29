"""Score change detection for FencingVision overlay.

Auto-detects the overlay bar position, then monitors score digit regions
for changes after a touch. No hard-coded pixel coordinates — the bar and
score positions are found automatically per video.

Also detects paused clock (equipment test / blade test filter).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class OverlayRegions:
    """Pixel regions for the FencingVision overlay, auto-detected."""

    bar_top: int
    bar_bottom: int
    bar_left: int
    bar_right: int
    left_score: tuple[int, int, int, int]  # y1, y2, x1, x2
    right_score: tuple[int, int, int, int]
    clock: tuple[int, int, int, int]

    @classmethod
    def detect(cls, frames: list[np.ndarray]) -> OverlayRegions | None:
        """Auto-detect overlay regions by averaging multiple frames.

        Finds the grey score bar in the bottom 15% of the frame, then
        locates score digits and clock by finding dark pixel clusters
        on the grey background.
        """
        if not frames:
            return None

        # Average frames to reduce noise from fencer movement
        avg = np.mean(
            [f.astype(np.float32) for f in frames[:min(20, len(frames))]],
            axis=0,
        ).astype(np.uint8)

        h, w = avg.shape[:2]

        # --- Step 1: Find the grey bar ---
        # Scan bottom 15% for rows with >45% grey pixels
        scan_start = int(h * 0.83)
        grey_rows: list[tuple[int, float, int, int]] = []

        for y in range(scan_start, h):
            row = avg[y, :, :]
            r = row[:, 0].astype(np.float32)
            g = row[:, 1].astype(np.float32)
            b = row[:, 2].astype(np.float32)
            brightness = (r + g + b) / 3
            color_var = np.abs(r - g) + np.abs(g - b) + np.abs(r - b)
            grey_mask = (color_var < 60) & (brightness > 130) & (brightness < 210)
            grey_frac = float(grey_mask.sum()) / w

            if grey_frac > 0.45:
                grey_cols = np.where(grey_mask)[0]
                grey_rows.append((y, grey_frac, int(grey_cols[0]), int(grey_cols[-1])))

        if len(grey_rows) < 20:
            return None

        # Find longest contiguous block of grey rows
        ys = [r[0] for r in grey_rows]
        best_start = 0
        best_len = 1
        cur_start = 0
        for i in range(1, len(ys)):
            if ys[i] - ys[i - 1] > 2:
                if i - cur_start > best_len:
                    best_len = i - cur_start
                    best_start = cur_start
                cur_start = i
        if len(ys) - cur_start > best_len:
            best_len = len(ys) - cur_start
            best_start = cur_start

        bar_rows = grey_rows[best_start : best_start + best_len]
        bar_top = bar_rows[0][0]
        bar_bottom = bar_rows[-1][0]
        bar_right = int(np.median([r[3] for r in bar_rows]))
        bar_left = int(np.median([r[2] for r in bar_rows]))

        # --- Step 2: Locate score digits and clock ---
        # The FencingVision overlay template places elements at fixed
        # proportional positions relative to the frame center. The bar
        # y-position can shift slightly between events, but the x-layout
        # is fixed for a given resolution.
        #
        # At 1280x720:
        #   Left score digit center:  x ≈ 545  (frame_center - 95)
        #   Clock center:             x ≈ 640  (frame_center)
        #   Right score digit center: x ≈ 735  (frame_center + 95)
        #
        # We scale these proportionally to the actual frame width.
        sx = w / 1280.0
        frame_cx = w // 2
        score_offset = int(95 * sx)
        score_half_w = int(25 * sx)  # half-width of score region
        clock_half_w = int(50 * sx)

        ls_cx = frame_cx - score_offset
        rs_cx = frame_cx + score_offset

        ls_x1 = ls_cx - score_half_w
        ls_x2 = ls_cx + score_half_w
        rs_x1 = rs_cx - score_half_w
        rs_x2 = rs_cx + score_half_w
        clock_x1 = frame_cx - clock_half_w
        clock_x2 = frame_cx + clock_half_w

        text_y1 = bar_top + (bar_bottom - bar_top) // 4
        text_y2 = bar_bottom - (bar_bottom - bar_top) // 4

        return cls(
            bar_top=bar_top,
            bar_bottom=bar_bottom,
            bar_left=bar_left,
            bar_right=bar_right,
            left_score=(text_y1, text_y2, ls_x1, ls_x2),
            right_score=(text_y1, text_y2, rs_x1, rs_x2),
            clock=(text_y1, text_y2, clock_x1, clock_x2),
        )


def extract_region(frame: np.ndarray, region: tuple[int, int, int, int]) -> np.ndarray:
    """Extract a region from a frame."""
    y1, y2, x1, x2 = region
    return frame[y1:y2, x1:x2, :]


def region_signature(region: np.ndarray) -> float:
    """Compute a signature for a score region.

    Uses the count of dark pixels (the digit strokes) as a stable
    metric that changes when the digit changes but is robust to
    minor brightness fluctuations.
    """
    gray = region.mean(axis=2)
    return float(np.sum(gray < 100))


def region_changed(sig_a: float, sig_b: float, threshold: float = 10.0) -> bool:
    """Check if a score region changed between two signatures."""
    return abs(sig_a - sig_b) > threshold


def clock_is_running(
    clock_frames: list[np.ndarray],
    min_frames: int = 10,
    drift_threshold: float = 1.5,
) -> bool:
    """Check if the clock is running by measuring cumulative pixel drift.

    At 25fps, frame-to-frame clock diffs are tiny (<0.05). Instead,
    compare the first and last frames in the window — a running clock
    drifts ~2-3 over 50 frames (2 seconds), while a paused clock
    stays below ~0.8.
    """
    if len(clock_frames) < min_frames:
        return True  # assume running if not enough data

    first = clock_frames[0].astype(np.float32)
    last = clock_frames[-1].astype(np.float32)
    drift = float(np.mean(np.abs(last - first)))
    return drift > drift_threshold


@dataclass
class ScoreChange:
    """Result of score change detection after a touch."""

    side: str  # "left", "right", "both", "none"
    change_frame: int  # frame where the change was first detected
    change_time_s: float  # timestamp of the change
    clock_running: bool  # whether the clock was running at touch time


def detect_score_change(
    frames: list[np.ndarray],
    touch_frame: int,
    fps: float,
    regions: OverlayRegions | None = None,
    lookback_frames: int = 25,
    lookahead_frames: int = 100,
) -> ScoreChange:
    """Detect which side's score changes after a touch.

    Args:
        frames: list of all video frames as numpy arrays
        touch_frame: frame index where the touch light was detected
        fps: video frame rate
        regions: overlay regions (auto-detected if None)
        lookback_frames: frames before touch to establish baseline
        lookahead_frames: frames after touch to look for score change

    Returns:
        ScoreChange with the detected side and timing
    """
    if not frames:
        return ScoreChange(side="none", change_frame=-1, change_time_s=0, clock_running=True)

    if regions is None:
        # Use frames around the touch for detection
        detect_start = max(0, touch_frame - 30)
        detect_end = min(len(frames), touch_frame + 10)
        regions = OverlayRegions.detect(frames[detect_start:detect_end])
        if regions is None:
            return ScoreChange(
                side="none", change_frame=-1, change_time_s=0, clock_running=True
            )

    # Establish baseline: average signature over lookback period
    baseline_start = max(0, touch_frame - lookback_frames)
    baseline_end = touch_frame

    left_sigs: list[float] = []
    right_sigs: list[float] = []
    clock_frames_list: list[np.ndarray] = []

    for i in range(baseline_start, min(baseline_end, len(frames))):
        left_sigs.append(region_signature(extract_region(frames[i], regions.left_score)))
        right_sigs.append(region_signature(extract_region(frames[i], regions.right_score)))
        clock_frames_list.append(extract_region(frames[i], regions.clock))

    if not left_sigs:
        return ScoreChange(side="none", change_frame=-1, change_time_s=0, clock_running=True)

    baseline_left = float(np.mean(left_sigs))
    baseline_right = float(np.mean(right_sigs))

    # Check if clock was running before the touch
    clock_running = clock_is_running(clock_frames_list)

    # Look forward for score change
    scan_end = min(touch_frame + lookahead_frames, len(frames))
    left_changed_frame = -1
    right_changed_frame = -1

    for i in range(touch_frame, scan_end):
        left_sig = region_signature(extract_region(frames[i], regions.left_score))
        right_sig = region_signature(extract_region(frames[i], regions.right_score))

        if left_changed_frame < 0 and region_changed(baseline_left, left_sig):
            left_changed_frame = i

        if right_changed_frame < 0 and region_changed(baseline_right, right_sig):
            right_changed_frame = i

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
    )
