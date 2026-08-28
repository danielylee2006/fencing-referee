"""Apparatus firewall — enforces separation between label path and feature path.

The score delta is the label. It must never reach the model as an input.
See CLAUDE.md §3.1 and PRD §10.6.

The light-state feature passed to S7 is restricted to light onsets and
truncated before any score update. This module validates that invariant.
"""

from __future__ import annotations

from dataclasses import dataclass


class ApparatusLeakError(Exception):
    """Raised when the apparatus firewall detects a label-path leak into the feature path."""


@dataclass(frozen=True)
class ScoreboardRegion:
    """Bounding box of the scoreboard in pixel coordinates (xyxy)."""

    x1: int
    y1: int
    x2: int
    y2: int


def validate_feature_window(
    feature_end_frame: int,
    score_update_frame: int,
) -> None:
    """Assert that the feature window is truncated before the score update.

    The feature path must not extend to or past the frame where the score
    updates, because that frame encodes the label.

    Raises:
        ApparatusLeakError: If feature_end_frame >= score_update_frame.
    """
    if feature_end_frame >= score_update_frame:
        msg = (
            f"Feature window extends to frame {feature_end_frame}, "
            f"but score updates at frame {score_update_frame}. "
            f"The feature path must be truncated before the score update."
        )
        raise ApparatusLeakError(msg)


def validate_no_scoreboard_region(
    feature_region_x1: int,
    feature_region_y1: int,
    feature_region_x2: int,
    feature_region_y2: int,
    scoreboard: ScoreboardRegion,
) -> None:
    """Assert that the feature region does not overlap the scoreboard.

    Any overlap means the model could read the score — the label — from
    the pixels it receives.

    Raises:
        ApparatusLeakError: If the feature region intersects the scoreboard.
    """
    overlaps = (
        feature_region_x1 < scoreboard.x2
        and feature_region_x2 > scoreboard.x1
        and feature_region_y1 < scoreboard.y2
        and feature_region_y2 > scoreboard.y1
    )
    if overlaps:
        msg = (
            f"Feature region [{feature_region_x1}, {feature_region_y1}, "
            f"{feature_region_x2}, {feature_region_y2}] overlaps scoreboard "
            f"[{scoreboard.x1}, {scoreboard.y1}, {scoreboard.x2}, {scoreboard.y2}]. "
            f"The scoreboard encodes the label and must never reach the model."
        )
        raise ApparatusLeakError(msg)
