# CLAUDE.md — A1: Right-of-Way Referee for Fencing

Guidance for Claude Code working in this repository. Read this before touching anything.

---

## 1. What this is

A research system that watches a fencing phrase and calls **right-of-way** (priority) —
who gets the point when both fencers land. Foil is primary, sabre is the transfer target,
épée is a **negative control**.

**The deliverable is a research repository and a released benchmark.** Not a product.
The README is the artifact a reader opens.

### Canonical documents (outside this repo, in `~/Documents/Job/pipeline/`)

| File | Authority |
|---|---|
| `a1-fencing-referee-prd.md` | **Canonical for *what and how*.** Architecture, data plan, eval protocol, phases, acceptance criteria. When this file and the PRD disagree, **the PRD wins** — and update this file. |
| `a1-fencing-referee.md` | Canonical for *why*. Motivation, moat, framing. |
| `fencing-projects.md` | Catalog of adjacent ideas (F1–F7). Not in scope here. |
| `build-plan.md` §2, §7 | Sequencing against other projects; the metrics-ledger rule. |

Section references below (`§7.3`, `§10.6`, `P1`) are PRD sections. **Read the cited PRD
section before implementing against it** — this file is a map, not a substitute.

---

## 2. Decisions that are locked

Do not relitigate these in code, in a PR, or in a suggestion. Changing one means editing
the PRD first.

| # | Locked |
|---|---|
| D1 | Full scope: pose + blade + audio, cross-weapon transfer, hard-case benchmark, explanations |
| D2 | Research repo + released benchmark. **No product, no UI, no deploy** — but see §7 below: figures and debug overlays are *required* |
| D3 | **Local Mac (Apple Silicon / MPS) is the compute baseline.** Cluster is an addition, never a dependency. Only P4b needs a GPU |
| D4 | **Publicly posted competition footage only.** No club recording, ever |
| D5 | **Offline inference only.** No real-time constraint — bidirectional attention, multi-pass, ensembling all permitted |
| D6 | Full public release, paper-grade rigor: benchmark, code, weights, protocol |
| D7 | Fully prescriptive spec. Follow §11 layout and §11.4 schemas exactly |
| D8 | Tiered labeling with a saturation stopping rule, not a fixed clip count |
| D9 | A1 is the priority project. Other builds resequence around it |

---

## 3. The five rules that cannot be broken

These are the ones where a mistake invalidates the whole project. Treat any change that
touches them as high-risk and say so out loud.

### 3.1 The apparatus firewall

**The score delta is the label. It must never reach the model as an input.**

Free supervision (§7.3) works because the answer is visible in the frame — the lights and
the scoreboard. A model with unrestricted frame access can read the answer off the
scoreboard and score ~100% while learning nothing.

- The light-state feature passed to S7 is **restricted to light onsets and truncated
  before any score update**.
- `src/a1/apparatus/firewall.py` enforces the separation between the S1 label path and
  the S7 feature path. **It is the most important file in the repo.**
- `tests/leakage/` contains a test that **fails the build** if a scoreboard region can
  reach the model. Never skip, xfail, or loosen it.
- The épée control (§8.3) must land **at chance**. If épée scores above chance, something
  is leaking — stop and find it before doing anything else.
- `viz.attention` (§11.10.1) is the third check. Run it at P3 and again whenever a feature
  stream is added. The firewall tests what we thought to exclude; attention shows what we
  didn't.

### 3.2 The lockbox

~15% of gold-labeled data, stratified by weapon / athlete / event / contestedness,
generated once at P2 with a fixed seed and committed as a fold definition.

- **Never evaluate against it** until the pre-registered final evaluation (§10.3).
- The loader refuses to run without an explicit environment flag. Every access is logged
  to a committed file.
- `EVALUATION_PREREGISTRATION.md` must predate the first lockbox access log entry.
- If the lockbox is touched more than once, **say so in the README.** That disclosure is
  worth more than the number it protects.
- Never suggest "just check it quickly to see how we're doing."

### 3.3 Every number traces to an artifact

