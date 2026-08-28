# Fixture Corpus & Annotation Tool Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 10-clip fixture corpus and a minimal PySide6 annotation tool so that P0's exit criterion — "the annotation tool can label a fixture clip end to end and write a valid `annotations.parquet`" — is met.

**Architecture:** Two independent pieces. (1) A fixture corpus: a manifest of 10 YouTube clips, a download/trim script, and hand-labeled gold annotations in Parquet. (2) A PySide6 desktop app in `tools/annotate/` with a PyAV video player, a label panel, and a store that autosaves and exports valid `annotations.parquet`. The tool imports enums from `src/a1/rules/taxonomy.py` and writes via `validated_write()` from `src/a1/data/schemas.py`.

**Tech Stack:** Python 3.11, PySide6 (optional extra), PyAV, yt-dlp, polars, existing schema validators.

## Global Constraints

- Python 3.11, uv-managed, locked (`uv.lock` committed)
- `ruff check` + `ruff format --check` + `mypy --strict src/a1` must pass
- PySide6 is an optional extra — `uv sync --extra annotate` to install
- No decord (no arm64 macOS wheels) — PyAV only
- Publicly posted competition footage only (D4)
- Each fixture clip: 5–10 seconds, <2MB; total <20MB
- Each fixture clip contains exactly one exchange
- `exchange_id` derived from clip filename
- Annotation tool lives in `tools/annotate/`, NOT in `src/a1/`
- Annotation tool imports from `src/a1/` but `src/a1/` never imports from `tools/`

---

### Task 1: Annotation Store (data layer)

**Files:**
- Create: `tools/annotate/store.py`
- Test: `tests/integration/test_annotation_roundtrip.py`

**Interfaces:**
- Consumes: `src/a1/data/schemas.py` → `ANNOTATIONS_SCHEMA`, `validated_write()`, `validate()`
- Consumes: `src/a1/rules/taxonomy.py` → `Call`, `CallConfidence`, `FoilAction`, `SabreAction`
- Produces: `AnnotationRecord` dataclass, `AnnotationStore` class with methods:
  - `__init__(self, exchange_id: str, annotator_id: str) -> None`
  - `set_call(self, call: str, confidence: str) -> None`
  - `set_actions(self, left: list[str], right: list[str]) -> None`
  - `set_weapon(self, weapon: str) -> None`
  - `start_timing(self) -> None`
  - `stop_timing(self) -> None`
  - `to_polars(self) -> pl.DataFrame`
  - `save_json(self, path: Path) -> None`
  - `load_json(cls, path: Path) -> AnnotationStore`
  - `export_parquet(self, path: Path) -> None`

- [ ] **Step 1: Write the failing test**

Create `tests/integration/test_annotation_roundtrip.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/integration/test_annotation_roundtrip.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.annotate.store'`

- [ ] **Step 3: Implement the store**

Create `tools/annotate/store.py`:

```python
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
                "annotated_at": [datetime.fromisoformat(r.annotated_at) if r.annotated_at else None],
                "is_blind_relabel": [r.is_blind_relabel],
            },
            schema_overrides={
                "tier": pl.Int8,
                "extension_onset_l": pl.Int32,
                "extension_onset_r": pl.Int32,
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/integration/test_annotation_roundtrip.py -v`
Expected: 3 passed

- [ ] **Step 5: Run full lint suite**

Run: `make lint && make test`
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add tools/annotate/store.py tests/integration/test_annotation_roundtrip.py
git commit -m "P0: add annotation store with autosave and Parquet export"
```

---

### Task 2: Fixture Corpus Manifest and Download Script

**Files:**
- Create: `tests/fixtures/manifest.yaml`
- Create: `scripts/download_fixtures.py`
- Modify: `Makefile` — add `fixtures` target

**Interfaces:**
- Consumes: yt-dlp CLI, PyAV for trimming
- Produces: 10 trimmed `.mp4` files in `tests/fixtures/clips/`

- [ ] **Step 1: Create the fixture manifest**

Create `tests/fixtures/manifest.yaml`. You need to find 10 real YouTube URLs of public FIE/international competition footage and note timestamps for single exchanges. The manifest format:

```yaml
# Fixture corpus manifest — 10 clips for CI and annotation tool testing.
# Each clip is one exchange, pre-trimmed to 5-10 seconds.
# Sources: publicly posted FIE competition footage (D4).

