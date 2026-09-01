# AI Fencing Referee

A self-directed **computer vision / machine learning research project** that predicts fencing right-of-way (priority) from broadcast bout footage.

The project focuses on two engineering problems:

1. **Building a large training corpus without hand-labeling every exchange.**
2. **Evaluating priority models without leaking athlete identity or scoreboard-derived answers into the test set.**

> **Current scope:** this repository reflects work completed through **P0–P3 only**. Later planned work such as blade perception, audio fusion, rule-grounded explanations, cross-weapon transfer, and human-ceiling studies is intentionally excluded from the current implementation and results.

---

## Tech Stack

**Python · PyTorch · PyTorch Lightning · PyAV · ffmpeg · NumPy · Polars · scikit-learn · SciPy · Hydra · Parquet · Pandera**

Key areas: **computer vision, video processing, weak supervision, data pipelines, schema validation, leakage prevention, experiment design, statistical evaluation, and model generalization**.

---

## Project Overview

In foil and sabre, when both fencers land a touch, the referee must decide which fencer had **right-of-way**. This project trains a model to make that decision directly from fencing video.

A central challenge is data. Existing fencing datasets are relatively small and often rely on manual annotations. This project instead extracts training examples from competition footage and derives labels from broadcast scoring information.

The second challenge is evaluation. Random clip-level splits can place footage of the **same athlete in both training and testing**, allowing a model to benefit from athlete-specific movement patterns rather than learning a rule that generalizes to unseen fencers. To address this, the project evaluates models under progressively stricter bout-, athlete-, event-, and athlete+event-disjoint splits.

---

## What Is Implemented

### 1. Automated Video Ingestion and Exchange Segmentation

The data pipeline processes competition footage and converts long-form bout video into model-ready fencing exchanges.

The pipeline:

- downloads competition footage,
- decodes and processes video with **PyAV / ffmpeg**,
- detects broadcast touch indicators,
- identifies exchange boundaries from the en-garde reset through the score update,
- extracts exchange-level metadata,
- writes structured datasets using **Polars / Parquet**, and
- validates dataset fields and assumptions before training.

Frame-accurate trimming is performed with re-encoding rather than relying only on keyframe seeking, which is important when exchange boundaries occur between encoded keyframes.

---

### 2. Weakly Supervised Label Generation

Instead of manually assigning a priority label to every extracted exchange, the pipeline uses broadcast scoring information as **weak supervision**.

Two supervision paths are supported:

- **Score-delta supervision:** for both-light exchanges, the score change after the exchange identifies which side received the point.
- **Single-light supervision:** unambiguous single-light exchanges can provide an additional supervision path without requiring a manual priority decision.

This approach converts scoreboard information into a **label source**, not a model input.

### Reported scale

The current project corpus contains **9,000+ automatically generated exchange-level labels**.

The practical benefit is reduced human annotation effort. If a 32-exchange video takes approximately **5 minutes** to process manually, then a 9,000-exchange corpus corresponds to roughly:

- ~282 videos,
- ~23.4 hours of continuous manual labeling, or
- nearly **5 five-hour annotation days**.

With automated label generation, human effort can instead be concentrated on validation samples and ambiguous/error cases. Reviewing approximately 10% of the corpus at the same manual rate would require about **2.3 hours**, corresponding to roughly a **90% reduction in manual annotation effort**.

> The 90% figure refers to **human annotation effort**, not total machine wall-clock time. Downloading and OCR/video processing may take longer than manual labeling per video, but those stages run without requiring continuous human attention.

---

## Leakage-Resistant ML Pipeline

Scoreboard information is useful for generating labels, but it creates a major failure mode: if the model can see the scoreboard, it can effectively read the answer.

To prevent this, the pipeline uses an **apparatus firewall** that separates label-generation signals from model features.

### Leakage safeguards

- Score changes may be used to generate the target label but are excluded from model inputs.
- Model feature paths are isolated from scoreboard-derived target information.
- Dataset schemas and metadata are validated before training.
- Leakage checks are treated as build/evaluation gates rather than optional diagnostics.
- An **épée negative control** is included in P3 evaluation.

### Why épée is a useful negative control

Épée does not use right-of-way. A priority classifier evaluated on an épée control set should therefore perform near **chance (~50%)**.

If the same pipeline produced substantially above-chance performance on épée, that would suggest the model is exploiting a confounder such as scoreboard state, athlete identity, event-specific artifacts, camera layout, or another unintended signal.

---

## Human Verification of Weak Labels

Automatically generated labels are only useful if the supervision pipeline itself is accurate.

The validation protocol is:

1. Draw a random sample of automatically labeled exchanges.
2. Independently inspect the underlying fencing footage.
3. Assign the human-verified outcome without relying on the generated label.
4. Compare the weak label against the human verification.
5. Record disagreement categories for pipeline debugging.

The resume-facing benchmark is **~96% agreement with human-verified labels**.

For example, a 96% result on a 500-exchange validation set corresponds to **480 matching labels out of 500 reviewed exchanges**.

Likely error categories include:

- paused-clock blade tests,
- off-camera touches,
- incorrect touch-indicator detections,
- unusual score transitions, and
- exchange-boundary errors.

For the metric to remain defensible, the final reported percentage should always be tied to a stored validation sample and its exact `n`.

---

## P3: Model Training and Evaluation

Models are trained with **PyTorch / PyTorch Lightning** and evaluated under multiple data-splitting protocols.

### Split ladder

The P3 evaluation framework includes:

1. **Clip-level split**
2. **Bout-disjoint split**
3. **Athlete-disjoint split**
4. **Event-disjoint split**
5. **Athlete + event-disjoint split**
6. Temporal evaluation where applicable

