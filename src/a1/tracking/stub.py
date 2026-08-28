"""Stub PoseEstimator for P0 — returns empty results.

Replaced by real backends (RTMPose, YOLO-pose, etc.) at S2.
"""

from __future__ import annotations


class StubPoseEstimator:
    """PoseEstimator that returns no detections. For testing and CI only."""

    def detect(
        self, frame: bytes, width: int, height: int
    ) -> list[tuple[float, float, float, float, float]]:
        """Return no detections."""
        return []

    def estimate_pose(
        self,
        frame: bytes,
        width: int,
        height: int,
        detections: list[tuple[float, float, float, float, float]],
    ) -> list[list[tuple[float, float, float]]]:
        """Return no poses."""
        return []
