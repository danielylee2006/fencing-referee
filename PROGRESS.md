# Project Progress

> Single source of truth for phase ownership and progress.
> Updated by the `/save` command. Read by `/start`.
> Phases are defined in CLAUDE.md section 8 and the PRD.

**Last updated:** 2026-08-31T02:00:00Z

## Engineers

| Name | GitHub | Role | Phases |
|------|--------|------|--------|
| Daniel Lee | danielylee2006 | Lead | All |

## Track Architecture

Two tracks. Track A runs to completion on local Mac. Track B is GPU-gated.

```
Track A (local Mac, no GPU):
P0 → P1 → P2 → P3 ─┬─→ P4a → P7 → P6 → P5 → P8
                     │   (recommended order after P3;
                     │    P4a/P5/P6/P7 are mutually independent)
                     │
Track B (GPU):       └─→ P4b (independent, GPU-gated)
```

## Phase Index

| ID | Phase | Owner | Status | Track | Branch |
|---|---|---|---|---|---|
| P0 | Foundations | danielylee2006 | in progress | A | — |
| P1 | Free supervision | danielylee2006 | not started | A | — |
| P2 | Replication | danielylee2006 | not started | A | — |
| P3 | Protocol result | danielylee2006 | not started | A | — |
| P4a | Blade data | danielylee2006 | not started | A | — |
| P4b | Blade detector training | danielylee2006 | not started | B | — |
| P5 | Audio fusion | danielylee2006 | not started | A | — |
| P6 | Rules and explanations | danielylee2006 | not started | A | — |
| P7 | Cross-weapon transfer | danielylee2006 | not started | A | — |
| P8 | Hard cases, ceiling, release | danielylee2006 | not started | A | — |

---

## P0 — Foundations
- **Owner:** danielylee2006
- **Status:** in progress
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** None
- **Delivers:** Repo, tooling, annotation tool, sponsor email
- **Exit criteria:**
  - [x] CI green on an empty pipeline
  - [x] `make test` passes, including property tests on a stub rule engine
  - [ ] Annotation tool labels a fixture clip end to end → valid `annotations.parquet`
  - [x] `profile/entries/a1-fencing-referee.md` created with every PRD section 15 measure pre-written as empty checkboxes
  - [x] Row added to `reference/entry-placement.json`
  - [ ] Faculty-sponsor email sent (YCRC / NSF ACCESS)
  - [ ] Extraction pipeline validated on fixture clips (score OCR + filters)
  - [ ] Corpus acquisition started (blocked on pipeline validation)
- **Steps:**
  - [x] Set up repo structure per PRD section 11 layout
  - [x] Configure uv, pyproject.toml, lock file
  - [x] Set up pre-commit (ruff + mypy --strict)
  - [x] Create Makefile with all documented targets
  - [x] Set up CI (GitHub Actions)
  - [x] Create Hydra config structure
  - [x] Stub rule engine with property tests
  - [x] Build annotation tool (PySide6)
  - [x] Create fixture clip corpus (10 clips) — clips downloaded, need verification in annotation tool
  - [x] Write apparatus firewall with leakage tests
  - [x] Build exchange auto-extraction pipeline (scripts/extract_exchanges.py)
  - [x] Document FencingVision as primary source (data/manifests/source_channels.yaml)
  - [x] Verify fixture clips in annotation tool and label calls
  - [x] Create profile entry with PRD section 15 measures
  - [x] Add row to entry-placement.json
  - [ ] Draft and send faculty-sponsor email
  - [x] Build score change detection for FencingVision overlay — rewritten to use OCR (EasyOCR)
  - [x] Build pipeline filters: paused clock (blade test rejection via OCR clock reading), no-score-change flagging
  - [x] Build exchange quality assessment module (src/a1/apparatus/exchange_filter.py)
  - [x] Add batch verification mode to annotation tool (--verify flag, N/P navigation)
  - [x] Verify 30 diverse clips from 4 bouts (first verification round)
  - [x] Verify 41 clips from single full-video test (GUO vs SAVIN) — completed, but 2025 overlay has persistent white detection issues
  - [x] Fix white light detection false positives — fixed lookahead (transition-based), added 2023 off-target square detection
  - [x] Verify 31 clips from 2023 overlay video (PAUTY vs CHOUPENITCH) — all correct
  - [x] Verify 32 clips from 2023 overlay video (NEMETH vs CHOI) — all correct
  - [x] Verify 20 mixed clips (10 old overlay + 10 new overlay) — old overlay 10/10, new overlay had label and light_side errors
  - [x] Decision: drop 2025 (new/grey) overlay support, old overlay only
  - [x] Remove 2025 overlay code, simplify pipeline to old overlay only
  - [x] Widen score OCR regions for double-digit scores (0-15)
  - [ ] Validate pipeline on 3 old-overlay videos (50+ exchanges) — plan written, Task 3 pending
  - [ ] Update source manifest to old-overlay playlists only — plan written, Task 4 pending
  - [ ] Start corpus acquisition (blocked on pipeline validation)
