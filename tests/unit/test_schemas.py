"""Schema validation tests.

Every Parquet write is validated against its schema. See PRD §11.4.
"""

from __future__ import annotations

import datetime

import polars as pl
import pytest

from a1.data.schemas import validate_clips_schema, validate_exchanges_schema


class TestClipsSchema:
    """Tests for clips.parquet schema validation."""

    def test_valid_clip_passes(self) -> None:
        df = pl.DataFrame(
            {
                "clip_id": ["abc123def456"],
                "source_url": ["https://youtube.com/watch?v=test"],
                "event": ["2024 Paris Olympics"],
                "weapon": ["foil"],
                "date": [datetime.date(2024, 7, 28)],
                "fps": [30.0],
                "width": [1920],
                "height": [1080],
                "has_audio": [True],
                "has_apparatus_visible": [True],
                "broadcast_layout_id": [None],
                "duration_s": [120.5],
                "license_note": [None],
            }
        )
        validate_clips_schema(df)  # should not raise

    def test_invalid_weapon_fails(self) -> None:
        df = pl.DataFrame(
            {
                "clip_id": ["abc123"],
                "source_url": ["https://example.com"],
                "event": ["test"],
                "weapon": ["katana"],  # invalid
                "date": [datetime.date(2024, 1, 1)],
                "fps": [30.0],
                "width": [1920],
                "height": [1080],
                "has_audio": [True],
                "has_apparatus_visible": [True],
                "broadcast_layout_id": [None],
                "duration_s": [60.0],
                "license_note": [None],
            }
        )
        with pytest.raises(ValueError):
            validate_clips_schema(df)

    def test_missing_required_column_fails(self) -> None:
        df = pl.DataFrame(
            {
                "clip_id": ["abc123"],
                # missing source_url and others
            }
        )
        with pytest.raises(ValueError):
            validate_clips_schema(df)


class TestExchangesSchema:
    """Tests for exchanges.parquet schema validation."""

    def test_valid_exchange_passes(self) -> None:
        df = pl.DataFrame(
            {
                "exchange_id": ["ex001"],
                "clip_id": ["clip001"],
                "start_frame": [100],
                "end_frame": [250],
                "weapon": ["foil"],
                "bout_id": [None],
                "athlete_left_id": [None],
                "athlete_right_id": [None],
                "apparatus_light_state": ['[{"frame_idx": 200, "light": "red"}]'],
                "score_before_l": [3],
                "score_before_r": [2],
                "score_after_l": [4],
                "score_after_r": [2],
                "label_t0": ["LEFT"],
                "label_t0_confidence": [1.0],
                "label_path": ["A"],
                "is_contested": [False],
                "was_reviewed": [False],
                "was_reversed": [False],
                "label_final": ["LEFT"],
                "label_tier": [0],
                "confounder_flags": [[]],
                "fold_s_clip": [None],
                "fold_s_bout": [None],
                "fold_s_athlete": [None],
                "fold_s_event": [None],
                "fold_s_both": [None],
                "in_lockbox": [False],
            }
        )
        validate_exchanges_schema(df)  # should not raise

    def test_invalid_label_t0_fails(self) -> None:
        df = pl.DataFrame(
            {
                "exchange_id": ["ex001"],
                "clip_id": ["clip001"],
                "start_frame": [100],
                "end_frame": [250],
                "weapon": ["foil"],
                "bout_id": [None],
                "athlete_left_id": [None],
                "athlete_right_id": [None],
                "apparatus_light_state": ["[]"],
                "score_before_l": [3],
                "score_before_r": [2],
                "score_after_l": [4],
                "score_after_r": [2],
                "label_t0": ["INVALID"],
                "label_t0_confidence": [1.0],
                "label_path": ["A"],
                "is_contested": [False],
                "was_reviewed": [False],
                "was_reversed": [False],
                "label_final": ["LEFT"],
                "label_tier": [0],
                "confounder_flags": [[]],
                "fold_s_clip": [None],
                "fold_s_bout": [None],
                "fold_s_athlete": [None],
                "fold_s_event": [None],
                "fold_s_both": [None],
                "in_lockbox": [False],
            }
        )
        with pytest.raises(ValueError):
            validate_exchanges_schema(df)

    def test_invalid_label_path_fails(self) -> None:
        df = pl.DataFrame(
            {
                "exchange_id": ["ex001"],
                "clip_id": ["clip001"],
                "start_frame": [100],
                "end_frame": [250],
                "weapon": ["foil"],
                "bout_id": [None],
                "athlete_left_id": [None],
                "athlete_right_id": [None],
                "apparatus_light_state": ["[]"],
                "score_before_l": [3],
                "score_before_r": [2],
                "score_after_l": [4],
                "score_after_r": [2],
                "label_t0": ["LEFT"],
                "label_t0_confidence": [1.0],
                "label_path": ["C"],  # invalid — must be A or B
                "is_contested": [False],
                "was_reviewed": [False],
                "was_reversed": [False],
                "label_final": ["LEFT"],
                "label_tier": [0],
                "confounder_flags": [[]],
                "fold_s_clip": [None],
                "fold_s_bout": [None],
                "fold_s_athlete": [None],
                "fold_s_event": [None],
                "fold_s_both": [None],
                "in_lockbox": [False],
            }
        )
        with pytest.raises(ValueError):
            validate_exchanges_schema(df)
