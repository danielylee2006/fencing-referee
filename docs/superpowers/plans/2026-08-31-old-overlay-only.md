# Old Overlay Only — Simplify Pipeline to 2023 FencingVision Overlay

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove 2025 overlay support, add early rejection of new-overlay videos in the acquisition pipeline, widen score regions for double-digit OCR, and validate detection accuracy on 3+ old-overlay videos (50+ exchanges).

**Architecture:** `detect_overlay_era()` becomes a gate — videos detected as "2025" are skipped during acquisition. All dual-era branching code is removed. Score OCR regions are widened to handle scores 0-15. Validation runs the full pipeline on 3 old-overlay videos and checks labels in the annotation tool.

**Tech Stack:** Python 3.11, PyAV, EasyOCR, numpy, PySide6 (annotation tool)

## Global Constraints

- Local Mac (Apple Silicon / MPS) is the compute baseline
- FencingVision 720p @ 25fps is the primary source
- Old overlay (dark blue bar, brightness < 160, B > R) is the only supported overlay
- Score range is 0-15 (fencing bout max)
- All positions are proportional to 720p reference resolution

---

### Task 1: Remove 2025 overlay code and make detection a gate

**Files:**
- Modify: `src/a1/apparatus/score_tracker.py:37-74` (simplify detect function, remove 2025 offsets)
- Modify: `src/a1/apparatus/score_tracker.py:77-120` (remove era parameter from OverlayRegions)
- Modify: `src/a1/apparatus/exchange_filter.py:52-55,73-75` (remove era parameter)
- Modify: `scripts/extract_exchanges.py` (remove era branching, use fixed 2023 positions)
- Modify: `scripts/acquire_corpus.py:220-231,260` (use detect as gate, skip 2025 videos)

**Interfaces:**
- Produces: `detect_overlay_era(frame) -> str` returns `"old"` or `"new"` (renamed for clarity)
- Produces: `is_old_overlay(frame) -> bool` convenience function
- Produces: `OverlayRegions.from_frame_size(h, w)` — no era parameter, always old overlay positions

- [ ] **Step 1: Simplify `score_tracker.py`**

Rename `detect_overlay_era` to `is_old_overlay`, return bool. Remove `_ERA_Y_OFFSETS` dict — hardcode old overlay values directly in `OverlayRegions.from_frame_size`. Remove `era` parameter and field from `OverlayRegions`.

```python
def is_old_overlay(frame: np.ndarray) -> bool:
    """Check if a frame uses the supported old (dark blue) FencingVision overlay.

    The old overlay has a dark blue bar (brightness ~149, B > R).
    The unsupported new overlay has a neutral grey bar (brightness ~176).
    """
    h, w = frame.shape[:2]
    sy = h / 720.0
    sx = w / 1280.0
    y1, y2 = int(625 * sy), int(635 * sy)
    x1, x2 = int(320 * sx), int(960 * sx)
    bar_sample = frame[y1:y2, x1:x2, :]
    r = float(bar_sample[:, :, 0].mean())
    b = float(bar_sample[:, :, 2].mean())
    brightness = (r + float(bar_sample[:, :, 1].mean()) + b) / 3
    return brightness < 160 and b > r
```

Remove `_ERA_Y_OFFSETS`. Update `OverlayRegions.from_frame_size` to use old overlay values directly (bar_top=615, bar_bottom=650, score_y1=617, score_y2=648, strip_y1=654, strip_y2=669). Remove `era` field and parameter.

- [ ] **Step 2: Simplify `exchange_filter.py`**

Remove `era` parameter from `assess_exchange()`. Update `OverlayRegions.from_frame_size(h, w)` call (no era).

- [ ] **Step 3: Simplify `extract_exchanges.py`**

Remove `detect_overlay_era` import (replace with `is_old_overlay`). Remove `era_strip_y` dict, `era_offtarget_y` dict, `overlay_era` variable. Hardcode strip positions: `strip_y1=654, strip_y2=669`. Hardcode off-target square region: `ot_y1=670, ot_y2=700`.

Remove all `if overlay_era == "2023"` branches — the off-target square check and baseline capture now run unconditionally (they only matter for old overlay, which is the only overlay).

Add early exit: after detecting overlay on frame 0, if `not is_old_overlay(img)`, print warning, close container, return empty list.

```python
if i == 0:
    if not is_old_overlay(img):
        print("Skipping: unsupported overlay (not old FencingVision)")
        container.close()
        return []
```

- [ ] **Step 4: Update `acquire_corpus.py`**