- **Resume context** (written by `/save`):
  - **Last worked:** 2026-08-31T02:00:00Z @danielylee2006
  - **Last commit:** 66cc71c P0: add old-overlay-only implementation plan
  - **Files touched this session:** scripts/extract_exchanges.py, scripts/acquire_corpus.py, src/a1/apparatus/score_tracker.py, src/a1/apparatus/exchange_filter.py, docs/superpowers/plans/2026-08-31-old-overlay-only.md, data/corpus/verify_full_video.yaml, data/corpus/verify_2023_overlay.yaml, data/corpus/verify_mixed_test.yaml
  - **Next step:** Execute Tasks 3-4 from `docs/superpowers/plans/2026-08-31-old-overlay-only.md`. Task 3: download a 3rd old-overlay video, run full pipeline on all 3 (50+ exchanges), verify in annotation tool. Task 4: update source manifest to old-overlay playlists only. SDD ledger at `.superpowers/sdd/2026-08-31-old-overlay-only/progress.md` — Tasks 1-2 complete, resume at Task 3.
  - **Open questions / gotchas:**
    - 2025 (grey) overlay is now fully unsupported — `is_old_overlay()` gate rejects at pipeline entry. Decision driven by persistent white/off-target detection false positives on new overlay that consumed 2+ days without resolution.
    - FencingVision switched overlays somewhere in 2024 — not all playlist years are reliable indicators of overlay type. The t5ZK3MAWXwM video is in the "2025 Shanghai" playlist but uses the old overlay. Must check per-video, not per-playlist.
    - Score OCR regions widened (left x=490-595, right x=685-790) for double-digit scores 0-15. Verified on single and double-digit values.
    - 2023 off-target (white square at y=670-700) detection uses both immediate check (absolute threshold 0.02 on touch frame) and lookahead transition (0.03 delta). The square can appear 1 frame before the red/green touch, so prev-frame baseline is needed.
    - Test videos available in data/corpus/.tmp/: old_overlay_sample.mp4 (PAUTY vs CHOUPENITCH), test_2023_foil.mp4 (NEMETH vs CHOI), iT5tv5va1Ws.mp4 (new overlay, for gate testing), test_2025_foil.mp4 (OLIVARES vs CHOUPENITCH — actually old overlay despite "2025" playlist).
    - Pipeline OCR assessment takes ~30-40s per exchange (~15 min per video with 25-40 exchanges). This is the bottleneck for validation.
