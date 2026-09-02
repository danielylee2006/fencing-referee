"""Secondary pipeline test — download one video, extract 20 diverse clips.

Downloads a single video from the corpus, runs the full pipeline
(detect exchanges → assess quality → label), then selects 20 clips
with diverse label/light_side combinations for manual verification.

Usage:
    uv run python scripts/secondary_test.py
    uv run python scripts/secondary_test.py --video-url "https://www.youtube.com/watch?v=VIDEO_ID"
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import av
import numpy as np
import yaml

# Import pipeline components
sys.path.insert(0, str(Path(__file__).parent))
from extract_exchanges import Exchange, detect_exchanges

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from a1.apparatus.exchange_filter import assess_exchange

# Reuse acquire_corpus helpers
import acquire_corpus
from acquire_corpus import _load_frame_range, download_video, trim_clip

TEMP_DIR = Path("data/corpus/.tmp")
OUT_DIR = Path("data/corpus/secondary_test")
TARGET_CLIPS = 20


def categorize(label: str, light_side: str, flags: list[str]) -> str:
    """Return a category string for diversity selection."""
    if "no_score_change" in flags:
        return f"NONE-{light_side}"
    if label == "NONE":
        return f"NONE-{light_side}"
    if "both_scores_changed" in flags:
        return f"{label}-both_changed"
    return f"{label}-{light_side}"


def select_diverse(assessed: list[dict], target: int) -> list[dict]:
    """Select target clips with maximum diversity across categories.

    Round-robin across categories so rare types (off_target, both,
    NONE) aren't crowded out by common ones (LEFT-left, RIGHT-right).
    """
    by_cat: dict[str, list[dict]] = {}
    for a in assessed:
        cat = a["category"]
        by_cat.setdefault(cat, []).append(a)

    selected: list[dict] = []
    seen_indices: set[int] = set()

    # Round-robin: take one from each category in turn
    while len(selected) < target:
        added_any = False
        for cat in sorted(by_cat.keys()):
            if len(selected) >= target:
                break
            candidates = by_cat[cat]
            for c in candidates:
                if c["index"] not in seen_indices:
                    selected.append(c)
                    seen_indices.add(c["index"])
                    added_any = True
                    break
        if not added_any:
            break  # exhausted all categories

    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description="Secondary pipeline test")
    parser.add_argument(
        "--video-url",
        default="https://www.youtube.com/watch?v=1_pm8haO-qs",
        help="YouTube URL to test (default: NAGANO vs LEE, 2024 Torino Foil T64)",
    )
    parser.add_argument(
        "--target",
        type=int,
        default=TARGET_CLIPS,
        help=f"Number of clips to extract (default: {TARGET_CLIPS})",
    )
    parser.add_argument(
        "--cookies",
        type=str,
        default=None,
        help="Browser to read cookies from (e.g. chrome, firefox)",
    )
    parser.add_argument(
        "--weapon",
        type=str,
        default="foil",
        help="Weapon type for assessment (foil, sabre, epee)",
    )
    args = parser.parse_args()

    # Wire cookie support through to acquire_corpus
    acquire_corpus._cookie_browser = args.cookies

    video_id = args.video_url.split("v=")[-1].split("&")[0]
    print(f"=== Secondary Pipeline Test ===")
    print(f"Video: {args.video_url}")
    print(f"Target clips: {args.target}\n")

    # Step 1: Download
    print("Step 1: Downloading video...")
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    video_path = download_video(video_id, args.video_url)
    if not video_path:
        print("ERROR: Download failed", file=sys.stderr)
        sys.exit(1)

    # Step 2: Detect exchanges
    print("\nStep 2: Detecting exchanges...")
    exchanges = detect_exchanges(str(video_path), weapon=args.weapon)
    if not exchanges:
        print("ERROR: No exchanges detected", file=sys.stderr)
        video_path.unlink(missing_ok=True)
        sys.exit(1)
    print(f"  {len(exchanges)} exchanges detected")

    # Step 3: Assess all exchanges
    print("\nStep 3: Assessing all exchanges...")
    container = av.open(str(video_path))
    fps = float(container.streams.video[0].average_rate or 25)
    container.close()

    assessed: list[dict] = []
    rejected = 0

    for j, ex in enumerate(exchanges):
        assess_start_s = max(0, ex.light_onset_s - 3.0)
        if j + 1 < len(exchanges):
            assess_end_s = exchanges[j + 1].light_onset_s
        else:
            assess_end_s = ex.light_onset_s + 60.0

        frames = _load_frame_range(str(video_path), assess_start_s, assess_end_s)
        if not frames:
            continue

        touch_frame_local = int(3.0 * fps)
        lookahead = len(frames) - touch_frame_local
        quality = assess_exchange(frames, touch_frame_local, fps, args.weapon,
                                  lookahead_frames=lookahead)
        del frames

        if quality.reject:
            rejected += 1
            print(f"  [{j+1:2d}] REJECTED ({quality.reject_reason})")
            continue

        # Compute clip boundaries
        clip_start_s = assess_start_s
        if quality.score_change and quality.score_change.change_frame >= 0:
            score_change_s = assess_start_s + quality.score_change.change_frame / fps
            clip_end_s = score_change_s + 2.0
        else:
            clip_end_s = ex.light_onset_s + 5.0
        if clip_end_s - clip_start_s > 15.0:
            clip_end_s = clip_start_s + 15.0

        entry = {
            "index": j,
            "exchange_num": j + 1,
            "light_onset_s": round(ex.light_onset_s, 2),
            "clip_start_s": round(clip_start_s, 2),
            "clip_end_s": round(clip_end_s, 2),
            "light_side": ex.side,
            "light_detail": ex.light_detail,
            "label": quality.label,
            "flags": quality.flags if quality.flags else [],
            "score_before": f"{quality.score_change.left_before}-{quality.score_change.right_before}"
            if quality.score_change else "?-?",
            "score_after": f"{quality.score_change.left_after}-{quality.score_change.right_after}"
            if quality.score_change else "?-?",
        }
        entry["category"] = categorize(entry["label"], entry["light_side"], entry["flags"])
        assessed.append(entry)
        print(f"  [{j+1:2d}] {entry['label']:>5s}  light={entry['light_side']:<10s}  "
              f"detail={entry['light_detail']:<12s}  "
              f"score={entry['score_before']}→{entry['score_after']}  "
              f"flags={entry['flags']}  cat={entry['category']}")

    print(f"\n  Total: {len(assessed)} accepted, {rejected} rejected")

    # Step 4: Select diverse clips
    print(f"\nStep 4: Selecting {args.target} diverse clips...")
    cat_counts = Counter(a["category"] for a in assessed)
    print(f"  Categories available: {dict(cat_counts)}")

    selected = select_diverse(assessed, args.target)
    sel_cats = Counter(s["category"] for s in selected)
    print(f"  Selected categories:  {dict(sel_cats)}")

    # Step 5: Trim selected clips
    print(f"\nStep 5: Trimming {len(selected)} clips...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    for s in selected:
        clip_name = f"{video_id}_{s['exchange_num']:03d}.mp4"
        clip_path = OUT_DIR / clip_name
        duration = s["clip_end_s"] - s["clip_start_s"]
        if not clip_path.exists():
            trim_clip(video_path, s["clip_start_s"], duration, clip_path)
        size_mb = clip_path.stat().st_size / (1024 * 1024) if clip_path.exists() else 0
        s["clip_file"] = clip_name
        s["size_mb"] = round(size_mb, 1)

    # Step 6: Write verification YAML
    verify_path = OUT_DIR / "verify_secondary_test.yaml"
    verify_clips = []
    for s in sorted(selected, key=lambda x: x["exchange_num"]):
        entry = {
            "clip": s["clip_file"],
            "label": s["label"],
            "light_side": s["light_side"],
            "light_detail": s["light_detail"],
        }
        if s["flags"]:
            entry["flags"] = s["flags"]
        verify_clips.append(entry)

    verify_data = {
        "clips_dir": str(OUT_DIR),
        "clips": verify_clips,
    }
    with open(verify_path, "w") as f:
        yaml.dump(verify_data, f, default_flow_style=False, sort_keys=False)

    # Summary
    print(f"\n{'=' * 60}")
    print(f"Secondary test complete!")
    print(f"  Video:     {video_id}")
    print(f"  Detected:  {len(exchanges)} exchanges")
    print(f"  Rejected:  {rejected} (blade tests / clock paused)")
    print(f"  Assessed:  {len(assessed)}")
    print(f"  Selected:  {len(selected)} diverse clips")
    print(f"  Output:    {OUT_DIR}/")
    print(f"  Verify:    {verify_path}")
    print(f"\nTo verify in annotation tool:")
    print(f"  uv run python tools/annotate/app.py --verify {verify_path}")

    # Print the selected clips table
    print(f"\n{'#':>3}  {'Label':>5}  {'Light':>10}  {'Detail':<12}  {'Score':>11}  {'Category':<20}  Flags")
    print("-" * 90)
    for s in sorted(selected, key=lambda x: x["exchange_num"]):
        print(f"{s['exchange_num']:3d}  {s['label']:>5s}  {s['light_side']:>10s}  "
              f"{s['light_detail']:<12s}  "
              f"{s['score_before']}→{s['score_after']:>5s}  {s['category']:<20s}  {s['flags']}")

    # Don't delete the video yet — user may want to re-run with different params
    print(f"\nVideo kept at: {video_path}")
    print(f"Delete manually when done: rm {video_path}")


if __name__ == "__main__":
    main()
