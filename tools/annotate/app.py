"""Entry point for the annotation tool.

Usage: uv run python -m tools.annotate <clip_path> [--annotations <dir>]
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
