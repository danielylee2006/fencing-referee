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