Replace `detect_overlay_era` import with `is_old_overlay`. Remove era detection loop after download. `detect_exchanges()` already returns empty for new overlay videos, so the pipeline naturally skips them. Remove `era` parameter from `assess_exchange` call. Remove era from the log message.

- [ ] **Step 5: Update module docstrings**

Update `score_tracker.py` module docstring — remove the two-era documentation, state that only the old (dark blue) overlay is supported. Update `extract_exchanges.py` docstring similarly.

- [ ] **Step 6: Run and verify**

```bash
# Should detect old overlay and find exchanges
uv run python scripts/extract_exchanges.py data/corpus/.tmp/old_overlay_sample.mp4

# Should detect old overlay and find exchanges
uv run python scripts/extract_exchanges.py data/corpus/.tmp/test_2023_foil.mp4

# Should skip (new overlay)
uv run python scripts/extract_exchanges.py data/corpus/.tmp/iT5tv5va1Ws.mp4
```

- [ ] **Step 7: Commit**

```bash
git add src/a1/apparatus/score_tracker.py src/a1/apparatus/exchange_filter.py \
  scripts/extract_exchanges.py scripts/acquire_corpus.py
git commit -m "remove 2025 overlay support, old overlay only"
```

---

### Task 2: Widen score OCR regions for double-digit scores

**Files:**
- Modify: `src/a1/apparatus/score_tracker.py` (OverlayRegions score x-positions)
- Test: Manual OCR verification on clips with double-digit scores

**Interfaces:**
- Modifies: `OverlayRegions.from_frame_size` — left_score and right_score x-ranges widened

- [ ] **Step 1: Measure correct score positions on old overlay**

Run a diagnostic on the 2023 test video with double-digit scores (if available) or the PAUTY video at high-score frames. Save wide crops at multiple score values (single-digit and double-digit) to determine the correct x-range.

```bash
uv run python -c "
import av, cv2
import numpy as np
from src.a1.apparatus.score_tracker import OverlayRegions

# Use old_overlay_sample.mp4 — scores go up to 9-7 by end of bout
container = av.open('data/corpus/.tmp/old_overlay_sample.mp4')
fps = float(container.streams.video[0].average_rate or 25)
# Check several timepoints with increasing scores
for target_t in [30, 200, 400, 500]:
    target_f = int(target_t * fps)
    for i, frame in enumerate(container.decode(video=0)):
        if i == target_f:
            img = frame.to_ndarray(format='rgb24')
            h, w = img.shape[:2]
            sy, sx = h/720, w/1280
            # Save wide crop x=460-600 (left) and x=680-820 (right)
            y1, y2 = int(615*sy), int(650*sy)
            for name, x1, x2 in [('left', 460, 600), ('right', 680, 820)]:
                crop = cv2.cvtColor(img[y1:y2, int(x1*sx):int(x2*sx)], cv2.COLOR_RGB2BGR)
                cv2.imwrite(f'data/corpus/.tmp/score_wide_{name}_t{target_t}.png', crop)
            break
container.close()
"
```

Inspect the crops. Determine the minimum x-range that captures all digits 0-15 for both left and right scores.

- [ ] **Step 2: Update score regions**

Update `OverlayRegions.from_frame_size` with the measured x-ranges. Expected change: widen from `(510, 580)` to approximately `(490, 595)` for left and `(685, 790)` for right (exact values from step 1).

- [ ] **Step 3: Verify OCR on single and double-digit scores**

```bash
uv run python -c "
from src.a1.apparatus.score_tracker import OverlayRegions, read_score
import av

for video, times in [
    ('data/corpus/.tmp/old_overlay_sample.mp4', [30, 200, 400, 500]),
    ('data/corpus/.tmp/test_2023_foil.mp4', [30, 200, 400]),
]:
    container = av.open(video)
    fps = float(container.streams.video[0].average_rate or 25)
    regions = None
    for i, frame in enumerate(container.decode(video=0)):
        t = i / fps
        if regions is None:
            img = frame.to_ndarray(format='rgb24')
            regions = OverlayRegions.from_frame_size(*img.shape[:2])
        for target_t in list(times):
            if abs(t - target_t) < 0.05:
                img = frame.to_ndarray(format='rgb24')
                ls = read_score(img, regions.left_score)
                rs = read_score(img, regions.right_score)
                print(f'{video}: t={t:.0f}s left={ls} right={rs}')
                times.remove(target_t)
        if not times or t > 550:
            break
    container.close()
"
```

Verify all scores read correctly, especially double-digit values (10+).

- [ ] **Step 4: Commit**

```bash
git add src/a1/apparatus/score_tracker.py
git commit -m "widen score OCR regions for double-digit scores (0-15)"
```

---