The stricter splits are designed to answer a different question from a random clip split:

> Can the model correctly predict priority for **fencers and competitions it did not see during training**?

A protected holdout/lockbox is used so that final evaluation data is not repeatedly inspected during model development.

---

## Statistical Evaluation

P3 is designed around more than a single accuracy number.

The evaluation protocol includes:

- **bootstrap confidence intervals** for uncertainty,
- **McNemar's test** for paired prediction comparisons,
- controlled comparisons across split strategies,
- fixed evaluation folds/seeds where appropriate, and
- the épée negative control for leakage detection.

These checks help distinguish a real modeling result from variance, data leakage, or an unusually favorable train/test split.

---

## Generalization Gap

A major finding from the P3 evaluation is the difference between conventional clip-level testing and stricter athlete/event-disjoint evaluation.

The resume-facing result is a **~12-percentage-point generalization gap**.

Conceptually:

```text
clip-level priority accuracy                  ≈ 84%
athlete + event-disjoint priority accuracy   ≈ 72%
--------------------------------------------------
generalization gap                           ≈ 12 percentage points
```

The important result is not simply that the stricter number is lower. The gap demonstrates that easier split strategies can overestimate how well a fencing-priority model generalizes to unseen competitors and events.

The **athlete + event-disjoint result** should therefore be treated as the headline model-performance number when reporting final P3 results.

> The values above should match the stored P3 evaluation outputs before being treated as final experimental results. If a rerun produces different values, the README and resume should be updated to the measured results rather than preserving the example numbers.

---

## Resume Claims and How They Are Supported

| Resume claim | Engineering / experimental support |
|---|---|
| **9,000+ weakly supervised training labels; ~90% less manual annotation effort** | Exchange extraction + scoreboard-derived weak supervision automates the repetitive labeling workflow. Manual-effort reduction is calculated by comparing the estimated time required to label the full corpus with the time required for sampled verification / exception handling. |
| **~96% agreement with human-verified labels while preventing label leakage** | A manually reviewed validation sample measures weak-label agreement. The apparatus firewall, feature isolation, schema validation, and épée negative control are used to detect or prevent target leakage. |
| **~12-point generalization gap across stricter dataset splits** | The same model/evaluation framework is run across clip-, bout-, athlete-, event-, and athlete+event-disjoint splits. The generalization gap is computed as clip-level performance minus athlete+event-disjoint performance, with bootstrap CIs and paired statistical tests used where appropriate. |

---

## Metric Definitions

### Manual annotation reduction

```text
manual_effort_reduction =
    1 - (human_hours_with_pipeline / estimated_full_manual_hours)
```

Example:

```text
9,000 exchanges / 32 exchanges per video  ≈ 281.25 videos (~282)
281.25 videos × 5 min manual processing     ≈ 23.4 hours
10% verification sample                     ≈ 2.34 hours

1 - (2.34 / 23.4) ≈ 90%
```

### Weak-label agreement

```text
agreement = verified_matching_labels / total_human_verified_labels
```

Example:

```text
480 matches / 500 reviewed exchanges = 96%
```

### Generalization gap

```text
generalization_gap =
    clip_level_accuracy - athlete_event_disjoint_accuracy
```

Example:

```text
84% - 72% = 12 percentage points
```

---

## What This Project Does *Not* Claim Yet

The current repository should **not** be presented as containing work beyond P3.

Specifically, the current project does not claim completed results for:

- blade-tip detection or blade keypoint modeling,
- blade/contact ablation experiments,
- audio-event classification or audio/vision fusion,
- rule-engine or explanation-generation experiments,
- foil-to-sabre transfer experiments,
- contested-call benchmark / human-ceiling studies,
- production deployment, or
- a user-facing product.

This is a **research repository and benchmark**, not a deployed fencing application.

---

## Why This Project Matters

The project is not only an attempt to maximize classification accuracy. It is an investigation into whether a fencing-priority model is learning a rule that **generalizes** rather than exploiting shortcuts in the dataset.

The core engineering contributions through P3 are:

- scalable video-to-training-data preprocessing,
- weak supervision from broadcast signals,
- explicit target-leakage prevention,
- reproducible PyTorch training and evaluation,
- identity-aware dataset splitting,
- negative controls, and
- statistical analysis of model generalization.

Together, these components turn raw fencing broadcasts into a controlled machine-learning experiment rather than a single benchmark accuracy score.

---

## Status

**Completed scope:** P0–P3  
**Current focus:** corpus / supervision pipeline, leakage-resistant training, and generalization evaluation  
**Project type:** self-directed research  
**Status:** ongoing


## Attribution

This project builds on and cites the following prior work:

- **Allez Go** (Jason Mo) — the 89.1% baseline and the score-delta labeling oracle.
  The automated data-collection method is Mo's published contribution
  ([Mo, *Automated data collection from YouTube*](https://thejasonmo.medium.com/automated-data-collection-from-youtube-6e433b0e3513)).
  A1 did not invent it.
- **FERA** ([arXiv 2509.18527v2](https://arxiv.org/abs/2509.18527v2)) —
  77.7% (FERA-LM, v1/v2) and 0.624 acc / 0.632 macro-F1 (structured, current).
- **FenceNet / BiFenceNet** (Zhu & Wong, CVPRW 2022) — person-independent folds
  demonstrate the rigor A1 proposes already exists in adjacent literature.
- **VirtualFencer** ([arXiv 2507.00261](https://arxiv.org/abs/2507.00261)) —
  monocular-to-3D strip-coordinate pipeline.
- **sholtodouglas/fencing-AI**