- `RESULTS.md` is **generated** by `make results` from run artifact directories.
  **Never hand-edited.** CI checks this.
- Every run writes: resolved Hydra config, git SHA + dirty-tree flag, environment lock,
  fold-definition hash, seed, per-epoch metrics, final metrics with CIs, predictions
  Parquet, failure-taxonomy breakdown.
- **CI fails a reported run from a dirty tree.**
- A number in the README that no artifact directory produced is a bug.
- Every reported number is **mean ± std over seeds `[0,1,2,3,4]`**.

### 3.4 Nothing that affects a result is a flag or a constant

Hydra, composed, always. If it changes an outcome, it lives in `configs/` and is committed.
No magic numbers in `src/`, no `--lr 3e-4` on the command line for a reported run.

### 3.5 Report the protocol, not just the number

Every published baseline is cited **with its version and its split protocol**. The
comparison is protocol-matched or it is not a comparison. See §5 below.

---

## 4. Repository layout

```
a1-fencing-referee/
├── README.md                     # the artifact: related work, protocol, results, honesty
├── EVALUATION_PREREGISTRATION.md # committed before the lockbox opens
├── DATA_STATEMENT.md             # sources, posture, what is and is not released
├── RESULTS.md                    # GENERATED by `make results`. never hand-edited
├── LICENSE
├── pyproject.toml                # uv-managed, locked
├── Makefile                      # every documented command has a target
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
│
├── configs/                      # Hydra
│   ├── config.yaml
│   ├── data/       {corpus, splits, tiers}
│   ├── model/      {prt, fera_mdt, bilstm, tcn, bifencenet, heuristic}
│   ├── features/   {pose2d, pose3d, blade, audio, appearance, relational}
│   ├── training/   {pretrain_ssl, pretrain_weak, finetune_gold, semisup}
│   ├── eval/       {s_clip, s_bout, s_athlete, s_event, s_both, temporal, lockbox}
│   ├── ablation/   {a01..a16}
│   └── compute/    {mac_mps, hpc_slurm, cloud}
│
├── src/a1/
│   ├── corpus/         # S0: yt-dlp acquisition, manifest, content-addressed cache
│   ├── apparatus/      # S1: light state, OCR, exchange bounding, weak labels
│   │   └── firewall.py #     §3.1 above. heavily tested
│   ├── tracking/       # S2: detect, pose, track, canonicalize
│   ├── kinematics/     # S3: 2D FERA-compatible block, 3D strip block, relational
│   ├── blade/          # S4: guard, direction, streak, contact, synthetic pretraining
│   ├── audio/          # S5: onset, classifier, A/V sync
│   ├── appearance/     # S6: video backbone features
│   ├── models/         # S7: PRT + every baseline, one file each
│   ├── rules/          # S8/S9: taxonomy, rule program, trace, justification
│   ├── calibration/    # S10: temperature, risk-coverage, ensembling
│   ├── data/           # datasets, splits, lockbox guard, active selection
│   ├── eval/           # metrics, bootstrap, mcnemar, wilcoxon, failure taxonomy
│   ├── viz/            # overlay renderer, curves, confusion matrices
│   └── cli/            # every pipeline stage as a resumable command
│
├── tools/annotate/     # §9.3 annotation tool (PySide6)
├── tests/
│   ├── unit/ property/ integration/ leakage/ fixtures/
├── scripts/            # slurm submission, corpus sync, release packaging
├── notebooks/          # exploration only. NEVER imported by src/
└── data/               # gitignored, content-addressed. manifests ARE committed
```

**Rules:** one baseline model per file in `src/a1/models/`. `notebooks/` is never imported
by `src/`. `data/` bytes are gitignored; manifests are committed (DVC over the
content-addressed cache).

---

## 5. Stack

Python 3.11 · **uv** (locked) · PyTorch 2.x + **Lightning** · **Hydra** · **MLflow**
(must work offline on a compute node) · DVC · Polars + Parquet · pytest + **Hypothesis** ·
ruff · **mypy --strict on `src/a1`** · pre-commit · GitHub Actions · Docker (local) /
Apptainer (HPC) from one definition.