- **Session log — 2026-08-29/31 (session 5):**
  - BUILT: White light lookahead fix — changed from absolute threshold (>0.10) to transition-based detection (delta from baseline captured at touch onset). Root cause: right strip has permanent bright-neutral pixels (~0.09-0.38) that always exceeded the absolute threshold, falsely upgrading left-only touches to "both".
  - BUILT: Overlay era auto-detection (`detect_overlay_era()`) — samples bar background color at y=625-635. Old overlay (dark blue) has brightness ~149 with B > R; new overlay (grey) has brightness ~176. Threshold at 160.
  - BUILT: Dual-era overlay support (2023 y=654-669, 2025 y=648-663) — later removed in favor of old-overlay-only.
  - BUILT: 2023 off-target square detection at y=670-700. The old overlay shows off-target as a small white square (36×24px at x=782-817) below the bar, unlike the 2025 overlay which uses a white line in the touch strip. Two detection paths: immediate check (absolute >0.02 on touch frame) and lookahead transition (delta >0.03).
  - BUILT: Score OCR regions widened from 70px to 105px (left x=490-595, right x=685-790) to capture double-digit scores 0-15. Previous 70px regions clipped trailing digits of "11", "14", etc.
  - BUILT: Old-overlay-only pipeline simplification — removed all 2025 era code, `is_old_overlay()` gate rejects new overlay videos at pipeline entry.
  - BUG: White detection lookahead used absolute thresholds (right_white > 0.10) but right strip has permanent bright-neutral pixels. Fixed: transition-based detection using baseline captured at touch onset.
  - BUG: 2023 off-target square appeared 1 frame BEFORE the red touch in NEMETH vs CHOI video. Transition-based lookahead missed it because baseline already included the square. Fixed: immediate absolute check (>0.02) on the touch frame itself, plus prev-frame baseline for lookahead.
  - BUG: Score OCR read "10" instead of "11" and "12" instead of "14" at high scores. Root cause: score region x=510-580 (70px) too narrow for double-digit numbers. Fixed: widened to x=490-595 (105px).
  - BUG: extract_exchanges.py import `from src.a1.apparatus...` failed when run as a script (ModuleNotFoundError). Fixed: added `sys.path.insert(0, ...)` matching acquire_corpus.py pattern.
  - BUG: Video t5ZK3MAWXwM from "2025 Shanghai" playlist actually uses the old overlay (brightness 148). Playlist year is not a reliable indicator of overlay era.
  - DECISION: Drop 2025 (grey) overlay support entirely. After 2+ days of white/off-target detection work, the 2025 overlay still had light_side errors on 2/5 tested clips. The 2023 overlay went 10/10 clean on every test. Old overlay has cleaner separation: distinct colored lines, off-target as separate white square. Reduces code complexity and increases reliability.
  - DECISION: Off-target detection uses both absolute threshold (0.02, for same-frame appearance) and transition threshold (0.03, for delayed appearance). The square can appear anywhere from 1 frame before to 6 frames after the red/green touch.
  - DECISION: Score OCR regions need ~105px width to handle scores 0-15 reliably. Measured actual digit positions: left "15" spans x≈535-649, right "10" spans x≈680-746.
  - LEARNED: FencingVision has exactly two overlay designs across its entire channel history. The old overlay (dark blue, pre-2024) has reliable, consistent touch indicators. The new overlay (grey, 2024+) has ambient bright-neutral pixels that confound white detection.
  - LEARNED: The old overlay's off-target indicator (white square) is in a completely different y-region (y=674-695) from the touch indicator strip (y=657-666). It's 36×24 pixels, covering only ~6% of the half-strip width — too small for the 8% transition threshold used for the white line in 2025.
  - LEARNED: Red/green color detection (R-G dominance > 50, transition > 20%) is very robust across both overlay eras. Mean R-G gap is ~180-210 points, well above the 50 threshold. Coverage is ~40-69% of strip pixels when active.
  - LEARNED: The 2023 overlay touch indicators fire at y=657-666 with a weaker leading edge at y=654. The old overlay bar is at y=615-650 (vs 2025 at y=607-647).
  - LEARNED: FencingVision switched overlays sometime during 2024, not cleanly at a year boundary. Some 2025-playlist videos use the old overlay.
  - DEFERRED: Full pipeline validation on 3 old-overlay videos (50+ exchanges) — Task 3 in plan.
  - DEFERRED: Source manifest update to old-overlay playlists only — Task 4 in plan.
  - DEFERRED: Corpus acquisition start — blocked on pipeline validation.
