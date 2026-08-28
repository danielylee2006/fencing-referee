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
        stream.codec_context.skip_frame = "NONE"  # decode all frames, not just keyframes
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