Perception: **RTMDet + RTMPose** (MMDet/MMPose, FERA-matched) · **WHAM** for 3D
(alt 4D-Humans/HMR2.0) · **Norfair** tracking (alt ByteTrack) · **SAM 2** + **CoTracker3** ·
PaddleOCR (alt EasyOCR) · torchaudio + librosa · **V-JEPA 2** (alt VideoMAE V2), frozen
first · PyAV + decord · yt-dlp.

**Wrap RTMDet/RTMPose behind a `PoseEstimator` protocol.** MM installs are brittle on
Apple Silicon and the alternates (Ultralytics YOLO-pose, Sapiens) must be swappable by
config alone.

**Pin every version. Commit the lock file. Record the resolved environment in every run's
artifacts.** D6 makes reproducibility a deliverable.

---

## 6. Evaluation — the actual contribution

**The protocol is the argument.** A1's headline is not an accuracy number, it is that this
task has never been evaluated on athlete-disjoint splits.

### The split ladder (R3) — always report all five

| Protocol | Constraint |
|---|---|
| S-clip | 5-fold multilabel-stratified, clip level. **Matches FERA — the comparison arm** |
| S-bout | No bout in both train and test |
| S-athlete | No fencer in both train and test. **The honest number** |
| S-event | No competition in both train and test |
| **S-both** | Athlete- *and* event-disjoint. **A1's headline protocol** |

Plus a **temporal split** (train before date D, test after) as a drift check.

### The bar, stated correctly

| System | Version | Weapon | Number | Protocol |
|---|---|---|---|---|
| Allez Go | JSR | unspecified | 89.1% | split protocol **not stated**; student-research journal |
| FERA-LM | v1/v2 | foil | 77.7% | 969 exchanges, bout-disjoint, **not athlete-disjoint** |
| FERA structured | current | foil | 0.624 acc / 0.632 macro-F1 | "shared protocol" |
| FERA-MDT | current | foil | 0.549 ± 0.018 macro-F1 | 5-fold stratified, clip-level |
| BiFenceNet | CVPRW'22 | footwork | 87.6% | person-independent 10-fold |

**Beating 89.1% is explicitly *not* a success criterion.** Protocol-matched comparison is.
70% on an honest athlete-disjoint split is a good result; 70% against 89.1% on a
self-selected split is not the same claim. Never let a number appear without its protocol.

### Also required

- **Human ceiling (R7)** drawn as a band on every accuracy axis. Nothing in this literature
  is readable without it.
- **Failure taxonomy (§10.5)**, pre-declared categories, compared against the *human* error
  distribution on the same clips.
- **Leakage audit (§10.6)** run before the lockbox opens. Every check is a committed test.
- Statistical protocol per §10.3: bootstrap CIs, McNemar, Wilcoxon. Not bare point estimates.

---

## 7. Visualization — required, with a hard line

D2's "no UI" bans a **product**, not **pictures**.

| Serves | Verdict |
|---|---|
| You, locally (debug overlays, annotation tool, leak inspection) | **Required** |
| The README's reader (result figures, qualitative examples, rule traces) | **Required** |
| A stranger over the network (hosted demo, upload flow, accounts, deploy) | **Out of scope** |

- **Static outputs only** — MP4, PNG, SVG on disk. No server, no browser app, no JS.
- **matplotlib** for plots, **OpenCV/PIL** for overlays. Nothing else.
- `make figures` regenerates every README figure from committed artifacts. A figure that
  cannot be regenerated does not go in the README.
- **Timebox: 2 days total across the whole project.** Debug renderers are written when the
  stage they debug is written, not up front.
- **Descope order:** cut optional README figures first. **Never cut the blade, pose, and
  attention overlays** — those are how we know the numbers are real.

Required renderers: `viz.overlay.blade`, `viz.overlay.pose`, `viz.overlay.exchange`,
`viz.overlay.contact`, `viz.attention`, `viz.failure`, plus the rule-trace timeline.

