"""Generate fixture gold labels from the manifest.

Creates fixtures_gold.parquet with one annotation per fixture clip,
using the expected_label from the manifest as the call.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import polars as pl
import yaml

from a1.data.schemas import ANNOTATIONS_SCHEMA, validated_write

MANIFEST = Path("tests/fixtures/manifest.yaml")
OUTPUT = Path("tests/fixtures/fixtures_gold.parquet")


def main() -> None:
    with open(MANIFEST) as f:
        manifest = yaml.safe_load(f)

    rows = []
    for clip in manifest["clips"]:
        rows.append(
            {
                "exchange_id": clip["id"],
                "annotator_id": "gold_manifest",
                "tier": 0,
                "call": clip["expected_label"],
                "call_confidence": "high",
                "actions_left": [],
                "actions_right": [],
                "extension_onset_l": None,
                "extension_onset_r": None,
                "tempo_breaks": [],
                "blade_line_l": None,
                "blade_line_r": None,
                "justification_structured": "{}",
                "justification_text": None,
                "ambiguity_note": None,
                "annotation_seconds": 0.0,
                "annotated_at": datetime.now(tz=timezone.utc),
                "is_blind_relabel": False,
            }
        )

    df = pl.DataFrame(
        rows,
        schema_overrides={
            "tier": pl.Int8,
            "extension_onset_l": pl.Int32,
            "extension_onset_r": pl.Int32,
            "tempo_breaks": pl.List(pl.Int32),
            "annotated_at": pl.Datetime("us"),
        },
    )
    validated_write(df, OUTPUT, ANNOTATIONS_SCHEMA, table_name="annotations")
    print(f"Wrote {len(rows)} gold annotations to {OUTPUT}")


if __name__ == "__main__":
    main()