- **Session log — 2026-08-28/29 (session 4):**
  - BUILT: Score tracker rewritten from pixel-counting to OCR (EasyOCR). Reads actual score digits (0-15) with 6x upscaling. Eliminates false positives from overlay glow artifacts that plagued the binarized approach.
  - BUILT: Clock detection rewritten from drift-based to OCR. Reads clock at two points — if same value, clock is stopped (blade test). Drift approach was measuring fencer movement, not clock changes.
  - BUILT: Score scan bounded by next exchange's light onset instead of fixed 20s window. Eliminates score change bleeding into subsequent exchanges (was causing blade tests to inherit the next exchange's score change).
  - BUILT: Annotation tool batch verification mode (--verify flag). Accepts YAML clip list with expected labels, Next/Prev buttons + N/P keyboard shortcuts for stepping through clips. Shows pipeline label and light side in title bar.
  - BUILT: White/off-target light detection added to extract_exchanges.py. Detects bright (>200) color-neutral pixels in touch indicator strip. Still has calibration issues.
  - BUILT: 8-frame lookahead for second light in double touches (FIE 300ms lockout window). Both lights rarely fire on the same frame.
  - BUG: Video 1 (Zeng v Choi) had 95% NONE labels — only 1/22 exchanges got a label. Root cause: `lookahead_frames=100` (4 seconds at 25fps) was too short. This referee took 4-7s to call touches. The pipeline loaded 10s of frames but only scanned the first 4s. Fix: scan all available frames.
  - BUG: Score tracker false positive — overlay glow from touch indicator changed pixel counts in score region, crossing the binarized threshold of 10. Clip 29 (bP_I3a9P28k_025) was labeled LEFT when it should have been RIGHT. Root cause: binarized pixel counting had only a 3-pixel margin between noise (0-9) and real changes (13+). Fix: switched to OCR.
  - BUG: OCR failed on digit "7" with 4x upscaling — EasyOCR couldn't detect it as text. Fix: 6x upscaling reads all digits 0-15 reliably.
  - BUG: `both_scores_changed` false positive (clip 7, Zeng v Choi) — pixel counting detected both scores changing when only right changed (4-0→4-1). Root cause: same binarized threshold sensitivity issue. Fix: OCR reads exact values, no ambiguity.
  - BUG: Score change from exchange 27 (blade test) bled into exchange 28's score change because 20s assessment window exceeded the gap between exchanges. Fix: bound scan by next exchange's light onset.
  - BUG: Clock drift detection was completely unreliable — drift values 2-11 even when clock stopped because the clock region (100px wide) captured fencer movement. Fix: OCR-based clock reading.
  - BUG: Clip 20 (GUO vs SAVIN) labeled NONE when score changed 7-9→8-9. OCR failed to read "7" at baseline. Fix: 6x upscaling resolved this.
  - BUG: Overlay auto-detection (OverlayRegions.detect) returned inconsistent bar heights — clip 014 got h=18 vs normal h=40. Fix: switched to fixed proportional positions (OverlayRegions.from_frame_size) since FencingVision overlay is standardized.
  - DECISION: Session 3's decision "No full OCR needed" reversed. Pixel counting had a 3-pixel margin between noise and real digit changes — too fragile. OCR reads actual values with 99%+ confidence and gives us the score numbers needed for P1's score-delta oracle.
  - DECISION: EasyOCR chosen over PaddleOCR — simpler install, single `easyocr` package. PaddleOCR requires paddlepaddle + paddleocr. Both add torch as a dependency.
  - DECISION: Score scan bounded by next exchange onset, not by clock restart. Clock detection is unreliable for this purpose (fencer movement confounds drift). Next exchange onset is a known hard boundary from the exchange detector.
  - DECISION: Assessment window set to 60s (was 20s). The actual scan terminates at the next exchange's light onset, so 60s is just a generous upper bound for the last exchange in a video.
  - DECISION: White light detection kept despite calibration issues — off-target touches matter for priority in foil. Will tune thresholds based on full verification results.
  - LEARNED: In foil, the electronic scoring apparatus allows 300ms (±25ms) between first and second hit. At 25fps that's 7-8 frames. Both lights almost never fire on the exact same frame.
  - LEARNED: FencingVision touch indicator brightness varies hugely between left (Δ+4 from baseline) and right (Δ+68). This makes brightness-threshold approaches for light detection unreliable. Color transition detection (R-G dominance) is more robust for red/green.
  - LEARNED: Some referees take 30-50+ seconds to make calls (especially after video review). Fixed assessment windows of any length will miss some — next-exchange boundary is the correct approach.
  - LEARNED: Both-lights-with-priority is valid training data (e.g., clip 32: left single touch but right fencer's blade touches floor after action, both lights fire, LEFT gets point). Light_side=both with label=LEFT teaches the model that double lights don't mean ambiguous priority.
  - LEARNED: First verification round (30 clips, 4 bouts): labels 21/30 correct before fixes, all errors were NONE→actual (score change missed). After fixes: 10/10 on re-tested clips. Second round (37 clips, 1 full bout): labels 35/37 correct with OCR. Light_side had 4 errors from white detection calibration.
  - DEFERRED: White light detection calibration — false positives on clips 2, 3, 33; miss on clip 9. Brightness>200 threshold helps but isn't sufficient. May need per-strip baseline or different approach for white.
  - DEFERRED: Full corpus acquisition — blocked on completing pipeline verification.
  - DEFERRED: Faculty sponsor email.
- **Session log — 2026-08-28 (session 3):**
  - BUILT: Completed all 10 fixture clips — re-detected sabre (05-07) and epee (08-10) timestamps, re-trimmed, verified all 10 in annotation tool with Daniel.
  - BUILT: Score change detection (src/a1/apparatus/score_tracker.py) — auto-detects FencingVision overlay bar position via grey band scanning, monitors score digit regions for pixel-diff changes after touch, detects paused clock via cumulative drift.
  - BUILT: Exchange quality filter (src/a1/apparatus/exchange_filter.py) — rejects blade tests (clock paused), labels LEFT/RIGHT from score delta, labels NONE for epee, flags no-score-change and late changes.
  - BUILT: Corpus acquisition pipeline (scripts/acquire_corpus.py) — downloads video, detects touches, assesses quality per exchange on full video frames, trims clips to include score change, deletes full video. Resumable.
  - BUILT: Profile entry (~/Documents/Job/profile/entries/a1-fencing-referee.md) with all 60 PRD section 15 measures. Row added to entry-placement.json.
  - BUG: Fixture 01 (originally exchange #1 at 14.32s) had fencers off-camera during touch — camera pan too slow. Swapped to exchange #2 (77.52s). That exchange showed off-target priority (left attacks off-target, annuls right's valid touch, no point). Label changed from RIGHT to LEFT, clip extended to 11s to capture referee decision.
  - BUG: Fixture 03 (exchange #8 at 189.20s) was a blade test — Bibard stopped the bout to test equipment, clock was paused, light fired but not a real exchange. Swapped to exchange #9 (209.32s).
  - BUG: Fixture 10 (epee, exchange #1 at 44.32s) was a blade test — Hauri tested on himself, clock paused. Exchange #2 (149.08s) also a test. Swapped to exchange #4 (336.96s).
  - BUG: Initial score tracker used hard-coded pixel coordinates (x=510-570 for left score). These hit the decorative bracket, not the score digit. Corrected to x=525-565 by visual inspection of overlay bar crops. Then replaced with proportional auto-detection.
  - BUG: Clock detection initially used per-frame diffs (threshold 3.0) — showed PAUSED for everything because FencingVision clock changes are tiny at 25fps (<0.05 per frame). Fixed by using cumulative drift over 50 frames (running ≈2.5, paused ≈0.5, threshold 1.5).
  - BUG: First corpus acquisition run (with old pipeline) showed 64% "no_score_change" because clips were fixed 8s (light-3s to light+5s) and referee decisions often take 5-10s. Fixed by assessing on full video then trimming to include score change.
  - BUG: Attempted to load all frames of a 10-min bout into memory (~15,000 frames × 1280×720×3 = ~41 GB). Process appeared to complete but produced no output. Fixed by streaming only ~13s of frames per exchange from the full video.
  - DECISION: Fixture 05 label changed from LEFT to RIGHT — Oh fleches, Morrill parries and ripostes, referee awards RIGHT (parry-riposte has priority over fleche). The touch detector said LEFT because the red light fired first, but priority determines the label.
  - DECISION: Off-camera detection NOT implemented as a hard filter — edge density varies too much by weapon/venue/zoom. Will flag for manual review instead. Off-camera is rare per Daniel.
  - DECISION: No full OCR needed — pixel-diff score change detection is sufficient and more reliable than OCR for the FencingVision overlay. Score digits are dark-on-grey; counting dark pixels and detecting changes is enough for labeling.
  - DECISION: Overlay bar y-position auto-detected (scan bottom 15% for grey band >45% coverage), score digit x-positions proportional to frame center (center ± 95px at 1280w). No hard-coded pixel coordinates.
  - DECISION: Added 3 foil playlists (2024 Shanghai, 2024 Torino, 2023 Shanghai) to hit ~60/20/20 foil/sabre/epee ratio. Total: 9 playlists, ~946 videos.
  - DECISION: PRD updated — FencingVision at 25fps is the primary source (overlay reliability outweighs frame rate). ≥50fps ablation deferred unless a reliable high-fps source with standardized overlay is found.
  - DECISION: Pipeline validates extraction quality BEFORE bulk acquisition — a broken pipeline over 946 videos wastes days of compute.
  - DECISION: Clips are variable length (8-15s) instead of fixed 8s, bounded by light-3s to score_change+2s, capped at 15s.
  - LEARNED: Blade tests (equipment checks) fire the touch light with clock paused — a frequent false positive. Three of our original 10 fixture clips were blade tests. Clock-paused detection is a reliable filter.
  - LEARNED: FencingVision overlay bar is always at y≈607-647 in 720p, right edge at ~x=1025. Score digits are at consistent proportional positions relative to frame center across all events and weapons tested.
  - LEARNED: Fencing exchanges where left has priority but hits off-target result in no score change — the score-delta oracle labels these as NONE, but the actual priority call is LEFT. These are valid training examples showing priority without a point.
  - LEARNED: The epee negative control question is deeper than expected — Daniel pointed out the model could learn to output NONE simply by recognizing weapon type from visual cues (different guard shape, no lamé). A true negative control requires the model to not distinguish weapons from its inputs.
  - DEFERRED: Manual verification of 30 diverse corpus clips — pipeline integration was being tested when session ended.
  - DEFERRED: Full corpus acquisition restart — blocked on pipeline validation.
  - DEFERRED: Faculty sponsor email — Daniel said it's drafted but not yet sent.
- **Session log — 2026-08-28 (session 2):**
  - BUILT: Fixed frame-accurate clip trimming — moved ffmpeg `-ss` after `-i` in both download_fixtures.py and extract_exchanges.py. Before: `-ss` before `-i` does keyframe seeking, landing on wrong timestamps. After: `-ss` after `-i` with re-encoding gives exact frame positioning.
  - BUILT: Updated manifest foil timestamps (fixtures 01-04) from current extract_exchanges.py output. Verified all 4 clips visually: each shows fencing action → touch lights → score change.
  - BUG: Fixture clips showed wrong part of the video — no touch, no action, no score change. Root cause: TWO bugs compounding. (1) Manifest timestamps were stale from an earlier buggy detection run (e.g., manifest said light at 25.52s but actual first touch is at 87.44s). (2) ffmpeg `-ss` before `-i` does keyframe seeking, adding further offset error. Fix: re-ran extract_exchanges.py to get correct timestamps, moved `-ss` after `-i`.
  - BUG: Initial hypothesis was that `-ss` position was the sole bug. Testing disproved this — moving `-ss` gave identical frames. The stale timestamps were the primary cause; both bugs needed fixing.
  - DECISION: Selected 4 foil exchanges with LEFT/RIGHT mix: detection #1 (right, 14.32s), #3 (left, 87.44s), #8 (right, 189.20s), #5 (left, 110.80s). Changed fixture_01 and fixture_03 from LEFT to RIGHT to match actual detection.
  - DECISION: Clip window standardized to light-3s → light+5s (8s total) instead of the previous variable windows.
  - LEARNED: Analyzed sholtodouglas/fencing-AI and GalDude33/fencing-AI repos. Both confirm A1's design is stronger on every axis — evaluation rigor, leakage prevention, feature engineering. GalDude33's pose-as-debiasing insight validates A1's firewall philosophy. Neither repo has anything worth adopting directly.
  - LEARNED: GalDude33 achieved ~70% on sabre (vs sholtodouglas's ~60% on foil) using OpenPose keypoints + temporal dilated convolutions, but with random clip-level splits (not athlete-disjoint). Both have no leakage testing.
  - DEFERRED: Sabre/epee clip re-detection and trimming — needs wifi for downloading source videos (~150-200MB each at ~115 KB/s was impractical).
  - DEFERRED: Annotation tool verification and labeling — blocked on correct sabre/epee clips.
- **Session log — 2026-08-27/28:**
  - BUILT: Full P0 scaffold — pyproject.toml, all src/a1 subpackages, Parquet schemas (PRD section 11.4), Hydra config skeleton, Makefile, CI, pre-commit, README with attribution, LICENSE (Apache-2.0), DATA_STATEMENT.md, EVALUATION_PREREGISTRATION.md stub
  - BUILT: Apparatus firewall (src/a1/apparatus/firewall.py) with real validation logic and 10 leakage tests that fail the build
  - BUILT: Stub rule engine with one real rule (established attack → priority, FIE t.56) and non-vacuous swap-equivariance property tests
  - BUILT: PoseEstimator protocol + stub (no MM deps for Apple Silicon compat)
  - BUILT: Annotation tool — PySide6 app with PyAV video player, label panel, annotation store with JSON autosave and Parquet export
  - BUILT: Exchange auto-extraction pipeline (scripts/extract_exchanges.py) — detects touch indicator lines in FencingVision overlay
  - BUILT: Fixture download script with full-video caching and ffmpeg frame-accurate trimming
  - BUILT: FencingVision source channel documentation (data/manifests/source_channels.yaml)
  - BUG: yt-dlp --download-sections corrupts video timestamps via keyframe snapping — every clip trimmed this way started at the wrong point in the video. Fix: download full video (no sections), trim with ffmpeg -ss
  - BUG: First extract_exchanges.py detected red/green SIDE INDICATORS (permanent dots in overlay) as touch lights. These are always present, not touch signals. Fix: detect the colored LINE that appears ABOVE the overlay bar on a touch
  - BUG: Absolute color thresholds for touch detection failed because the FencingVision overlay has permanent green-dominant pixels (~40% of right strip). Fix: detect TRANSITIONS (frame-to-frame delta > 20%) instead of absolute levels
  - BUG: Score-change detection via whole-bar pixel diff didn't work — a digit change (0→1) is too few pixels relative to the whole bar. Simplified: just use touch onset timestamp, clip = touch-3s to touch+5s
  - BUG: PySide6 pixmap.scaled() requires Qt.AspectRatioMode enum members, not integer literals (1). Crashed on launch.
  - BUG: PyAV frame.to_ndarray() requires numpy — was missing from deps. Added to [annotate] extras.
  - BUG: FencingVision video 5t9VT74KqKo (labeled "T16 Choi vs Bibard") actually starts with a different bout (T8 Cristino vs Favaretto). FencingVision videos contain multiple bouts back-to-back on the same piste.
  - DECISION: FencingVision (@FencingVision) is the primary source channel — standardized overlay, uncut bouts, structured video titles for metadata extraction
  - DECISION: Avoid videos with "podium/final/semi" in title — those have slow-motion replays that break detection
  - DECISION: Action labeling (lunge, parry, riposte etc.) deferred to T2 tier — P0 annotation tool only needs call (LEFT/RIGHT/NONE) + confidence
  - DECISION: PRD amendments applied — label_path {A,B} column, five flat fold columns instead of struct, contact_type enum proposed
  - DECISION: Trimmed P0 dependencies hard — no torch, lightning, mlflow, dvc, scipy, matplotlib, opencv in P0. CI runs in <1 min.
  - DECISION: decord dropped — no maintained arm64 macOS wheels. PyAV only.
  - LEARNED: T0 labels (tens of thousands) are fully automatic via score-delta oracle. T2 action labels (~1500) are for explanation/evaluation, not for training the priority predictor. The model works without action labels; explanations don't.
  - LEARNED: The FencingVision overlay touch signal is a colored line (red/green/white) that appears ABOVE the name bar, spanning the fencer's half of the screen. Red = left valid touch, green = right valid touch, white = off-target. Both red+green = double touch.
  - DEFERRED: Profile entry (profile/entries/a1-fencing-referee.md) — needs build-plan.md PRD section 15 template
  - DEFERRED: entry-placement.json — external file
  - DEFERRED: Faculty sponsor email — not a code artifact
  - DEFERRED: Two-panel crop view, blade keypoint annotation, blind relabeling mode — P4a/R7
  - DEFERRED: Score-change detection in overlay — needed for P1's score-delta oracle but not for P0 fixture trimming

## P1 — Free Supervision
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** P0
- **Delivers:** T0 corpus, Path A + Path B labels
- **Exit criteria:**
  - [ ] T0 corpus acquired with manifest
  - [ ] Path A (score-delta oracle) labels generated with measured error rates
  - [ ] Path B (light-state) labels generated
  - [ ] Apparatus firewall validated — no scoreboard leakage
  - [ ] Confounder flags assigned to all exchanges
- **Steps:**
  - [ ] Implement S0 corpus acquisition pipeline (yt-dlp, content-addressed cache)
  - [ ] Implement S1 light state detection
  - [ ] Implement S1 OCR for score extraction
  - [ ] Implement exchange bounding (en-garde reset → score update)
  - [ ] Build score-delta oracle with error-rate gates
  - [ ] Assign confounder flags
  - [ ] Validate apparatus firewall end-to-end
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

## P2 — Replication
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** P1
- **Delivers:** Harness validated against FERA; lockbox generated
- **Exit criteria:**
  - [ ] FERA-MDT baseline replicated within tolerance on S-clip split
  - [ ] Lockbox generated (15% gold, stratified, fixed seed, committed fold definition)
  - [ ] Lockbox guard tested (loader refuses without explicit flag, access logged)
  - [ ] EVALUATION_PREREGISTRATION.md committed
- **Steps:**
  - [ ] Implement FERA-MDT baseline model
  - [ ] Set up split ladder (S-clip, S-bout, S-athlete, S-event, S-both, temporal)
  - [ ] Run FERA-MDT on S-clip, compare to published 0.549 ± 0.018 macro-F1
  - [ ] Generate lockbox with stratification
  - [ ] Implement lockbox guard and access logging
  - [ ] Write EVALUATION_PREREGISTRATION.md
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

## P3 — Protocol Result
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** P2
- **Delivers:** R3 (split ladder), R4 (ablations), épée control
- **Exit criteria:**
  - [ ] All five split protocols reported (S-clip, S-bout, S-athlete, S-event, S-both)
  - [ ] Temporal split reported
  - [ ] Épée control lands at chance (if not, leakage — stop everything)
  - [ ] Ablation matrix (PRD section 10.4) completed
  - [ ] All numbers reported as mean ± std over seeds [0,1,2,3,4]
  - [ ] Statistical protocol: bootstrap CIs, McNemar, Wilcoxon
  - [ ] viz.attention run and reviewed
- **Steps:**
  - [ ] Train PRT model on all split protocols
  - [ ] Run épée negative control
  - [ ] Run ablation matrix
  - [ ] Implement bootstrap CIs, McNemar, Wilcoxon
  - [ ] Generate attention visualizations
  - [ ] Write results to RESULTS.md via `make results`
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

## P4a — Blade Data
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** P3
- **Delivers:** Blade keypoint annotation, synthetic generator
- **Exit criteria:**
  - [ ] Blade keypoint annotation schema defined
  - [ ] Annotation tool extended for blade keypoints
  - [ ] Synthetic blade data generator implemented
  - [ ] Blade training data validated
- **Steps:**
  - [ ] Define blade keypoint schema
  - [ ] Extend annotation tool for blade annotation
  - [ ] Build synthetic blade data generator
  - [ ] Validate generated data quality
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

## P4b — Blade Detector Training
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** B
- **GPU:** Yes
- **Blocked by:** P4a
- **Delivers:** R1 — the headline (blade perception impact)
- **Exit criteria:**
  - [ ] Blade detector trained on annotated + synthetic data
  - [ ] R1 result: blade features improve (or don't improve) priority prediction
  - [ ] Result reported with full statistical protocol
- **Steps:**
  - [ ] Train blade detector on GPU
  - [ ] Extract blade features for all exchanges
  - [ ] Ablation: model with vs. without blade features
  - [ ] Report R1 result
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

## P5 — Audio Fusion
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** P3
- **Delivers:** Audio contact detection
- **Exit criteria:**
  - [ ] Audio onset detection implemented
  - [ ] Audio classifier trained
  - [ ] A/V sync validated
  - [ ] Audio feature fusion into model evaluated
- **Steps:**
  - [ ] Implement S5 audio onset detection
  - [ ] Train audio contact classifier
  - [ ] Validate A/V synchronization
  - [ ] Fuse audio features into PRT model
  - [ ] Ablation: with vs. without audio
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

## P6 — Rules and Explanations
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** P3
- **Delivers:** R6 (rule program), R8 (explanations), explanation corpus
- **Exit criteria:**
  - [ ] Rule taxonomy implemented (S8)
  - [ ] Rule program produces structured traces (S9)
  - [ ] Justification generation implemented
  - [ ] Explanation corpus created and validated
- **Steps:**
  - [ ] Implement rule taxonomy from rulebook
  - [ ] Build rule program with trace output
  - [ ] Implement justification generation
  - [ ] Create explanation corpus
  - [ ] Validate explanations against expert review
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

## P7 — Cross-Weapon Transfer
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** P3
- **Delivers:** R2 — the result nobody has
- **Exit criteria:**
  - [ ] Foil model evaluated on sabre data
  - [ ] Transfer learning approach implemented and evaluated
  - [ ] R2 result reported with statistical protocol
- **Steps:**
  - [ ] Acquire sabre corpus
  - [ ] Label sabre exchanges
  - [ ] Evaluate foil-trained model on sabre (zero-shot)
  - [ ] Fine-tune on sabre data
  - [ ] Report R2 cross-weapon transfer result
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

## P8 — Hard Cases, Ceiling, Release
- **Owner:** danielylee2006
- **Status:** not started
- **Branch:** —
- **Track:** A
- **GPU:** No
- **Blocked by:** P4a, P5, P6, P7
- **Delivers:** R5 (hard-case benchmark), R7 (human ceiling), benchmark release
- **Exit criteria:**
  - [ ] Hard-case benchmark curated
  - [ ] Human ceiling measured and reported as band on accuracy axes
  - [ ] Failure taxonomy compared against human error distribution
  - [ ] Leakage audit (PRD section 10.6) run before lockbox opens
  - [ ] EVALUATION_PREREGISTRATION.md predates first lockbox access
  - [ ] Lockbox evaluated (once, final, pre-registered)
  - [ ] Full public release: benchmark, code, weights, protocol
  - [ ] DATA_STATEMENT.md finalized
- **Steps:**
  - [ ] Curate hard-case benchmark clips
  - [ ] Conduct human ceiling study
  - [ ] Run failure taxonomy analysis
  - [ ] Run final leakage audit
  - [ ] Open lockbox (single pre-registered evaluation)
  - [ ] Package release: code, weights, benchmark, protocol
  - [ ] Write DATA_STATEMENT.md
  - [ ] Generate all README figures via `make figures`
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —
