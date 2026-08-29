"""Main window — coordinates video player, label panel, and annotation store."""

from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
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

    def __init__(
        self,
        clip_path: Path,
        annotations_path: Path | None = None,
        clip_list: list[tuple[Path, str, str]] | None = None,
    ) -> None:
        super().__init__()
        self.setMinimumSize(1024, 700)

        # Batch verification state
        self._clip_list = clip_list  # [(path, expected_label, light_side), ...]
        self._clip_idx = 0
        self._verify_results: list[dict[str, str]] = []  # track pass/fail per clip

        self._annotations_path = annotations_path
        self._setup_clip(clip_path)

        # Widgets
        self._player = VideoPlayer()
        self._labels = LabelPanel()

        # Save button
        save_btn = QPushButton("Export annotations.parquet")
        save_btn.clicked.connect(self._export)

        # Layout: video on left, labels on right
        right = QVBoxLayout()

        # Navigation bar (only in batch mode)
        if self._clip_list:
            nav_layout = QHBoxLayout()
            self._prev_btn = QPushButton("◀ Prev (P)")
            self._next_btn = QPushButton("Next (N) ▶")
            self._nav_label = QLabel()
            self._expected_label = QLabel()
            self._expected_label.setStyleSheet("font-size: 14px; font-weight: bold; padding: 4px;")
            self._prev_btn.clicked.connect(self._prev_clip)
            self._next_btn.clicked.connect(self._next_clip)
            nav_layout.addWidget(self._prev_btn)
            nav_layout.addWidget(self._nav_label)
            nav_layout.addWidget(self._next_btn)
            right.addLayout(nav_layout)
            right.addWidget(self._expected_label)
            self._update_nav()

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

    def _setup_clip(self, clip_path: Path) -> None:
        """Set up state for a single clip."""
        self._clip_path = clip_path
        exchange_id = clip_path.stem
        annotator_id = os.environ.get("USER", "unknown")

        ann_dir = self._annotations_path or clip_path.parent
        self._json_path = ann_dir / f"{exchange_id}_session.json"
        self._parquet_path = ann_dir / "annotations.parquet"

        if self._json_path.exists():
            self._store = AnnotationStore.load_json(self._json_path)
        else:
            self._store = AnnotationStore(exchange_id=exchange_id, annotator_id=annotator_id)
        self._store.start_timing()

        # Update title
        if self._clip_list:
            _, expected, light = self._clip_list[self._clip_idx]
            self.setWindowTitle(
                f"A1 Verify — {clip_path.name}  |  "
                f"Pipeline: {expected}  |  Light: {light}  |  "
                f"[{self._clip_idx + 1}/{len(self._clip_list)}]"
            )
        else:
            self.setWindowTitle(f"A1 Annotator — {clip_path.name}")

    def _update_nav(self) -> None:
        """Update navigation labels and button states."""
        if not self._clip_list:
            return
        total = len(self._clip_list)
        self._nav_label.setText(f"Clip {self._clip_idx + 1} / {total}")
        self._prev_btn.setEnabled(self._clip_idx > 0)
        self._next_btn.setEnabled(self._clip_idx < total - 1)
        _, expected, light = self._clip_list[self._clip_idx]
        self._expected_label.setText(
            f"Pipeline label: {expected}  |  Light side: {light}"
        )

    def _load_clip_at_index(self, idx: int) -> None:
        """Load a clip by index in the batch list."""
        if not self._clip_list or idx < 0 or idx >= len(self._clip_list):
            return
        self._store.stop_timing()
        self._store.save_json(self._json_path)
        self._clip_idx = idx
        clip_path, _, _ = self._clip_list[idx]
        self._setup_clip(clip_path)
        self._player.load(clip_path)
        self._labels.reset()
        self._update_nav()

    def _prev_clip(self) -> None:
        self._load_clip_at_index(self._clip_idx - 1)

    def _next_clip(self) -> None:
        self._load_clip_at_index(self._clip_idx + 1)

    def keyPressEvent(self, event) -> None:  # type: ignore[override]
        key = event.text()
        modifiers = event.modifiers()

        # Batch navigation shortcuts (N/P)
        if self._clip_list and key.lower() == "n":
            self._next_clip()
            return
        if self._clip_list and key.lower() == "p":
            self._prev_clip()
            return

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
