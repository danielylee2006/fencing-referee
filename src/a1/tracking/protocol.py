"""PoseEstimator protocol — wraps detection/pose backends behind a swappable interface.

RTMDet/RTMPose (MMDetection/MMPose) is the primary backend but is brittle on
Apple Silicon. Alternates (Ultralytics YOLO-pose, Sapiens) must be swappable
by config alone. See PRD §11.2.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


@runtime_checkable
class PoseEstimator(Protocol):
    """Protocol for detection + pose estimation backends."""

    def detect(
        self, frame: bytes, width: int, height: int
    ) -> list[tuple[float, float, float, float, float]]:
        """Detect people in a frame.

        Args:
            frame: Raw frame bytes.
            width: Frame width in pixels.
            height: Frame height in pixels.

        Returns:
            List of (x1, y1, x2, y2, confidence) tuples.
        """
        ...

    def estimate_pose(
        self,
        frame: bytes,
        width: int,
        height: int,
        detections: list[tuple[float, float, float, float, float]],
    ) -> list[list[tuple[float, float, float]]]:
        """Estimate pose for each detection.

        Args:
            frame: Raw frame bytes.
            width: Frame width in pixels.
            height: Frame height in pixels.
            detections: Output of detect().

        Returns:
            List of keypoint lists. Each keypoint is (x, y, confidence).
            Keypoint count is K=17 (COCO-17 format).
        """
        ...