---

## 8. Phases and current state

**Two tracks. The rule: run Track A to completion. Do not wait on the cluster for anything.**

| Phase | Track | GPU | Delivers | State |
|---|---|---|---|---|
| **P0** Foundations | A | No | Repo, tooling, annotation tool, sponsor email | ← **current** |
| **P1** Free supervision | A | No | T0 corpus, Path A + Path B labels | |
| **P2** Replication | A | No | Harness validated against FERA; lockbox generated | |
| **P3** Protocol result | A | No | **R3, R4**, épée control | |
| **P4a** Blade data | A | No | Blade keypoint annotation, synthetic generator | |
| **P5** Audio fusion | A | No | Audio contact detection | |
| **P6** Rules and explanations | A | No | **R6, R8**, explanation corpus | |
| **P7** Cross-weapon transfer | A | No | **R2** — the result nobody has | |
| **P8** Hard cases, ceiling, release | A | No | **R5, R7**, benchmark release | |
| **P4b** Blade detector training | **B** | **Yes** | **R1** — the headline | GPU-gated |

Track A alone delivers seven of eight contributions and is a complete, defensible project.
After P3, P4a/P5/P6/P7/P8 are mutually independent — recommended order **P4a → P7 → P6 →
P5 → P8** (P8 last, because it opens the lockbox).

**A phase is not complete until its exit criteria are demonstrably met — not "mostly
working."** Read the phase's PRD section for its exit criteria before declaring it done.

### P0 exit criteria (what we're working toward now)

- [ ] CI green on an empty pipeline
- [ ] `make test` passes, including property tests on a stub rule engine
- [ ] Annotation tool labels a fixture clip end to end → valid `annotations.parquet`
- [ ] `profile/entries/a1-fencing-referee.md` created with **every §15 measure pre-written
      as an empty checkbox** (20 minutes, non-negotiable)
- [ ] Row added to `reference/entry-placement.json`
- [ ] **Faculty-sponsor email sent** (YCRC / NSF ACCESS) — the only item with external
      latency; it blocks nothing but should be in flight from day one
- [ ] Corpus acquisition started — it runs in the background for weeks

P0 has **no descope condition.**

---

## 9. Commands

Every documented operation is a `make` target. Add one rather than documenting a raw
command.

```
make setup       # uv sync, pre-commit install
make lint        # ruff + mypy --strict on src/a1
make test        # unit + property + schema + leakage + integration on fixtures
make corpus      # S0 acquisition from the committed source manifest (resumable)
make label       # S1 free supervision: light state, OCR, bounding, score-delta oracle
make features    # S2–S6 feature extraction
make train       # Hydra-composed; every reported run over seeds [0,1,2,3,4]
make eval        # the split ladder + statistical protocol
make ablate      # the §10.4 matrix
make figures     # regenerate every README figure from committed artifacts
make results     # regenerate RESULTS.md from artifact directories
make reproduce   # clean-checkout reproduction of every number in RESULTS.md
```

**Every CLI stage must be resumable.** Corpus acquisition runs for weeks; a stage that
can't resume from a partial cache is a bug.

---

## 10. Testing expectations

| Layer | Bar |
|---|---|
| Unit | Every module |
| Property (Hypothesis) | Homography round-trips; feature invariance to translate/scale/mirror; rule engine over generated structured states |
| Rule engine table tests | Textbook cases **with cited rulebook articles**. Target 100% branch coverage on `src/a1/rules` |
| Swap-equivariance | `f(swap(x)) == swap(f(x))` within tolerance, on every trained checkpoint, in CI against a committed tiny checkpoint |
| **Leakage** | Every §10.6 check, as a test that **fails the build** |
| Lockbox guard | Loader raises without the explicit flag; every access is logged |
| Integration | Full pipeline on the 10-clip fixture corpus, **under 10 minutes in CI** |
| Determinism | Same seed → same metrics within tolerance, twice |
| Schema | Every Parquet write validated (Pandera or equivalent) |

