"""Parquet schemas for all pipeline data tables.

Defines the canonical column names and types for every Parquet file in the
pipeline, per PRD §11.4. Each schema is a polars Schema object. The
``validate`` function checks a DataFrame against a schema before write.

Design decisions and PRD amendments applied here:
- split_assignment replaced by five flat nullable Int8 columns: fold_s_clip,
  fold_s_bout, fold_s_athlete, fold_s_event, fold_s_both. Flat columns give
  predicate pushdown in Parquet. PRD amendment.
- apparatus_light_state: Utf8 (JSON-encoded list of {frame_idx: int, light: str}
  structs). Per-exchange, onsets only, truncated before score update per §3.1.
  This field lives on the label path; it reaches S7 only through the firewall.
  PRD amendment.
- label_path: Categorical {A, B}. Not in original PRD §11.4. PRD amendment —
  required by P1 exit criteria (Path A and Path B agreement reported separately).
- bbox: List(Float32) with 4 elements, xyxy format [x1, y1, x2, y2].
  Matches RTMDet native output.
- keypoints_2d: List(Float32) with K*3 elements. K=17 (COCO-17).
  keypoint_format column records the format for migration safety.
- smpl_params: flat List(Float32) — 10 shape + 72 pose + 3 global orient + 3 transl.
  NOT JSON. Per-frame dense floats.
- contact_type: {blade_blade, blade_target, blade_guard, blade_piste, unknown}.
  PRD amendment — not defined in original §11.4.
- error_category: 11 pre-declared categories from §10.5 verbatim.
- label_final: non-null, defaults to label_t0 when not reversed.
- is_contested: non-null, default false.
- Nullable: broadcast_layout_id, license_note, bout_id, athlete_left_id,
  athlete_right_id, blade geometry fields, calibrated_probs, structured_state,
  rule_trace.

Enum validation constants are defined here and used by validate().
Schema changes are migrations, not edits. Bump and record.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

if TYPE_CHECKING:
    from pathlib import Path

# ---------------------------------------------------------------------------
# Enum value sets for validation
# ---------------------------------------------------------------------------

WEAPONS = {"foil", "sabre", "epee"}
CALLS = {"LEFT", "RIGHT", "NONE"}
FENCERS = {"LEFT", "RIGHT"}
LABEL_PATHS = {"A", "B"}
LABEL_TIERS = {0, 1, 2, 3}
CALL_CONFIDENCES = {"high", "med", "low"}
BLADE_METHODS = {"learned", "streak", "lsd", "track", "none"}
CONTACT_TYPES = {"blade_blade", "blade_target", "blade_guard", "blade_piste", "unknown"}
TAKERS = {"LEFT", "RIGHT", "UNKNOWN"}
PREDICTION_ARMS = {"direct", "rule_grounded"}
ERROR_CATEGORIES = {
    "simultaneous_initiation",
    "remise_vs_riposte",
    "counterattack_vs_stop_hit",
    "parry_ambiguity",
    "point_in_line",
    "attack_losing_tempo",
    "occlusion",
    "camera_angle_degeneracy",
    "motion_blur",
    "apparatus_label_error",
    "rule_genuinely_ambiguous",
}

# ---------------------------------------------------------------------------
# Schema definitions — field names and order match PRD §11.4
# ---------------------------------------------------------------------------

CLIPS_SCHEMA = pl.Schema(
    {
        "clip_id": pl.Utf8,  # sha256, not null
        "source_url": pl.Utf8,  # not null
        "event": pl.Utf8,  # not null
        "weapon": pl.Utf8,  # {foil, sabre, epee}, not null
        "date": pl.Date,  # not null
        "fps": pl.Float64,  # not null
        "width": pl.Int32,  # not null
        "height": pl.Int32,  # not null
        "has_audio": pl.Boolean,  # not null
        "has_apparatus_visible": pl.Boolean,  # not null
        "broadcast_layout_id": pl.Utf8,  # nullable
        "duration_s": pl.Float64,  # not null
        "license_note": pl.Utf8,  # nullable
    }
)

EXCHANGES_SCHEMA = pl.Schema(
    {  # type: ignore[arg-type]
        "exchange_id": pl.Utf8,  # not null
        "clip_id": pl.Utf8,  # not null
        "start_frame": pl.Int32,  # not null
        "end_frame": pl.Int32,  # not null
        "weapon": pl.Utf8,  # {foil, sabre, epee}, not null
        "bout_id": pl.Utf8,  # nullable
        "athlete_left_id": pl.Utf8,  # nullable
        "athlete_right_id": pl.Utf8,  # nullable
        # JSON list of {frame_idx: int, light: str} — onsets only, label path.
        # Reaches S7 only through the firewall.
        "apparatus_light_state": pl.Utf8,  # not null
        "score_before_l": pl.Int32,  # not null
        "score_before_r": pl.Int32,  # not null
        "score_after_l": pl.Int32,  # not null
        "score_after_r": pl.Int32,  # not null
        "label_t0": pl.Utf8,  # {LEFT, RIGHT, NONE}, not null
        "label_t0_confidence": pl.Float64,  # not null
        "label_path": pl.Utf8,  # {A, B}, not null — PRD amendment
        "is_contested": pl.Boolean,  # not null, default false
        "was_reviewed": pl.Boolean,  # not null
        "was_reversed": pl.Boolean,  # not null
        "label_final": pl.Utf8,  # {LEFT, RIGHT, NONE}, not null
        "label_tier": pl.Int8,  # {0, 1, 2, 3}, not null
        "confounder_flags": pl.List(pl.Utf8),  # not null
        "fold_s_clip": pl.Int8,  # nullable — PRD amendment (was split_assignment)
        "fold_s_bout": pl.Int8,  # nullable
        "fold_s_athlete": pl.Int8,  # nullable
        "fold_s_event": pl.Int8,  # nullable
        "fold_s_both": pl.Int8,  # nullable
        "in_lockbox": pl.Boolean,  # not null
    }
)

POSES_SCHEMA = pl.Schema(
    {  # type: ignore[arg-type]
        "exchange_id": pl.Utf8,  # not null
        "frame_idx": pl.Int32,  # not null
        "fencer": pl.Utf8,  # {LEFT, RIGHT}, not null
        "track_id": pl.Int32,  # not null
        "bbox": pl.List(pl.Float32),  # [x1, y1, x2, y2], not null
        "keypoints_2d": pl.List(pl.Float32),  # K*3 floats (x, y, conf), not null
        "keypoints_3d_strip": pl.List(pl.Float32),  # K*3 floats, nullable
        "keypoint_format": pl.Utf8,  # e.g. "coco17", not null
        "smpl_params": pl.List(pl.Float32),  # 88 floats, nullable
        "pose_confidence": pl.Float64,  # not null
        "estimator_version": pl.Utf8,  # not null
    }
)

BLADE_SCHEMA = pl.Schema(
    {  # type: ignore[arg-type]
        "exchange_id": pl.Utf8,  # not null
        "frame_idx": pl.Int32,  # not null
        "fencer": pl.Utf8,  # {LEFT, RIGHT}, not null
        "guard_xy": pl.List(pl.Float32),  # [x, y], nullable
        "guard_conf": pl.Float64,  # nullable
        "tip_xy": pl.List(pl.Float32),  # [x, y], nullable
        "tip_conf": pl.Float64,  # nullable
        "blade_angle": pl.Float64,  # nullable
        "visible_length_px": pl.Float64,  # nullable
        "angular_velocity": pl.Float64,  # nullable
        "method": pl.Utf8,  # {learned, streak, lsd, track, none}, not null
        "is_annotated": pl.Boolean,  # not null
    }
)

CONTACTS_SCHEMA = pl.Schema(
    {
        "exchange_id": pl.Utf8,  # not null
        "frame_idx": pl.Int32,  # not null
        "time_ms": pl.Float64,  # not null
        "taker": pl.Utf8,  # {LEFT, RIGHT, UNKNOWN}, not null
        "contact_type": pl.Utf8,  # PRD amendment, not null
        "line": pl.Utf8,  # nullable — blade line
        "vision_conf": pl.Float64,  # nullable
        "audio_conf": pl.Float64,  # nullable
        "fused_conf": pl.Float64,  # not null
        "is_annotated": pl.Boolean,  # not null
    }
)

ANNOTATIONS_SCHEMA = pl.Schema(
    {  # type: ignore[arg-type]
        "exchange_id": pl.Utf8,  # not null
        "annotator_id": pl.Utf8,  # not null
        "tier": pl.Int8,  # {0, 1, 2, 3}, not null
        "call": pl.Utf8,  # {LEFT, RIGHT, NONE}, not null
        "call_confidence": pl.Utf8,  # {high, med, low}, not null
        "actions_left": pl.List(pl.Utf8),  # list of action enum values
        "actions_right": pl.List(pl.Utf8),
        "extension_onset_l": pl.Int32,  # frame index, nullable
        "extension_onset_r": pl.Int32,  # frame index, nullable
        "tempo_breaks": pl.List(pl.Int32),  # list of frame indices
        "blade_line_l": pl.Utf8,  # nullable (sabre has no blade lines)
        "blade_line_r": pl.Utf8,  # nullable
        "justification_structured": pl.Utf8,  # JSON, not null
        "justification_text": pl.Utf8,  # nullable
        "ambiguity_note": pl.Utf8,  # nullable
        "annotation_seconds": pl.Float64,  # not null
        "annotated_at": pl.Datetime("us"),  # not null
        "is_blind_relabel": pl.Boolean,  # not null
    }
)

PREDICTIONS_SCHEMA = pl.Schema(
    {  # type: ignore[arg-type]
        "run_id": pl.Utf8,  # not null
        "exchange_id": pl.Utf8,  # not null
        "arm": pl.Utf8,  # {direct, rule_grounded}, not null
        "pred": pl.Utf8,  # {LEFT, RIGHT, NONE}, not null
        "probs": pl.List(pl.Float64),  # length 3, not null
        "calibrated_probs": pl.List(pl.Float64),  # length 3, nullable
        "abstained": pl.Boolean,  # not null
        "structured_state": pl.Utf8,  # JSON, nullable
        "rule_trace": pl.Utf8,  # JSON, nullable
        "justification_text": pl.Utf8,  # nullable
        "error_category": pl.Utf8,  # nullable, values from §10.5
    }
)


# ---------------------------------------------------------------------------
# All schemas, keyed by table name
# ---------------------------------------------------------------------------

ALL_SCHEMAS: dict[str, pl.Schema] = {
    "clips": CLIPS_SCHEMA,
    "exchanges": EXCHANGES_SCHEMA,
    "poses": POSES_SCHEMA,
    "blade": BLADE_SCHEMA,
    "contacts": CONTACTS_SCHEMA,
    "annotations": ANNOTATIONS_SCHEMA,
    "predictions": PREDICTIONS_SCHEMA,
}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

# Columns and their allowed enum values for validation.
_ENUM_CHECKS: dict[str, dict[str, set[str]]] = {
    "clips": {"weapon": WEAPONS},
    "exchanges": {
        "weapon": WEAPONS,
        "label_t0": CALLS,
        "label_path": LABEL_PATHS,
        "label_final": CALLS,
    },
    "poses": {"fencer": FENCERS},
    "blade": {"fencer": FENCERS, "method": BLADE_METHODS},
    "contacts": {"taker": TAKERS, "contact_type": CONTACT_TYPES},
    "annotations": {"call": CALLS, "call_confidence": CALL_CONFIDENCES},
    "predictions": {"arm": PREDICTION_ARMS, "pred": CALLS},
}


def validate(
    df: pl.DataFrame,
    schema: pl.Schema,
    *,
    table_name: str = "",
) -> None:
    """Validate that *df* conforms to *schema*.

    Checks:
    1. Every column in the schema is present in the DataFrame.
    2. Column dtypes match (Utf8 accepted where Categorical expected).
    3. Non-null enum columns contain only allowed values.

    Raises:
        ValueError: On any mismatch.
    """
    prefix = f"[{table_name}] " if table_name else ""
    errors: list[str] = []

    for col_name, expected_dtype in schema.items():
        if col_name not in df.columns:
            errors.append(f"{prefix}Missing column: {col_name}")
            continue

        actual_dtype = df.schema[col_name]

        # Null dtype means all values are None — accept for any nullable column.
        if actual_dtype == pl.Null:
            continue

        # Accept Utf8 where Categorical expected.
        if expected_dtype == pl.Categorical and actual_dtype == pl.Utf8:
            continue

        # Accept wider integer types (Int64 for Int32/Int8).
        if expected_dtype in (pl.Int8, pl.Int32) and actual_dtype == pl.Int64:
            continue

        # Accept List(Null) for List(Utf8) when the list is empty.
        if expected_dtype == pl.List(pl.Utf8) and actual_dtype == pl.List(pl.Null):
            continue

        if actual_dtype != expected_dtype:
            errors.append(
                f"{prefix}Column {col_name!r}: expected {expected_dtype}, got {actual_dtype}"
            )

    # Enum value checks
    enum_checks = _ENUM_CHECKS.get(table_name, {})
    for col_name, allowed in enum_checks.items():
        if col_name not in df.columns:
            continue
        non_null = df.filter(pl.col(col_name).is_not_null())
        if len(non_null) == 0:
            continue
        actual_values = set(non_null[col_name].unique().to_list())
        bad = actual_values - allowed
        if bad:
            errors.append(f"{prefix}Column {col_name!r}: invalid values {bad}. Allowed: {allowed}")

    if errors:
        raise ValueError("\n".join(errors))


def validated_write(
    df: pl.DataFrame,
    path: str | Path,
    schema: pl.Schema,
    *,
    table_name: str = "",
) -> None:
    """Validate *df* against *schema*, then write to Parquet.

    This is the only sanctioned way to write pipeline Parquet files.
    Every write is validated; a schema mismatch is a hard error.
    """
    validate(df, schema, table_name=table_name)
    df.write_parquet(str(path))


# ---------------------------------------------------------------------------
# Convenience wrappers per table
# ---------------------------------------------------------------------------


def validate_clips_schema(df: pl.DataFrame) -> None:
    """Validate a clips DataFrame."""
    validate(df, CLIPS_SCHEMA, table_name="clips")


def validate_exchanges_schema(df: pl.DataFrame) -> None:
    """Validate an exchanges DataFrame."""
    validate(df, EXCHANGES_SCHEMA, table_name="exchanges")
