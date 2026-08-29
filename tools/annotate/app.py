"""Entry point for the annotation tool.

Usage:
    uv run python -m tools.annotate <clip_path> [--annotations <dir>]
    uv run python -m tools.annotate --verify <clip_list.yaml>
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from tools.annotate.main_window import MainWindow


def main() -> None:
    parser = argparse.ArgumentParser(description="A1 Fencing Annotation Tool")
    parser.add_argument("clip", nargs="?", type=Path, help="Path to the video clip to annotate")
    parser.add_argument(
        "--annotations",
        type=Path,
        default=None,
        help="Directory for annotation output (default: same as clip)",
    )
    parser.add_argument(
        "--verify",
        type=Path,
        default=None,
        help="YAML file with clip list and expected labels for batch verification",
    )
    args = parser.parse_args()

    if args.verify:
        import yaml

        if not args.verify.exists():
            print(f"Verify list not found: {args.verify}", file=sys.stderr)
            sys.exit(1)
        with open(args.verify) as f:
            verify_data = yaml.safe_load(f)
        clips_dir = Path(verify_data["clips_dir"])
        clip_list = [
            (clips_dir / entry["clip"], entry.get("label", ""), entry.get("light_side", ""))
            for entry in verify_data["clips"]
        ]
        missing = [str(p) for p, _, _ in clip_list if not p.exists()]
        if missing:
            print(f"Missing clips: {missing[:5]}...", file=sys.stderr)
            sys.exit(1)

        app = QApplication(sys.argv)
        window = MainWindow(
            clip_list[0][0],
            args.annotations,
            clip_list=clip_list,
        )
        window.show()
        sys.exit(app.exec())
    else:
        if args.clip is None:
            parser.error("clip is required unless --verify is used")
        if not args.clip.exists():
            print(f"Clip not found: {args.clip}", file=sys.stderr)
            sys.exit(1)

        app = QApplication(sys.argv)
        window = MainWindow(args.clip, args.annotations)
        window.show()
        sys.exit(app.exec())


if __name__ == "__main__":
    main()