clips:
  - id: fixture_01
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: foil
    event: "PLACEHOLDER EVENT"
    expected_label: LEFT
    scenario: "Clean double touch, left scores"

  - id: fixture_02
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: foil
    event: "PLACEHOLDER EVENT"
    expected_label: RIGHT
    scenario: "Clean double touch, right scores"

  - id: fixture_03
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: foil
    event: "PLACEHOLDER EVENT"
    expected_label: LEFT
    scenario: "Contested/close call"

  - id: fixture_04
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: sabre
    event: "PLACEHOLDER EVENT"
    expected_label: LEFT
    scenario: "Clean double touch, left scores"

  - id: fixture_05
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: sabre
    event: "PLACEHOLDER EVENT"
    expected_label: RIGHT
    scenario: "Clean double touch, right scores"

  - id: fixture_06
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: sabre
    event: "PLACEHOLDER EVENT"
    expected_label: NONE
    scenario: "Simultaneous — no award"

  - id: fixture_07
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: epee
    event: "PLACEHOLDER EVENT"
    expected_label: NONE
    scenario: "Double touch (both score) — negative control"

  - id: fixture_08
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: epee
    event: "PLACEHOLDER EVENT"
    expected_label: NONE
    scenario: "Double touch (both score) — negative control"

  - id: fixture_09
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: epee
    event: "PLACEHOLDER EVENT"
    expected_label: NONE
    scenario: "Double touch (both score) — negative control"

  - id: fixture_10
    url: "https://www.youtube.com/watch?v=PLACEHOLDER"
    start_s: 0.0
    end_s: 7.0
    weapon: foil
    event: "PLACEHOLDER EVENT"
    expected_label: NONE
    scenario: "Card penalty or annulment"
```

**IMPORTANT:** The PLACEHOLDERs must be replaced with real YouTube URLs and timestamps by the implementer. Search for FIE (Fédération Internationale d'Escrime) official YouTube channel and similar public competition footage. Each clip must show one complete exchange with a visible scoreboard.

- [ ] **Step 2: Write the download script**

Create `scripts/download_fixtures.py`:

```python
"""Download and trim fixture clips from the manifest.

Usage: uv run python scripts/download_fixtures.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


MANIFEST = Path("tests/fixtures/manifest.yaml")
OUTPUT_DIR = Path("tests/fixtures/clips")


def download_and_trim(clip: dict[str, object]) -> None:
    clip_id = clip["id"]
    url = str(clip["url"])
    start = float(str(clip["start_s"]))
    end = float(str(clip["end_s"]))
    out_path = OUTPUT_DIR / f"{clip_id}.mp4"

    if out_path.exists():
        print(f"  {clip_id}: already exists, skipping")
        return

    duration = end - start
    print(f"  {clip_id}: downloading {duration:.1f}s from {url}")

    # Download and trim in one pass with yt-dlp's built-in section support
    cmd = [
        "yt-dlp",
        "--download-sections", f"*{start}-{end}",
        "--force-keyframes-at-cuts",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]",
        "--merge-output-format", "mp4",
        "-o", str(out_path),
        "--no-playlist",
        "--quiet",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR downloading {clip_id}: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    # Verify file size
    size_mb = out_path.stat().st_size / (1024 * 1024)
    if size_mb > 2.0:
        print(f"  WARNING: {clip_id} is {size_mb:.1f}MB (target <2MB)")


def main() -> None:
    if not MANIFEST.exists():
        print(f"Manifest not found: {MANIFEST}", file=sys.stderr)
        sys.exit(1)

    with open(MANIFEST) as f:
        manifest = yaml.safe_load(f)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Downloading {len(manifest['clips'])} fixture clips...")
    for clip in manifest["clips"]:
        download_and_trim(clip)

    print("Done.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 3: Add `fixtures` target to Makefile**

Add to the Makefile after the `test-integration` target and before the stubs section:

```makefile
fixtures:
	uv run python scripts/download_fixtures.py
```

- [ ] **Step 4: Add pyyaml to dev dependencies**

The download script uses `yaml.safe_load`. Add `pyyaml` to dev dependencies in `pyproject.toml` (it may already be installed as a transitive dep of hydra, but pin it explicitly):

Check if pyyaml is already a dependency: `uv run python -c "import yaml; print(yaml.__version__)"`
If it works, skip this step. If not, add `"pyyaml>=6,<7"` to `[tool.uv] dev-dependencies` and run `uv sync`.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/manifest.yaml scripts/download_fixtures.py Makefile
git commit -m "P0: add fixture corpus manifest and download script"
```

**NOTE:** The actual downloading (`make fixtures`) and committing of clip files happens after the manifest PLACEHOLDERs are replaced with real URLs. That is a manual step by the project owner (Daniel), not an automated task.

---

### Task 3: Annotation Tool — Video Player Widget

**Files:**
- Create: `tools/annotate/video_player.py`

**Interfaces:**
- Consumes: PyAV, PySide6
- Produces: `VideoPlayer(QWidget)` with methods:
  - `load(self, path: Path) -> None`
  - `frame_count(self) -> int` (property)
  - `current_frame(self) -> int` (property)
  - `fps(self) -> float` (property)
  - `seek(self, frame_idx: int) -> None`
  - `step(self, delta: int) -> None`
  - `play(self) -> None`
  - `pause(self) -> None`
  - `set_speed(self, multiplier: float) -> None`
  - Signal: `frame_changed(int)` — emitted on every frame change

- [ ] **Step 1: Implement the video player widget**

Create `tools/annotate/video_player.py`:

```python
"""Video player widget — PyAV-based frame-accurate playback.

