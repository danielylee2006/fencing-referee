"""Annotation store — state management, autosave, and Parquet export.

Holds annotation records, saves to JSON for crash safety, and exports
valid annotations.parquet via the schema validators in src/a1/data/schemas.py.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from a1.data.schemas import ANNOTATIONS_SCHEMA, validated_write

VALID_CALLS = {"LEFT", "RIGHT", "NONE"}
VALID_CONFIDENCES = {"high", "med", "low"}


@dataclass
class AnnotationRecord:
    """A single exchange annotation."""

    exchange_id: str
    annotator_id: str
    tier: int = 0
    call: str = ""
    call_confidence: str = ""
    actions_left: list[str] = field(default_factory=list)
    actions_right: list[str] = field(default_factory=list)
    extension_onset_l: int | None = None
    extension_onset_r: int | None = None
    tempo_breaks: list[int] = field(default_factory=list)
    blade_line_l: str | None = None
    blade_line_r: str | None = None
    justification_structured: str = "{}"
    justification_text: str | None = None
    ambiguity_note: str | None = None
    annotation_seconds: float = 0.0
    annotated_at: str = ""
    is_blind_relabel: bool = False


class AnnotationStore:
    """Manages annotation state for one exchange."""

    def __init__(self, exchange_id: str, annotator_id: str) -> None:
        self._record = AnnotationRecord(
            exchange_id=exchange_id,
            annotator_id=annotator_id,
        )
        self._timer_start: float | None = None

    def set_call(self, call: str, confidence: str) -> None:
        if call not in VALID_CALLS:
            msg = f"Invalid call: {call!r}. Must be one of {VALID_CALLS}"
            raise ValueError(msg)
        if confidence not in VALID_CONFIDENCES:
            msg = f"Invalid confidence: {confidence!r}. Must be one of {VALID_CONFIDENCES}"
            raise ValueError(msg)
        self._record.call = call
        self._record.call_confidence = confidence

    def set_actions(self, left: list[str], right: list[str]) -> None:
        self._record.actions_left = left
        self._record.actions_right = right

    def set_weapon(self, weapon: str) -> None:
        """Set weapon context (stored in justification_structured for P0)."""
        structured = json.loads(self._record.justification_structured)
        structured["weapon"] = weapon
        self._record.justification_structured = json.dumps(structured)

    def start_timing(self) -> None:
        self._timer_start = time.monotonic()

    def stop_timing(self) -> None:
        if self._timer_start is not None:
            self._record.annotation_seconds += time.monotonic() - self._timer_start
            self._timer_start = None
        self._record.annotated_at = datetime.now(tz=timezone.utc).isoformat()

    def to_polars(self) -> pl.DataFrame:
        r = self._record
        return pl.DataFrame(
            {
                "exchange_id": [r.exchange_id],
                "annotator_id": [r.annotator_id],
                "tier": [r.tier],
                "call": [r.call],
                "call_confidence": [r.call_confidence],
                "actions_left": [r.actions_left],
                "actions_right": [r.actions_right],
                "extension_onset_l": [r.extension_onset_l],
                "extension_onset_r": [r.extension_onset_r],
                "tempo_breaks": [r.tempo_breaks],
                "blade_line_l": [r.blade_line_l],
                "blade_line_r": [r.blade_line_r],
                "justification_structured": [r.justification_structured],
                "justification_text": [r.justification_text],
                "ambiguity_note": [r.ambiguity_note],
                "annotation_seconds": [r.annotation_seconds],
                "annotated_at": [
                    datetime.fromisoformat(r.annotated_at) if r.annotated_at else None
                ],
                "is_blind_relabel": [r.is_blind_relabel],
            },
            schema_overrides={
                "tier": pl.Int8,
                "extension_onset_l": pl.Int32,
                "extension_onset_r": pl.Int32,
                "tempo_breaks": pl.List(pl.Int32),
                "annotated_at": pl.Datetime("us"),
            },
        )

    def save_json(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self._record), indent=2))

    @classmethod
    def load_json(cls, path: Path) -> AnnotationStore:
        data = json.loads(path.read_text())
        store = cls(exchange_id=data["exchange_id"], annotator_id=data["annotator_id"])
        store._record = AnnotationRecord(**data)
        return store

    def export_parquet(self, path: Path) -> None:
        df = self.to_polars()
        validated_write(df, path, ANNOTATIONS_SCHEMA, table_name="annotations")
