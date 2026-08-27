# Project Progress

> Single source of truth for phase ownership and progress.
> Updated by the `/save` command. Read by `/start`.
> Phases are defined in CLAUDE.md §8 and the PRD.

**Last updated:** 2026-08-27

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
  - [ ] CI green on an empty pipeline
  - [ ] `make test` passes, including property tests on a stub rule engine
  - [ ] Annotation tool labels a fixture clip end to end → valid `annotations.parquet`
  - [ ] `profile/entries/a1-fencing-referee.md` created with every §15 measure pre-written as empty checkboxes
  - [ ] Row added to `reference/entry-placement.json`
  - [ ] Faculty-sponsor email sent (YCRC / NSF ACCESS)
  - [ ] Corpus acquisition started
- **Steps:**
  - [ ] Set up repo structure per §11 layout
  - [ ] Configure uv, pyproject.toml, lock file
  - [ ] Set up pre-commit (ruff + mypy --strict)
  - [ ] Create Makefile with all documented targets
  - [ ] Set up CI (GitHub Actions)
  - [ ] Create Hydra config structure
  - [ ] Stub rule engine with property tests
  - [ ] Build annotation tool (PySide6)
  - [ ] Create fixture clip corpus (10 clips)
  - [ ] Write apparatus firewall with leakage tests
  - [ ] Create profile entry with §15 measures
  - [ ] Add row to entry-placement.json
  - [ ] Draft and send faculty-sponsor email
  - [ ] Start corpus acquisition (background)
- **Resume context** (written by `/save`):
  - **Last worked:** —
  - **Last commit:** —
  - **Files touched this session:** —
  - **Next step:** —
  - **Open questions / gotchas:** —

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
  - [ ] Ablation matrix (§10.4) completed
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
  - [ ] Leakage audit (§10.6) run before lockbox opens
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