Displays video frames in a QLabel. Supports frame stepping, seeking,
play/pause, and variable speed. No decord (no arm64 macOS wheels).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import av
from PySide6.QtCore import QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

if TYPE_CHECKING:
    import numpy as np
    from numpy.typing import NDArray


class VideoPlayer(QWidget):
    """Frame-accurate video player backed by PyAV."""

    frame_changed = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._container: av.container.InputContainer | None = None
        self._frames: list[bytes] = []  # raw RGB bytes per frame
        self._width = 0
        self._height = 0
        self._fps = 30.0
        self._current = 0
        self._speed = 1.0

        # UI
        self._display = QLabel()
        self._display.setMinimumSize(640, 360)
        self._info = QLabel("No video loaded")

        layout = QVBoxLayout()
        layout.addWidget(self._display)
        layout.addWidget(self._info)
        self.setLayout(layout)

        # Playback timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def load(self, path: Path) -> None:
        """Decode all frames into memory. Only suitable for short clips."""
        container = av.open(str(path))
        stream = container.streams.video[0]
        stream.codec_context.skip_frame = "NONKEY"  # decode all
        stream.thread_type = "AUTO"

        self._fps = float(stream.average_rate or 30)
        self._frames = []

        container.seek(0)
        for frame in container.decode(video=0):
            img = frame.to_ndarray(format="rgb24")
            self._height, self._width = img.shape[:2]
            self._frames.append(img.tobytes())

        container.close()
        self._current = 0
        self._show_frame(0)

    @property
    def frame_count(self) -> int:
        return len(self._frames)

    @property
    def current_frame(self) -> int:
        return self._current

    @property
    def fps(self) -> float:
        return self._fps

    def seek(self, frame_idx: int) -> None:
        frame_idx = max(0, min(frame_idx, len(self._frames) - 1))
        self._current = frame_idx
        self._show_frame(frame_idx)

    def step(self, delta: int) -> None:
        self.seek(self._current + delta)

    def play(self) -> None:
        interval = int(1000 / (self._fps * self._speed))
        self._timer.start(max(1, interval))

    def pause(self) -> None:
        self._timer.stop()

    def toggle_play(self) -> None:
        if self._timer.isActive():
            self.pause()
        else:
            self.play()

    def set_speed(self, multiplier: float) -> None:
        self._speed = max(0.25, min(4.0, multiplier))
        if self._timer.isActive():
            self.play()  # restart timer with new interval

    def _on_tick(self) -> None:
        if self._current < len(self._frames) - 1:
            self.step(1)
        else:
            self.pause()

    def _show_frame(self, idx: int) -> None:
        if not self._frames:
            return
        raw = self._frames[idx]
        qimg = QImage(raw, self._width, self._height, self._width * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(qimg)
        scaled = pixmap.scaled(
            self._display.size(),
            aspectMode=1,  # Qt.KeepAspectRatio
            mode=1,  # Qt.SmoothTransformation
        )
        self._display.setPixmap(scaled)
        time_s = idx / self._fps if self._fps > 0 else 0
        self._info.setText(f"Frame {idx}/{len(self._frames) - 1}  |  {time_s:.2f}s  |  {self._speed:.1f}x")
        self.frame_changed.emit(idx)
```

- [ ] **Step 2: Smoke test manually** (no automated test — PySide6 widgets need a display)

Run: `uv sync --extra annotate` to install PySide6, then:
```bash
uv run python -c "from tools.annotate.video_player import VideoPlayer; print('import OK')"
```
Expected: `import OK`

- [ ] **Step 3: Commit**

```bash
git add tools/annotate/video_player.py
git commit -m "P0: add PyAV video player widget"
```

---

### Task 4: Annotation Tool — Label Panel Widget

**Files:**
- Create: `tools/annotate/label_panel.py`

**Interfaces:**
- Consumes: `src/a1/rules/taxonomy.py` → `FoilAction`, `SabreAction`, `Call`, `CallConfidence`
- Produces: `LabelPanel(QWidget)` with:
  - Signal: `call_changed(str, str)` — (call, confidence)
  - Signal: `actions_changed(list, list)` — (left_actions, right_actions)
  - Signal: `weapon_changed(str)`
  - `get_call(self) -> tuple[str, str]`
  - `get_actions(self) -> tuple[list[str], list[str]]`
  - `get_weapon(self) -> str`
  - `reset(self) -> None`

- [ ] **Step 1: Implement the label panel**

Create `tools/annotate/label_panel.py`:

```python
"""Label panel widget — call, actions, confidence, and weapon controls.

Keyboard shortcuts:
  Call:       1=LEFT, 2=RIGHT, 3=NONE
  Confidence: Q=high, W=med, E=low
  Weapon:     set once via dropdown
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from a1.rules.taxonomy import FoilAction, SabreAction

# Action lists by weapon
_FOIL_ACTIONS = [a.value for a in FoilAction]
_SABRE_ACTIONS = [a.value for a in SabreAction]


class LabelPanel(QWidget):
    """Panel for labeling one exchange: call, confidence, actions, weapon."""

    call_changed = Signal(str, str)
    actions_changed = Signal(list, list)
    weapon_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._weapon = "foil"

        layout = QVBoxLayout()

        # --- Weapon selector ---
        weapon_group = QGroupBox("Weapon")
        weapon_layout = QHBoxLayout()
        self._weapon_combo = QComboBox()
        self._weapon_combo.addItems(["foil", "sabre", "epee"])
        self._weapon_combo.currentTextChanged.connect(self._on_weapon_changed)
        weapon_layout.addWidget(self._weapon_combo)
        weapon_group.setLayout(weapon_layout)
        layout.addWidget(weapon_group)

        # --- Call buttons ---
        call_group = QGroupBox("Call  (1=LEFT  2=RIGHT  3=NONE)")
        call_layout = QHBoxLayout()
        self._call_buttons = QButtonGroup(self)
        for i, label in enumerate(["LEFT", "RIGHT", "NONE"]):
            btn = QRadioButton(label)
            self._call_buttons.addButton(btn, i)
            call_layout.addWidget(btn)
        self._call_buttons.buttonClicked.connect(self._on_call_clicked)
        call_group.setLayout(call_layout)
        layout.addWidget(call_group)

        # --- Confidence buttons ---
        conf_group = QGroupBox("Confidence  (Q=high  W=med  E=low)")
        conf_layout = QHBoxLayout()
        self._conf_buttons = QButtonGroup(self)
        for i, label in enumerate(["high", "med", "low"]):
            btn = QRadioButton(label)
            self._conf_buttons.addButton(btn, i)
            conf_layout.addWidget(btn)
        conf_group.setLayout(conf_layout)
        layout.addWidget(conf_group)

        # --- Actions (left fencer) ---
        left_group = QGroupBox("Actions — Left Fencer")
        left_layout = QVBoxLayout()
        self._left_actions = QListWidget()
        self._left_actions.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._left_actions.addItems(_FOIL_ACTIONS)
        left_layout.addWidget(self._left_actions)
        left_group.setLayout(left_layout)
        layout.addWidget(left_group)

        # --- Actions (right fencer) ---
        right_group = QGroupBox("Actions — Right Fencer")
        right_layout = QVBoxLayout()
        self._right_actions = QListWidget()
        self._right_actions.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self._right_actions.addItems(_FOIL_ACTIONS)
        right_layout.addWidget(self._right_actions)
        right_group.setLayout(right_layout)
        layout.addWidget(right_group)

        # --- Status ---
        self._status = QLabel("No label set")
        layout.addWidget(self._status)

        self.setLayout(layout)

    def get_call(self) -> tuple[str, str]:
        call_btn = self._call_buttons.checkedButton()
        conf_btn = self._conf_buttons.checkedButton()
        call = call_btn.text() if call_btn else ""
        conf = conf_btn.text() if conf_btn else ""
        return call, conf

    def get_actions(self) -> tuple[list[str], list[str]]:
        left = [item.text() for item in self._left_actions.selectedItems()]
        right = [item.text() for item in self._right_actions.selectedItems()]
        return left, right

    def get_weapon(self) -> str:
        return self._weapon

    def reset(self) -> None:
        self._call_buttons.setExclusive(False)
        for btn in self._call_buttons.buttons():
            btn.setChecked(False)
        self._call_buttons.setExclusive(True)
        self._conf_buttons.setExclusive(False)
        for btn in self._conf_buttons.buttons():
            btn.setChecked(False)
        self._conf_buttons.setExclusive(True)
        self._left_actions.clearSelection()
        self._right_actions.clearSelection()
        self._status.setText("No label set")

    def _on_call_clicked(self) -> None:
        call, conf = self.get_call()
        if call and conf:
            self.call_changed.emit(call, conf)
            self._status.setText(f"Call: {call} ({conf})")

    def _on_weapon_changed(self, weapon: str) -> None:
        self._weapon = weapon
        actions = _FOIL_ACTIONS if weapon == "foil" else _SABRE_ACTIONS if weapon == "sabre" else []
        self._left_actions.clear()
        self._right_actions.clear()
        if actions:
            self._left_actions.addItems(actions)
            self._right_actions.addItems(actions)
        self.weapon_changed.emit(weapon)

    def handle_key(self, key: str) -> bool:
        """Handle keyboard shortcuts. Returns True if handled."""
        call_map = {"1": 0, "2": 1, "3": 2}
        conf_map = {"q": 0, "w": 1, "e": 2}

        if key in call_map:
            self._call_buttons.buttons()[call_map[key]].setChecked(True)
            self._on_call_clicked()
            return True
        if key.lower() in conf_map:
            self._conf_buttons.buttons()[conf_map[key.lower()]].setChecked(True)
            self._on_call_clicked()
            return True
        return False
```

- [ ] **Step 2: Smoke test import**

```bash
uv run python -c "from tools.annotate.label_panel import LabelPanel; print('import OK')"
```
Expected: `import OK`

- [ ] **Step 3: Commit**

```bash
git add tools/annotate/label_panel.py
git commit -m "P0: add annotation label panel widget"
```

---

### Task 5: Annotation Tool — Main Window and App Entry Point

**Files:**
- Create: `tools/annotate/main_window.py`
- Create: `tools/annotate/app.py`
- Modify: `tools/annotate/__init__.py` (stays empty)

**Interfaces:**
- Consumes: `VideoPlayer` from task 3, `LabelPanel` from task 4, `AnnotationStore` from task 1
- Produces: A launchable app via `uv run python -m tools.annotate.app <clip_path>`

- [ ] **Step 1: Implement the main window**

Create `tools/annotate/main_window.py`:

```python
"""Main window — coordinates video player, label panel, and annotation store."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tools.annotate.label_panel import LabelPanel
from tools.annotate.store import AnnotationStore
from tools.annotate.video_player import VideoPlayer


class MainWindow(QMainWindow):
    """Annotation tool main window."""

    def __init__(self, clip_path: Path, annotations_path: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle(f"A1 Annotator — {clip_path.name}")
        self.setMinimumSize(1024, 700)

        self._clip_path = clip_path
        exchange_id = clip_path.stem
        annotator_id = os.environ.get("USER", "unknown")

        # Determine save paths
        self._json_path = (annotations_path or clip_path.parent) / f"{exchange_id}_session.json"
        self._parquet_path = (annotations_path or clip_path.parent) / "annotations.parquet"

        # Load or create store
        if self._json_path.exists():
            self._store = AnnotationStore.load_json(self._json_path)
        else:
            self._store = AnnotationStore(exchange_id=exchange_id, annotator_id=annotator_id)

        self._store.start_timing()

        # Widgets
        self._player = VideoPlayer()
        self._labels = LabelPanel()

        # Save button
        save_btn = QPushButton("Export annotations.parquet")
        save_btn.clicked.connect(self._export)

        # Layout: video on left, labels on right
        right = QVBoxLayout()
        right.addWidget(self._labels)
        right.addWidget(save_btn)
        right.addStretch()

        central_layout = QHBoxLayout()
        central_layout.addWidget(self._player, stretch=3)
        right_widget = QWidget()
        right_widget.setLayout(right)
        central_layout.addWidget(right_widget, stretch=1)

        central = QWidget()
        central.setLayout(central_layout)
        self.setCentralWidget(central)

        # Connect signals
        self._labels.call_changed.connect(self._on_label_change)
        self._labels.actions_changed.connect(self._on_actions_change)
        self._labels.weapon_changed.connect(self._on_weapon_change)

        # Load video
        self._player.load(clip_path)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key = event.text()
        modifiers = event.modifiers()

        # Label panel shortcuts
        if self._labels.handle_key(key):
            return

        # Video shortcuts
        if key == " ":
            self._player.toggle_play()
        elif event.key() == Qt.Key.Key_Right:
            delta = 5 if modifiers & Qt.KeyboardModifier.ShiftModifier else 1
            self._player.step(delta)
        elif event.key() == Qt.Key.Key_Left:
            delta = -5 if modifiers & Qt.KeyboardModifier.ShiftModifier else -1
            self._player.step(delta)
        elif key == "+":
            self._player.set_speed(self._player._speed + 0.25)
        elif key == "-":
            self._player.set_speed(self._player._speed - 0.25)
        else:
            super().keyPressEvent(event)

    def _on_label_change(self, call: str, confidence: str) -> None:
        self._store.set_call(call, confidence)
        self._autosave()

    def _on_actions_change(self, left: list[str], right: list[str]) -> None:
        self._store.set_actions(left, right)
        self._autosave()

    def _on_weapon_change(self, weapon: str) -> None:
        self._store.set_weapon(weapon)
        self._autosave()

    def _autosave(self) -> None:
        self._store.save_json(self._json_path)

    def _export(self) -> None:
        call, conf = self._labels.get_call()
        if not call or not conf:
            QMessageBox.warning(self, "Missing label", "Set a call and confidence before exporting.")
            return
        self._store.stop_timing()
        left, right = self._labels.get_actions()
        self._store.set_actions(left, right)
        self._store.export_parquet(self._parquet_path)
        QMessageBox.information(self, "Saved", f"Exported to {self._parquet_path}")
        self._store.start_timing()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._store.stop_timing()
        self._autosave()
        super().closeEvent(event)
```

- [ ] **Step 2: Implement the app entry point**

Create `tools/annotate/app.py`:

```python
"""Entry point for the annotation tool.

Usage: uv run python -m tools.annotate.app <clip_path> [--annotations <dir>]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from tools.annotate.main_window import MainWindow


def main() -> None:
    parser = argparse.ArgumentParser(description="A1 Fencing Annotation Tool")
    parser.add_argument("clip", type=Path, help="Path to the video clip to annotate")
    parser.add_argument(
        "--annotations",
        type=Path,
        default=None,
        help="Directory for annotation output (default: same as clip)",
    )
    args = parser.parse_args()

    if not args.clip.exists():
        print(f"Clip not found: {args.clip}", file=sys.stderr)
        sys.exit(1)

    app = QApplication(sys.argv)
    window = MainWindow(args.clip, args.annotations)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

Also create `tools/annotate/__main__.py` so `python -m tools.annotate` works:

```python
"""Allow running as: python -m tools.annotate <clip_path>"""

from tools.annotate.app import main

main()
```

- [ ] **Step 3: Smoke test the full app launches**

```bash
uv run python -c "from tools.annotate.main_window import MainWindow; print('import OK')"
```
Expected: `import OK`

- [ ] **Step 4: Run full lint and test suite**

```bash
make lint && make test
```
Expected: all pass (mypy runs on `src/a1` only, not `tools/`, so PySide6 types don't need stubs)

- [ ] **Step 5: Commit**

```bash
git add tools/annotate/main_window.py tools/annotate/app.py tools/annotate/__main__.py
git commit -m "P0: add annotation tool main window and app entry point"
```

---

### Task 6: Gold Labels and Integration Verification

**Files:**
- Create: `scripts/create_fixture_gold.py` — generates `fixtures_gold.parquet` from manifest
- Modify: `tests/fixtures/` — add gold labels
- Modify: `.gitignore` — ensure `tests/fixtures/clips/` is NOT ignored

**Interfaces:**
- Consumes: `tests/fixtures/manifest.yaml`, `ANNOTATIONS_SCHEMA`
- Produces: `tests/fixtures/fixtures_gold.parquet`

- [ ] **Step 1: Write the gold label generator script**

Create `scripts/create_fixture_gold.py`:

```python
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
            "annotated_at": pl.Datetime("us"),
        },
    )
    validated_write(df, OUTPUT, ANNOTATIONS_SCHEMA, table_name="annotations")
    print(f"Wrote {len(rows)} gold annotations to {OUTPUT}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Ensure fixture clips are not gitignored**

Check `.gitignore`. The `data/**` rule should NOT catch `tests/fixtures/clips/`. Verify:

```bash
git check-ignore tests/fixtures/clips/test.mp4
```

If it prints the path, add an exclusion. It should return nothing since `tests/` is not under `data/`.

- [ ] **Step 3: Run the gold label generator**

```bash
uv run python scripts/create_fixture_gold.py
```

Expected: `Wrote 10 gold annotations to tests/fixtures/fixtures_gold.parquet`

- [ ] **Step 4: Add a test that loads the gold labels and validates them**

Add to `tests/integration/test_annotation_roundtrip.py`:

```python
def test_fixture_gold_labels_valid() -> None:
    """The committed gold labels pass schema validation."""
    gold_path = Path("tests/fixtures/fixtures_gold.parquet")
    if not gold_path.exists():
        pytest.skip("Gold labels not yet generated — run scripts/create_fixture_gold.py")
    df = pl.read_parquet(gold_path)
    validate(df, ANNOTATIONS_SCHEMA, table_name="annotations")
    assert df.shape[0] == 10
```

Add `from pathlib import Path` to the imports if not already there.

- [ ] **Step 5: Run full test suite**

```bash
make lint && make test
```
Expected: all pass

- [ ] **Step 6: Commit**

```bash
git add scripts/create_fixture_gold.py tests/fixtures/fixtures_gold.parquet tests/integration/test_annotation_roundtrip.py
git commit -m "P0: add fixture gold labels and validation test"
```
