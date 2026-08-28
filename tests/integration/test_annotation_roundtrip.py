"""Integration test: annotation store writes valid annotations.parquet."""

from __future__ import annotations

import tempfile
from pathlib import Path

import polars as pl
import pytest

from a1.data.schemas import ANNOTATIONS_SCHEMA, validate


def test_annotation_store_roundtrip() -> None:
    """Create an annotation, export to parquet, validate against schema."""
    from tools.annotate.store import AnnotationStore

    store = AnnotationStore(exchange_id="fixture_01", annotator_id="test_user")
    store.set_call("LEFT", "high")
    store.set_actions(left=["lunge", "hit"], right=["parry"])
    store.start_timing()
    store.stop_timing()

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "annotations.parquet"
        store.export_parquet(out)

        df = pl.read_parquet(out)
        validate(df, ANNOTATIONS_SCHEMA, table_name="annotations")

        assert df.shape[0] == 1
        assert df["exchange_id"][0] == "fixture_01"
        assert df["call"][0] == "LEFT"
        assert df["call_confidence"][0] == "high"


def test_annotation_store_autosave_and_resume() -> None:
    """Save to JSON, reload, verify state is preserved."""
    from tools.annotate.store import AnnotationStore

    store = AnnotationStore(exchange_id="fixture_02", annotator_id="test_user")
    store.set_call("RIGHT", "med")
    store.set_actions(left=["counterattack"], right=["lunge", "hit"])

    with tempfile.TemporaryDirectory() as tmp:
        json_path = Path(tmp) / "session.json"
        store.save_json(json_path)

        loaded = AnnotationStore.load_json(json_path)
        df = loaded.to_polars()

        assert df["call"][0] == "RIGHT"
        assert df["call_confidence"][0] == "med"


def test_annotation_store_rejects_invalid_call() -> None:
    """Setting an invalid call value raises ValueError."""
    from tools.annotate.store import AnnotationStore

    store = AnnotationStore(exchange_id="fixture_03", annotator_id="test_user")
    with pytest.raises(ValueError, match="INVALID"):
        store.set_call("INVALID", "high")
