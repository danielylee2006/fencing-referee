"""Leakage tests for the apparatus firewall.

These tests FAIL THE BUILD if the firewall does not catch label-path leaks.
See CLAUDE.md §3.1 and PRD §10.6.

Never skip, xfail, or loosen these tests.
"""

from __future__ import annotations

import pytest

from a1.apparatus.firewall import (
    ApparatusLeakError,
    ScoreboardRegion,
    validate_feature_window,
    validate_no_scoreboard_region,
)

SCOREBOARD = ScoreboardRegion(x1=100, y1=0, x2=540, y2=60)


class TestFeatureWindowTruncation:
    """The feature window must end before the score-update frame."""

    def test_feature_at_score_update_frame_raises(self) -> None:
        """Feature window ending AT the score-update frame is a leak."""
        with pytest.raises(ApparatusLeakError):
            validate_feature_window(
                feature_end_frame=150,
                score_update_frame=150,
            )

    def test_feature_past_score_update_frame_raises(self) -> None:
        """Feature window ending AFTER the score-update frame is a leak."""
        with pytest.raises(ApparatusLeakError):
            validate_feature_window(
                feature_end_frame=200,
                score_update_frame=150,
            )

    def test_feature_before_score_update_passes(self) -> None:
        """Feature window ending before the score-update frame is clean."""
        validate_feature_window(
            feature_end_frame=149,
            score_update_frame=150,
        )

    def test_feature_well_before_score_update_passes(self) -> None:
        """Feature window ending well before score update is clean."""
        validate_feature_window(
            feature_end_frame=50,
            score_update_frame=150,
        )


class TestScoreboardRegionExclusion:
    """Features must not overlap the scoreboard region."""

    def test_full_overlap_raises(self) -> None:
        """Feature region fully inside scoreboard raises."""
        with pytest.raises(ApparatusLeakError):
            validate_no_scoreboard_region(
                feature_region_x1=200,
                feature_region_y1=10,
                feature_region_x2=400,
                feature_region_y2=50,
                scoreboard=SCOREBOARD,
            )

    def test_partial_overlap_raises(self) -> None:
        """Feature region partially overlapping scoreboard raises."""
        with pytest.raises(ApparatusLeakError):
            validate_no_scoreboard_region(
                feature_region_x1=50,
                feature_region_y1=30,
                feature_region_x2=200,
                feature_region_y2=100,
                scoreboard=SCOREBOARD,
            )

    def test_feature_below_scoreboard_passes(self) -> None:
        """Feature region entirely below the scoreboard passes."""
        validate_no_scoreboard_region(
            feature_region_x1=100,
            feature_region_y1=61,
            feature_region_x2=540,
            feature_region_y2=400,
            scoreboard=SCOREBOARD,
        )

    def test_feature_left_of_scoreboard_passes(self) -> None:
        """Feature region entirely left of the scoreboard passes."""
        validate_no_scoreboard_region(
            feature_region_x1=0,
            feature_region_y1=0,
            feature_region_x2=99,
            feature_region_y2=60,
            scoreboard=SCOREBOARD,
        )

    def test_feature_right_of_scoreboard_passes(self) -> None:
        """Feature region entirely right of the scoreboard passes."""
        validate_no_scoreboard_region(
            feature_region_x1=541,
            feature_region_y1=0,
            feature_region_x2=700,
            feature_region_y2=60,
            scoreboard=SCOREBOARD,
        )

    def test_adjacent_but_not_overlapping_passes(self) -> None:
        """Feature region touching but not overlapping the scoreboard passes."""
        # Touching at the right edge — x2 == scoreboard.x1, no overlap
        validate_no_scoreboard_region(
            feature_region_x1=0,
            feature_region_y1=0,
            feature_region_x2=100,
            feature_region_y2=60,
            scoreboard=SCOREBOARD,
        )
