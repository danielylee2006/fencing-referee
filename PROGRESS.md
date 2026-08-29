# Project Progress

> Single source of truth for phase ownership and progress.
> Updated by the `/save` command. Read by `/start`.
> Phases are defined in CLAUDE.md section 8 and the PRD.

**Last updated:** 2026-08-28T03:45:00Z

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
  - [ ] Build score OCR for FencingVision overlay (validate on fixture clips)
  - [ ] Build pipeline filters: paused clock, off-camera, no-score-change
  - [ ] Integrate OCR + filters into acquire_corpus.py
  - [ ] Start corpus acquisition (blocked on pipeline validation)
- **Resume context** (written by `/save`):
  - **Last worked:** 2026-08-28T03:45:00Z @danielylee2006
  - **Last commit:** 44975c0 P0: fix fixture clip trimming — frame-accurate seeking and correct timestamps
  - **Files touched this session:** scripts/download_fixtures.py, scripts/extract_exchanges.py, tests/fixtures/manifest.yaml, tests/fixtures/clips/fixture_01.mp4, tests/fixtures/clips/fixture_02.mp4, tests/fixtures/clips/fixture_03.mp4, tests/fixtures/clips/fixture_04.mp4
  - **Next step:** Download sabre/epee source videos on better wifi, run extract_exchanges.py on each to get correct timestamps, update manifest for fixtures 05-10, re-trim those clips. Then verify all 10 in the annotation tool and label calls.
  - **Open questions / gotchas:**
    - Foil clips (01-04) are VERIFIED — correct timestamps, frame-accurate trimming, all show real touches with score changes.
    - Sabre clips (05-07) and epee clips (08-10) still have STALE timestamps from the earlier buggy detection run. Must re-detect before trimming.
    - The annotation tool's space bar (play/pause) doesn't work — only arrow key frame stepping works. Low priority fix.
    - Action labeling UI is built but not needed for P0. Will be stripped from P0 tool and deferred to T2 phase.
    - Internet connection was too slow (~115 KB/s) to download the remaining source videos. Need wifi for the ~150-200MB per video downloads.
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
