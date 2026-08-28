# Fixture Corpus & Annotation Tool (P0 Minimal) — Design Spec

**Date:** 2026-08-27
**Status:** Approved
**Scope:** P0 exit criteria — fixture corpus + minimal annotation tool

---

## 1. Fixture Corpus

### Purpose

10 short clips committed to `tests/fixtures/clips/`, with gold labels, used by
integration tests and as the annotation tool's first input. These are test
fixtures, not training data.

### Clip Selection

| # | Weapon | Scenario | Why |
|---|---|---|---|
| 1 | Foil | Clean double touch, left scores | Happy path |
| 2 | Foil | Clean double touch, right scores | Happy path, other side |
| 3 | Foil | Contested/close call | Tests the hard case |
| 4 | Sabre | Clean double touch, left scores | Cross-weapon |
| 5 | Sabre | Clean double touch, right scores | Cross-weapon |
| 6 | Sabre | Simultaneous — no award | NONE label |
| 7 | Epee | Double touch (both score) | Negative control |
| 8 | Epee | Double touch (both score) | Negative control |
| 9 | Epee | Double touch (both score) | Negative control |
| 10 | Foil | Card penalty or annulment | Confounder handling |

### Files

- `tests/fixtures/manifest.yaml` — YouTube URLs, start/end timestamps, clip
  metadata (weapon, event, expected label)
- `tests/fixtures/clips/` — the trimmed `.mp4` files
- `tests/fixtures/fixtures_gold.parquet` — hand-labeled gold annotations using
  the `annotations.parquet` schema from `src/a1/data/schemas.py`
- `scripts/download_fixtures.py` — downloads and trims clips from the manifest
  via yt-dlp + PyAV
- `make fixtures` Makefile target

### Constraints

- Each clip: 5-10 seconds, <2MB
- Total fixture corpus: <20MB (small enough to commit to git)
- Clips must be from publicly posted competition footage (D4)
- The download script is reproducible — anyone with the manifest can regenerate

---

## 2. Annotation Tool (P0 Minimal)

### Purpose

A PySide6 desktop app that opens a clip, lets you step through frames and label
exchanges, and writes a valid `annotations.parquet`. Meets P0 exit criterion:
"The annotation tool can label a fixture clip end to end and write a valid
`annotations.parquet`."

### Architecture

```
tools/annotate/
├── __init__.py
├── app.py           # Entry point, QApplication setup
├── main_window.py   # Main window layout and coordination
├── video_player.py  # PyAV-based frame extraction + display
├── label_panel.py   # Call, action, confidence controls
└── store.py         # Annotation state, autosave, Parquet I/O
```

### Video Player (`video_player.py`)

- **Backend:** PyAV for frame-accurate seeking (no decord — no arm64 macOS wheels)
- **Frame cache:** Decode and cache nearby frames for smooth stepping
- **Display:** QLabel with the current frame rendered as QPixmap
- **Controls:**
  - Play/pause: Space
  - Frame forward/back: Right/Left arrows
  - 5-frame jump: Shift+Right/Left
  - Speed control: +/- keys
- **Info bar:** Frame number and timestamp displayed below the video

### Label Panel (`label_panel.py`)

- **Call:** LEFT (1) / RIGHT (2) / NONE (3) — keyboard bound
- **Actions left fencer:** Multi-select from `FoilAction` / `SabreAction` enum
  (a phrase has multiple actions)
- **Actions right fencer:** Same
- **Confidence:** high (Q) / med (W) / low (E)
- **Weapon selector:** foil / sabre / epee — set once per clip, persists
- Clear display of which exchange is being annotated

### Store (`store.py`)

- Holds all annotations as a list of dataclass records
- **Autosave:** Writes to a working JSON file on every label change (crash-safe)
- **Export:** Writes `annotations.parquet` via `validated_write()` from
  `src/a1/data/schemas.py`
- **Resume:** On startup, loads existing annotations if present
- **Timing:** Records `annotation_seconds` (time spent per exchange) and
  `annotated_at` timestamp automatically

### Exchange Delineation at P0

The exchange bounding pipeline (S1) doesn't exist yet. At P0, each fixture clip
is pre-trimmed to contain exactly one exchange. The annotator labels one exchange
per clip. The `exchange_id` is derived from the clip filename. When S1 is built
(P1), the tool will be extended to handle multiple exchanges per clip with
manual or auto-detected boundaries.

### Launch

```
uv run python -m tools.annotate.app <clip_path> [--annotations <path>]
```

### Deferred Features (not in P0)

| Feature | Needed at | Why deferred |
|---|---|---|
| Two-panel cropped view (full frame + guard crops) | P4a | Blade annotation is impossible at full zoom, not needed for call labeling |
| Blade keypoint annotation (guard + tip, two-click) | P4a | Blade data phase |
| Linear interpolation overlay | P4a | Blade data phase |
| Event marking (extension onset, contact frames) | P2+ | Needed for T2 labels |
| Justification text field | T3 labels | Gold tier only |
| Blind relabeling mode | R7 | Human ceiling study |
| Tempo break marking | P2+ | Needed for T2 labels |

### P0 Exit Test

Open a fixture clip → label the call + actions + confidence for each exchange →
save → output passes `validate_annotations_schema()`.

---

## 3. Dependencies

### Added to pyproject.toml

- `PySide6` moves from optional `[annotate]` extra to... still optional. The
  annotation tool is launched separately, not imported by `src/a1/`. Install
  with `uv sync --extra annotate`.

### No new src/a1 dependencies

The annotation tool lives in `tools/annotate/` and imports from `src/a1/data/schemas.py`
and `src/a1/rules/taxonomy.py` for enums. It does not add dependencies to the
core package.

---

## 4. Testing

- **Integration test:** `tests/integration/test_annotation_roundtrip.py` — open
  a fixture clip, write a fixture annotation, validate the output Parquet against
  the schema. Runs headless (no GUI) by testing the store directly.
- **Schema test:** Already exists — `tests/unit/test_schemas.py` covers
  `annotations.parquet` validation.
- The annotation tool GUI itself is not unit-tested (PySide6 widget testing is
  high-cost, low-value at this stage). The store and Parquet I/O are.