The rule engine is a **pure function**. Test it like one.

---

## 11. Data schemas

Parquet, explicit schemas, validated on write. Full field lists in PRD §11.4 — read it
before adding or renaming a column.

`clips.parquet` (per source video) · `exchanges.parquet` (per extracted exchange, carries
`label_tier`, `confounder_flags[]`, `split_assignment`, `in_lockbox`) · `poses.parquet` ·
`blade.parquet` · `contacts.parquet` · `annotations.parquet` (per exchange × annotator ×
tier, carries `justification_structured` and `justification_text`) · `predictions.parquet`
(per run × exchange, carries `rule_trace` and `error_category`).

Schema changes are migrations, not edits. Bump and record.

---

## 12. Attribution — the one failure mode that reads as dishonest

An informed reader will check these. Get them right in the README before anything else.

- **Cite Allez Go twice.** Once for the 89.1% baseline, and once for the
  **score-delta labeling oracle** — Jason Mo published that method
  ([automated data collection from YouTube][mo]). A1 did **not** invent it.
  A1's contribution at the supervision layer is narrower and true: the confounder
  handling, the two measured error-rate gates, and the apparatus firewall (§10.6).
  **Any comment, docstring, or README line claiming the oracle as novel is a bug.**
- **Cite FERA** ([arXiv 2509.18527][fera]) with **both** numbers and **both** versions —
  77.7% (FERA-LM, v1/v2) and 0.624 (structured, current). A citation without a version is
  not checkable on a paper revised five times.
- **Cite FenceNet / BiFenceNet** (Zhu & Wong, CVPRW 2022) — and note that its
  person-independent folds mean the rigor A1 proposes **already exists in the adjacent
  literature**. Not doing it is the anomaly.
- **Cite VirtualFencer** (arXiv 2507.00261) — its monocular→3D strip-coordinate pipeline
  is what A1's 3D kinematics block builds on.
- **Cite `sholtodouglas/fencing-AI`.**

**A1's deliberate divergence, and present it as one:** Mo uses fixed 2-second windows
centred on the touch. A1 bounds each exchange **backward to the last en-garde reset and
forward to the score update**, because initiation routinely precedes the touch by more
than a second. Back it with the ablation — fixed-2s vs. reset-bounded, same model, same
folds. If the fixed window loses, that explains part of the gap to 89.1%.

[mo]: https://thejasonmo.medium.com/automated-data-collection-from-youtube-6e433b0e3513
[fera]: https://arxiv.org/abs/2509.18527v2

---

## 13. Non-goals — do not build these, do not suggest them

- Real-time or piste-side inference (D5)
- A web app, upload UI, or coach dashboard (D2)
- Deployment, auth, multi-tenancy, ops (D2)
- Recording at Daniel's club (D4) — public footage only
- Épée priority — épée has no priority; it is the negative control
- Detecting whether a touch landed — the apparatus already does this and A1 **consumes**
  its output
- Full rulebook coverage — no cards, no ground judges, no equipment control

---

## 14. Working style in this repo

- **Read the cited PRD section before implementing against it.** This file summarizes; the
  PRD specifies.
- **A negative result is a result.** R1 (blade perception doesn't help) and a failed FERA
  replication are both publishable outcomes. Report them; never quietly drop a workstream
  because the number came out wrong.
- **Write the measure down when you have it.** §15's ledger lives in
  `profile/entries/a1-fencing-referee.md` as pre-written empty checkboxes. A number not
  written down while you have it cannot be recovered honestly.
- **When descoping, follow the phase's stated descope condition.** Don't lower a gate —
  narrow the corpus. A smaller clean corpus beats a larger noisy one.
- Prefer the honest framing to the flattering one, in code comments and in the README
  alike. Every soft claim in this project has already been made softer once on purpose.

---

*Sources: `pipeline/a1-fencing-referee-prd.md` (Aug 27, 2026) and
`pipeline/a1-fencing-referee.md` (Aug 26, 2026). Update this file whenever the PRD moves.*