### Task 3: Validation — full pipeline on 3 old-overlay videos (50+ exchanges)

**Files:**
- No code changes — this is a verification task
- Creates: `data/corpus/verify_old_overlay_validation.yaml` (verification clip list)

**Interfaces:**
- Consumes: `extract_exchanges.detect_exchanges()`, `assess_exchange()`, annotation tool `--verify`

- [ ] **Step 1: Select 3 old-overlay videos**

Use the 2 already downloaded:
1. `data/corpus/.tmp/old_overlay_sample.mp4` (PAUTY vs CHOUPENITCH, ~31 exchanges)
2. `data/corpus/.tmp/test_2023_foil.mp4` (NEMETH vs CHOI, ~32 exchanges)

Download a 3rd from the 2023 Shanghai Foil playlist (different fencers for athlete diversity). Verify it has the old overlay before proceeding.

```bash
# Pick a video, download, verify overlay
uv run yt-dlp -f "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]" \
  --merge-output-format mp4 -o "data/corpus/.tmp/test_2023_foil_v3.mp4" \
  --no-playlist --quiet "<VIDEO_URL>"

uv run python -c "
import av
from src.a1.apparatus.score_tracker import is_old_overlay
container = av.open('data/corpus/.tmp/test_2023_foil_v3.mp4')
for i, f in enumerate(container.decode(video=0)):
    if i == 50:
        print('Old overlay:', is_old_overlay(f.to_ndarray(format='rgb24')))
        break
container.close()
"
```

- [ ] **Step 2: Run full pipeline on all 3 videos**

For each video: run `detect_exchanges()`, then `assess_exchange()` on each non-rejected exchange. Record clip file, label, and light_side. Trim clips. Write a single combined verification YAML.

```bash
uv run python -c "
# [Script that processes all 3 videos, trims clips, writes YAML]
# Same pattern as the mixed test script from this session
# Output: data/corpus/verify_old_overlay_validation.yaml
# Clips dir: data/corpus/clips_validation
"
```

- [ ] **Step 3: Launch annotation tool and verify all clips**

```bash
uv run python -m tools.annotate --verify data/corpus/verify_old_overlay_validation.yaml
```

Step through every clip. Record:
- Label accuracy (LEFT/RIGHT/NONE vs what actually happened)
- Light side accuracy (left/right/both vs what actually fired)
- Any REJECTED clips that should not have been rejected
- Any clips that should have been rejected but weren't

- [ ] **Step 4: Document results**

Record accuracy in PROGRESS.md session log:
- Total exchanges detected across 3 videos
- Rejection rate (clock_paused filter)
- Label accuracy: correct / total non-rejected
- Light side accuracy: correct / total non-rejected
- Any systematic errors found

Target: **95%+ accuracy on both label and light_side** across 50+ exchanges from 3 different bouts with different fencers.

- [ ] **Step 5: Commit verification results**

```bash
git add data/corpus/verify_old_overlay_validation.yaml
git commit -m "validate old overlay pipeline — 3 videos, 50+ exchanges"
```

---

### Task 4: Update source manifest — old overlay playlists only

**Files:**
- Modify: `data/manifests/source_channels.yaml`

**Interfaces:**
- Consumes: FencingVision channel playlist listing
- Produces: Updated manifest with only old-overlay playlists

- [ ] **Step 1: Identify old-overlay playlists**

The 2023 Shanghai Foil playlist is confirmed old overlay. For other playlists (2024, 2025), check a sample video from each:

```bash
# For each playlist, grab first video, download a few seconds, check overlay
uv run yt-dlp --flat-playlist --print "%(id)s" "<PLAYLIST_URL>" | head -1
# Then download and check is_old_overlay on that video
```

Mark playlists as old/new. Some 2024 playlists may have the old overlay — check them individually.

- [ ] **Step 2: Update manifest**

Remove or comment out playlists that use the new overlay. Add a comment explaining why. If 2024 playlists use old overlay, keep them. Add any additional old-overlay playlists from the FencingVision channel (2022, 2021, etc.) to increase corpus size.

- [ ] **Step 3: Add overlay check to acquisition pipeline**

In `acquire_corpus.py`, after `detect_exchanges()` returns empty (which happens for new overlay), log the skip reason clearly:

```python
if not exchanges:
    print(f"    skipped (no exchanges — likely unsupported overlay)")
    video_path.unlink(missing_ok=True)
    return []
```

This is already the behavior, but make the log message explicit about the overlay reason.

- [ ] **Step 4: Commit**

```bash
git add data/manifests/source_channels.yaml scripts/acquire_corpus.py
git commit -m "restrict source manifest to old overlay playlists"
```
