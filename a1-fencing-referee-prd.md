# PRD — A1: A Right-of-Way Referee for Fencing

**Document type:** Product / build requirements document, written to be executed by Claude Code.
**Version:** 1.4
**Date:** August 26, 2026 · revised August 27, 2026
**Owner:** Daniel Lee
**Status:** Approved for build. Supersedes the build-order sections of `build-plan.md` (see §14).

**Revision history**

| Rev | Sections | Change |
|---|---|---|
| 1.1 | §3.4, §7.2, §7.3, §12 P1, §13, §15, §18 | Score-delta oracle attributed to prior art; Path B single-light supervision added — see §3.4 |
| 1.2 | §10.3, §10.4, §11.8, §13, §18 | Seed rule and ablation design corrected per [Bouthillier et al.][bout]; compute plan rebuilt with a real access/fallback ladder |
| 1.3 | §2 D3, §12.0, §12 (P4 split into P4a/P4b), §14, §17 | **Restructured into Track A (no GPU, seven of eight contributions) and Track B (GPU-gated, R1 only).** The cluster is now an addition to a complete project, never a dependency |
| 1.4 | §2 D2, §11.9, §11.10 (new), §13 R-9, §17 Q8 | **Visualization specified and made required.** D2's "no UI" banned a product, not pictures; debug overlays and README figures are now explicit deliverables, with a public demo deferred to Q8 |

---

## 0. How to read this document

There are now two A1 documents and they do different jobs.

| Document | Job | Authority |
|---|---|---|
| [`a1-fencing-referee.md`](a1-fencing-referee.md) | **Why.** The decisions, the moat argument, the framing, the honest risks | Canonical for rationale |
| **This file** | **What and how.** Contributions, architecture, data plan, evaluation protocol, repo spec, phase gates, acceptance criteria | Canonical for the build |

Where they conflict, **this document wins**, and §3 lists every place they conflict and why.

**A note on the scope change.** The canonical spec §6 chose Option A — pose-only first, blade tracking deferred to a post-January extension — because it was optimizing against a time budget. That budget has been removed. This PRD specifies **Option B**: the full system, blade tracking included, phased internally so that each phase produces a defensible result on its own but none of them is the stopping point.

**Conventions used throughout:**

- `[X]`, `[N]`, `[Y]` are **placeholders that stay bracketed until measured.** Per `resume-rules.md` rule 0.2, no exceptions. Nothing in this document invents a number for Daniel's own system.
- Every published number attributed to prior work carries a citation to §18 and a version, because — see §3.1 — one of them moved.
- Each phase in §12 has **entry criteria, exit criteria, and a descope condition.** The descope condition is what you do when the phase does not work, decided in advance rather than under pressure.

---

## 1. Summary

Foil and sabre are decided by **right-of-way**: when both fencers land, the referee decides who had priority — who initiated the attack, whether a parry landed, whether the attack lost tempo. It is the single most argued-about judgment in the sport.

**A1 is a research system that watches a fencing phrase and calls it**, together with the benchmark, the evaluation protocol, and the labeled corpus that make the call checkable.

**In one sentence, for anyone:** *"It watches two fencers and tells you who should get the point — the thing referees argue about."*

**What makes it a research contribution rather than a reimplementation.** Two systems have published on this problem. Neither tracks the blade visually; both say so. Neither has been evaluated on athlete-disjoint splits; one names this as a limitation. Neither has published on sabre. No one has published the referee-written explanations that would supervise a system to say *why*. And nobody has measured the ceiling — how often two referees watching the same phrase agree with each other. This project addresses all five.

**The deliverable is a research repository and a released benchmark.** No product, no UI, no deployment. The README is what a reader opens.

---

## 2. Decisions locked

These were settled before writing and are not open for renegotiation mid-build. Changing one means revising this document, not improvising.

| # | Decision | Choice | Consequence |
|---|---|---|---|
| D1 | Technical scope | **Full system, all phases.** Pose + blade + audio, cross-weapon transfer, hard-case benchmark, referee explanations | §12 has 9 phases, not 3 |
| D2 | Deliverable | **Research repo + released benchmark.** No product, no service, no deploy | §11 has no frontend, no auth, no ops. **This bans a *product*, not *pictures*** — see §11.10. Local debug tooling and figure generation are required, not merely permitted |
| D3 | Compute | **Local Mac (Apple Silicon / MPS); the cluster is an addition, never a dependency** | §11.8 and §12.0. **Only P4b requires a GPU.** Track A — P0–P3, P4a, P5–P8 — is entirely Mac-viable and delivers seven of eight contributions. Sponsor outreach is a **week-1 action item** but blocks nothing |
| D4 | Data source | **Publicly posted competition footage only.** No club recording | §9.1; the entire artifact is unambiguously shareable, and camera angle/frame rate are givens rather than choices |
| D5 | Inference mode | **Offline only.** No real-time constraint | Bidirectional attention over the whole phrase, multi-pass refinement, and ensembling are all permitted. Accuracy is the only axis |
| D6 | Release | **Full public release, paper-grade rigor.** Benchmark, code, weights, protocol | §10 specifies significance testing, pre-registration, and a lockbox test set |
| D7 | Specification detail | **Fully prescriptive.** Exact libraries, layout, schemas, acceptance criteria | §11 and §12 are written for direct execution |
| D8 | Labeling | **Tiered protocol with a saturation stopping rule**, not a fixed clip count | §9.2 |
| D9 | Priority vs. other projects | **A1 is the priority.** Other builds resequence around it | §14 states exactly what slips and what that costs |
| D10 | Pairing | **A1 only.** Tournament scoring is a separate project with no coupling assumed | Not referenced further |

---

## 3. Corrections to the canonical spec

Research done for this PRD on August 26, 2026 turned up four things the Aug 25–26 prior-art pass got wrong or missed. Three of them make the project better. One of them makes the headline number softer, and it needs handling honestly rather than quietly. **§3.4 was added August 27, 2026** (renumbering the summary table to §3.5) and corrects a novelty claim this document itself made.

### 3.1 FERA's number moved — and the direction matters

`a1-fencing-referee.md` §4 cites FERA at **77.7% priority accuracy on 969 exchanges**, from arXiv `2509.18527v2`. That number is real and appears in the v1/v2 text. But the paper has been revised repeatedly — at least five versions, with **three different titles** — and the current abstract at the base arXiv identifier reports:

> *"a compact structured classifier on the fixed two-dimensional token stream reaches **0.624 accuracy** and a **0.632 macro-averaged F1** score on the final Left / Right / None decision."*

The 77.7% figure in the full text belongs to **FERA-LM**, the language-model reasoning layer applied on top of predicted moves. The 0.624 in the current abstract is described as being **"under a shared protocol"** — that phrase is the tell. The authors tightened the evaluation and the number came down.

**What this means for the build, and it is not bad news:**

1. **The bar for foil priority is a range, not a point: roughly 62% to 78% depending on which version and which protocol you cite.** Anyone who checks will find this. The README must state it precisely.
2. **A published number that moves 15 points across revisions of the same paper is itself an argument for this project.** The reason it moved is protocol. That is exactly the gap §10 fills with a pre-registered, athlete-disjoint, lockbox-tested protocol.
3. The canonical spec's §10 warning — *"a 70% model is no longer a neutral result"* — needs revision. Against the current shared-protocol number, 70% on an **honest athlete-disjoint split** would be a good result. Against 89.1% on a self-selected split, it would look bad. **The protocol is the whole argument**, and this is why §10 of this PRD is as long as it is.

**Action:** update `a1-fencing-referee.md` §4 to cite both numbers with their versions. Cite the version, always. A citation without a version is not checkable on a paper that has been revised five times.

### 3.2 FERA released a benchmark — direct comparison is possible

The canonical spec assumes no benchmark exists and treats building one as the contribution. That is now only half true. FERA states:

> *"We also release an audited benchmark with adjudicated labels and fixed folds for reproducible evaluation."*
> *"All source videos are publicly available competition recordings; we release only anonymized pose features, labels, and code."*

**This is strictly good.** It means:

- A1 can be evaluated **on FERA's own folds, on FERA's own features**, producing a number that is directly comparable rather than distribution-shifted. That is the strongest form of "a baseline he is beating" that `project-recommendations.md` gate 2 admits.
- **Replicating 0.624 on their released features and folds is P2's acceptance criterion.** If the replication fails, that is a finding in itself and must be reported.
- Their release policy — derived features and labels, not raw video — is the legal precedent A1 follows in §9.1. Someone else already made this call for the same footage. Follow it.

The hard-case benchmark A1 builds (§9.5) is still novel, because FERA's benchmark contains no protested/reversed subset and no explanations. The contribution narrows from "the first benchmark" to "the first benchmark of the *hard cases*, plus the first athlete-disjoint protocol." That is a sharper claim and a more defensible one.

### 3.3 Two prior systems the spec is missing

| System | What it does | Numbers | Why it matters here |
|---|---|---|---|
| **[FenceNet / BiFenceNet][fn]** (Zhu & Wong, CVPRW 2022) | Fine-grained **footwork** recognition from 2D skeletons; stacked TCNs, causal + anti-causal | **87.6%** (BiFenceNet), **85.4%** (FenceNet), vs. JLJA at 86.3%, on the Fencing Footwork Dataset (10 fencers, 6 actions, 652 videos), **person-independent 10-fold CV** | Two things. First, a TCN-over-skeletons baseline with published numbers — build it as an internal baseline. Second and more important: **FenceNet uses person-independent folds.** The rigor A1 is proposing already exists in the adjacent literature. Not doing it is the anomaly |
| **[VirtualFencer][vf]** (arXiv 2507.00261, 2025) | Extracts fencing strategy from in-the-wild video and generates bouts; WHAM → 3D SMPL, SAM 2 piste-line homography, YOLO detection | 1.5 hours, 40 international bouts, 54 senior FIE fencers | **The pipeline is directly reusable.** They solved monocular-video → globally-accurate 3D coordinates on the canonical 14 m strip. Both refereeing systems use flat 2D pose. 3D pose in strip coordinates makes distance, closing velocity, and lunge depth *physical* quantities instead of pixel quantities, and it removes camera-angle confounding — which is a plausible source of the athlete/event overfitting FERA warns about |

Both go in the README's related-work table. §10 of the canonical spec — cite everything, prominently — applies to these too.

### 3.4 The score-delta oracle is prior art — Allez Go's author published it

*Added August 27, 2026.*

§7.3 of this document called the score-delta oracle "the highest-leverage idea in this document" and argued it was novel because FERA used scoreboard changes only to *locate* clips. **The first half stands. The second half was wrong.**

Jason Mo — the author of **Allez Go**, the 89.1% number this project is measured against in §3.5 — published the method in a write-up on automated data collection ([Mo][mo]). His pipeline:

| Step | Method | Matches A1 §7.3? |
|---|---|---|
| Corpus | YouTube playlists of EFC competition footage, pulled programmatically | Yes — §7.2, though A1 uses `yt-dlp` and a committed source manifest |
| Touch detection | **Colour detector on fixed pixels of the standardized score overlay** to catch the scoring lights firing | Yes — §7.3 light state, though A1 registers the ROI per layout rather than assuming fixed pixels |
| Score reading | Pre-trained digit recognizer tracking score changes | Yes — §7.3 OCR, though A1 adds temporal smoothing and a monotonicity constraint |
| **Label derivation** | **Both on target → whichever fencer is awarded the touch. One light, no score change → the other fencer had priority** | **Yes — this is the oracle, and it is his, including the single-light path A1 was missing** |
| Segmentation | Fixed 2-second clips centred on the touch | **No — A1 diverges deliberately, see below** |
| Yield | **~8,000 clips, ~10 GB, in about one week** | The yield precedent for §12 P1 |

He also credits `sholtodouglas/fencing-AI` for parts of the implementation, which is already in §18.

**Three consequences, and none of them is bad:**

1. **The claim of novelty comes out of §7.3 and the README, and the citation goes in.** A1's contribution at the supervision layer is the confounder handling, the two measured error-rate gates, and the apparatus firewall (§10.6) — not the oracle. That is a narrower claim and a true one, and it is the same move §3.2 already made when FERA's benchmark turned out to exist.
2. **It de-risks P1 substantially.** The single highest-leverage component of this build is no longer an untested bet; it is a method with an independently reported yield. The risk register (§13) should reflect that.
3. **It hands A1 the single-light path** (§7.3 Path B), which this document did not have. That is a straight expansion of free supervision, gated separately because it is noisier.

**The deliberate divergence — clip bounding.** Mo uses fixed 2-second windows centred on the touch. A1 bounds each exchange backward to the last en-garde reset and forward to the score update (§7.3). **Keep A1's.** Priority turns on *who initiated*, and initiation routinely precedes the touch by more than one second — a preparation, a beat, a failed attack that becomes the other fencer's attack in tempo. A fixed 2-second window truncates exactly the evidence the label depends on, and R4 (temporal resolution, §6) is a stated contribution of this project. **This is a considered divergence from a working baseline, not an oversight, and the README should present it as one** — with the ablation to back it: fixed-2s versus reset-bounded windows, same model, same folds. If the fixed window loses, that is a clean result explaining part of the gap to Allez Go's number.

---

### 3.5 What the corrected bar actually is

| System | Version | Weapon | Metric | Number | Protocol |
|---|---|---|---|---|---|
| Allez Go | JSR | unspecified | referee agreement | **89.1%** | ~4,000 clips, 7 yrs international; split protocol not stated; venue is a student-research journal, not a peer-reviewed CV venue |
| FERA-LM | v1/v2 | foil | priority accuracy | **77.7%** | 969 exchanges, bouts disjoint from CV folds; **not athlete-disjoint** |
| FERA structured | current | foil | accuracy / macro-F1 | **0.624 / 0.632** | "shared protocol" |
| FERA-MDT | current | foil | move-recognition macro-F1 | **0.549 ± 0.018** | 5-fold multilabel-stratified, clip-level |
| FERA blade-line | current | foil | macro-F1 | **≈0.38** | 5-way {4, 6, 7, 8, other} |
| BiFenceNet | CVPRW'22 | n/a (footwork) | accuracy | **87.6%** | person-independent 10-fold |

**Read the last column, not the fourth.** Two of these numbers come from protocols that permit the same athlete in train and test. One comes from a protocol that does not. They are not on the same scale, and A1's contribution is partly to put them on one.

---

## 4. Goals and non-goals

### 4.1 Goals

**G1 — Priority accuracy.** Beat the published foil numbers under a protocol at least as strict as any of them, and report against every published number with its protocol stated.

**G2 — Blade perception.** Build explicit visual blade tracking and show, by ablation, whether it improves priority accuracy over an identical pose-only model. **A negative result here is publishable and is an acceptable outcome** — both existing systems avoided this because it is hard, and measuring the cost of that avoidance is the contribution either way.

**G3 — Protocol.** Establish athlete-disjoint, event-disjoint evaluation as the standard for this task and quantify the generalization gap between it and the clip-level protocol currently in use.

**G4 — Cross-weapon.** Measure foil→sabre zero-shot transfer. Run épée as a negative control.

**G5 — Hard cases.** Build and release a benchmark of contested calls — those subjected to video review, reversed on review, and the rare actions FERA names as underrepresented.

**G6 — Explanations.** Build the referee-written justification corpus that FERA explicitly identifies as missing, and a rule-grounded model that produces checkable explanations rather than post-hoc rationalizations.

**G7 — The ceiling.** Measure how often referees agree with each other on this task. Every accuracy number in this literature is reported as though 100% were the target. It is not.

### 4.2 Non-goals

| Not doing | Why |
|---|---|
| Real-time / piste-side inference | D5. Costs accuracy for a use case nobody asked for in a research artifact |
| A web app, upload UI, or coach dashboard | D2. This is a repo and a benchmark |
| Deployment, auth, multi-tenancy, ops | D2 |
| Recording at Daniel's club | D4. Public footage only keeps the artifact unambiguously shareable |
| Épée priority | Épée has no priority. It is the **negative control** — see §8.3 |
| Detecting whether a touch landed | The scoring apparatus already does this, correctly, and its output is visible in the footage. A1 **consumes** it (§7.3) rather than reproducing it |
| Full rulebook coverage | Scope is the priority decision and the actions that determine it. Not cards, not ground judges, not equipment control |
| Beating 89.1% as a success criterion | §3.4. Protocol-matched comparison is the criterion. See §13-R1 |

---

## 5. Users

The artifact's audience, in priority order:

1. **A researcher in sports CV or temporal action understanding.** Opens the README, wants the related-work table, the protocol, and the ablation matrix. Everything in §10 is for this reader.
2. **An engineer evaluating Daniel technically.** Opens the repo, wants to see whether the hard part was actually solved and whether the numbers are honest. §12's acceptance criteria and §11.6's tests are for this reader.
3. **A recruiter doing a six-second skim.** Reads one sentence. §16's bullets are for this reader.
4. **A fencing referee or coach.** Would use the explanation output for calibration. Not a build target under D2, but the explanation corpus (§9.6) is what would make it one later.

---

## 6. The contributions

Each is stated as a **falsifiable claim** with the experiment that tests it and the outcome that would refute it. A contribution that cannot be refuted is not a contribution.

### R1 — Blade perception improves priority accuracy

**Claim:** Adding explicit visual blade state (guard position, tip position, blade-blade contact events) to an otherwise identical model improves priority accuracy on foil by a margin exceeding the paired bootstrap 95% CI.

**Experiment:** Identical architecture, identical folds, identical seeds, with and without the blade feature block. McNemar's test on paired predictions.

**Refuted if:** the improvement is within noise, or negative. **This is an acceptable outcome** and must be reported as prominently as a positive one, because it answers the question both prior systems dodged. If refuted, the finding is *"explicit blade tracking, done to [X] px tip error, does not recover priority information that body pose does not already carry"* — which is a real, useful, and non-obvious result.

### R2 — Foil→sabre transfer gap

**Claim:** A foil-trained priority model transfers poorly to sabre, because sabre priority turns on tempo and initiation rather than blade contact.

**Experiment:** Train on foil only. Evaluate zero-shot on sabre. Report the delta. Then train a sabre model and report the gap to it. Do not train jointly first — the zero-shot number is the result.

**Refuted if:** transfer is near-lossless, which would imply the two weapons' priority rules are, at the level a model recovers them, the same rule. That would be the more interesting finding of the two.

### R3 — The protocol gap

**Claim:** Priority accuracy under athlete-disjoint, event-disjoint splits is materially lower than under the clip-level stratified splits currently reported, and the gap is large enough to change how published numbers should be read.

**Experiment:** Evaluate the same trained model under (a) clip-level stratified CV, (b) bout-disjoint, (c) athlete-disjoint, (d) event-disjoint, (e) athlete-*and*-event-disjoint. Report all five. Where FERA's released features permit, run their model under the same ladder.

**Refuted if:** the gap is negligible, which would mean these models generalize better than the literature's own limitations sections fear.

### R4 — Temporal resolution

**Claim:** Priority accuracy is limited by frame rate, and footage at 50/60 fps supports materially better accuracy than the 25 fps FERA used.

**Experiment:** On the subset of corpus available at ≥50 fps, train and evaluate at 60/50/30/25/12.5 fps by decimation, holding everything else fixed. Report the accuracy-vs-frame-rate curve.

**Why it matters:** at 25 fps, the 200 ms window in which priority is decided is **five frames**. FERA names higher frame rates as future work. This is the cheapest experiment in the document and it may explain a chunk of everyone's error.

**Refuted if:** the curve is flat, meaning the decision is carried by information at a coarser timescale than assumed.

### R5 — The hard-case benchmark

**Claim:** Model accuracy on contested calls — those a referee sent to video review — is substantially lower than on uncontested calls, and this gap is invisible in every number published to date.

**Experiment:** Mine video-review segments from broadcast footage (§9.5). Report accuracy on contested vs. uncontested, matched for weapon and event.

**Refuted if:** performance is equal, meaning what referees find hard and what models find hard are different things — also a finding worth having.

### R6 — Referee explanations as supervision

**Claim:** Training with referee-written justifications improves priority accuracy over training with the call alone, not merely explanation quality.

**Experiment:** Same architecture, same folds, with and without the justification-supervised auxiliary objective. Evaluate both call accuracy and explanation quality (§10.1).

**Why it matters:** FERA states plainly that this data does not exist. Producing it is the scarcest input in the subfield, and Daniel is one of a small number of people who can.

### R7 — The human ceiling

**Claim:** Referee-to-referee agreement on contested phrases is well below 100%, and the reported accuracies of existing systems should be read against that ceiling rather than against perfection.

**Experiment:** Three sources, triangulated — (a) multi-annotator agreement on the gold set, with Krippendorff's α and Cohen's κ; (b) intra-rater agreement from Daniel relabeling a held-out sample ≥30 days later, blind to his first labels; (c) the empirical reversal rate on video-reviewed calls in the corpus, which is a lower bound on referee disagreement observable without recruiting anyone.

**Why it matters most:** if the ceiling on contested phrases is, say, in the 70s, then a model in the high 60s on that subset is near-ceiling and 89.1% on an uncontested-heavy distribution means something quite different than it appears to. **No paper in this space reports this.**

### R8 — Perception vs. reasoning error attribution

**Claim:** The dominant error source in rule-grounded priority systems is perception, not rule application.

**Experiment:** Feed **ground-truth structured state** (gold action labels, gold contact events, gold extension onsets) into the rule engine and measure the resulting priority accuracy. That number is the rule engine's ceiling. The gap between it and end-to-end accuracy is perception error; the gap between it and 100% is rule-model error.

**Why it matters:** this decomposition tells anyone building on this work where to spend effort. It costs one extra evaluation run and no one has published it.

---

## 7. System architecture

### 7.1 Overview

```
                          public competition footage (yt-dlp)
                                        |
        +-------------------------------+-------------------------------+
        |                               |                               |
   [S1] apparatus              [S2] participant                  [S5] audio
   lights / score / clock       detect + track + canonicalize     onset detection
   OCR + light-state CV         RTMDet -> RTMPose -> Norfair       log-mel CNN
        |                               |                               |
        |  exchange bounds              +---------------+               |
        |  FREE PRIORITY LABEL          |               |               |
        |  (score-delta oracle)   [S3] body kin.   [S4] blade          |
        |                          2D + 3D SMPL     guard + tip        |
        |                          strip coords     streak recovery    |
        |                          feature block    contact events     |
        |                               |               |               |
        +---------------+---------------+---------------+---------------+
                                        |
                        [S6] appearance stream (optional)
                             V-JEPA 2 / VideoMAE clip features
                                        |
                                        v
                    [S7] PRIORITY RELATIONAL TRANSFORMER
                    per-fencer token streams + relational token stream
                    cross-fencer attention, swap-equivariant by construction
                                        |
                +-----------------------+-----------------------+
                |                                               |
   [S8a] structured state head                      [S8b] direct priority head
   actions, extension onsets, contacts,             end-to-end L/R/None
   tempo boundaries, blade line                     (comparison arm)
                |
                v
   [S9] DETERMINISTIC RULE ENGINE  (FIE t.-articles, per weapon)
        -> call + checkable natural-language justification
                |
                v
   [S10] calibration / abstention / ensemble
         temperature scaling, risk-coverage, selective prediction
```

**The architectural argument in one line:** priority is a **relational** property of two fencers over time, so the model's inductive bias should be relational and temporal, not per-fencer and per-frame. FERA tokenizes per fencer. §7.9 tokenizes the pair.

### 7.2 S0 — Corpus acquisition

**Sources.** Publicly posted competition footage: FIE-affiliated channels, national federation channels, event organizers, and publicly posted club/tournament uploads. `yt-dlp` with a declarative source manifest.

**Required per clip:** video, audio, native frame rate and resolution, source URL, upload date, event name, weapon, and — where derivable — fencer identities.

**Prioritize, in order:**
1. **≥50 fps** sources — required for R4, and probably better for everything else
2. Sources with **visible scoring apparatus** (lights and scoreboard in frame) — required for S1's free supervision. **Prefer channels with a standardized, stable score overlay** — EFC and FIE broadcast feeds in particular, which is the corpus Allez Go's collection pipeline was built on (§3.4). A layout that is identical across an entire playlist makes ROI registration a one-time cost per source instead of a per-event one, and it is the difference between S1 clearing its 97% gate and not
3. Sources with **usable audio** — required for S5
4. **Broadcast footage with replay segments** — see §9.5; replays are a free hard-case oracle
5. Weapon balance: foil primary, sabre for R2, épée for the control

**Store:** never commit video. A content-addressed local cache keyed by `sha256(source_url + start_ts + end_ts)`, with a committed manifest holding URLs, timestamps, and hashes so the corpus is reconstructible by anyone from public sources. This is the same posture FERA took and it is the one that makes the release legal (§9.1).

### 7.3 S1 — The scoring apparatus as free supervision

**This is the highest-leverage idea in this document.** Read it carefully before building anything else.

In foil and sabre, a **double touch** — both fencers' lights on — is exactly the case where right-of-way must be applied. The referee applies it, and then **the score changes.** Which side's score increments *is the referee's call.* Recovering it requires no human labeling at all.

```
PATH A — double light (primary, clean)
  both lights on  ->  referee applies right-of-way  ->  score delta
     red + green            (the decision)              red +1   =>  label LEFT
                                                        green +1 =>  label RIGHT
                                                        no change =>  label NONE (simultaneous)

PATH B — single light, no award (secondary, noisier — see gate below)
  one light on    ->  score does NOT increment for that side
     red only                                           =>  the touch was not awarded
                                                        =>  label RIGHT, *if* the cause was priority
```

**Path B, and why it is gated separately.** Path A only fires on double touches. Mo's pipeline also harvests **single**-light exchanges: one fencer's light comes on and the score does not move, which means the referee did not award it — frequently because the *other* fencer had priority. Those exchanges are currently discarded by S1, and there are a lot of them.

The reason Path B is not simply folded into Path A is that **"light on, no point" is many-to-one.** In Path A, a score change is proof that a priority decision was made — the referee cannot move the score on a double touch without applying right-of-way. In Path B the same observation is produced by at least four different causes, and the detector cannot tell them apart from the light state alone:

| Cause | Is it a priority label? |
|---|---|
| The attack was parried and the riposte was awarded to the other side | **Yes** — this is the signal |
| Foil off-target (white light) — no priority judgment occurred | **No.** Excludable on light colour; sabre has no off-target at all |
| Annulment, or a light that fired after the phrase ended | **No** — must be dropped by the §7.3 confounder handlers |
| Referee halted for a non-touch reason (corps-à-corps, floor, equipment) | **No** — no priority decision exists to recover |

So Path B carries a **structurally higher label-noise rate than Path A, and it must never be averaged into Path A's number.** A single blended 97% figure would hide a noisy half behind a clean half, which is precisely the failure §9.2 exists to prevent. Path B labels are tagged with their path in the schema, gated on their own measured error rate, and — until that gate passes — used only as an auxiliary/pretraining signal, never in the evaluation sets.

**What this buys.** FERA hand-labeled 1,734 clips, an effort that took a nine-year fencer working frame by frame. The score-delta oracle produces the same priority label — the exact `Left / Right / None` target — **at the scale of the entire corpus**, bounded only by how much footage you download and how well the OCR works. Tens of thousands of exchanges is not an unreasonable target.

**Attribution — this is not A1's idea, and the README must say so.** An earlier draft of this section claimed the score-delta *label* was novel on the grounds that FERA used scoreboard changes only to *find* clips. That is true of FERA and false in general: **Jason Mo — the author of Allez Go, the 89.1% baseline in §3.4 — published this exact pipeline** and built his training set with it ([Mo, *Automated data collection from YouTube*][mo]). See §3.4. Claiming it would be an uncited reinvention of the method behind the strongest number A1 is measured against, and an interviewer who reads the Allez Go write-ups will find it.

**What that changes: nothing about the plan, and it strengthens the case for it.** The oracle is now an *independently validated* method with a reported yield — ~8,000 clips in roughly one week of collection — rather than an untested bet. A1's contribution at this layer is not the oracle; it is the **confounder handling, the measured weak-label error rate, and the acceptance gate** below, none of which the prior work reports. Free labels at scale are cheap. Free labels with a defended noise rate are not.

**Implementation.**

| Component | Approach | Notes |
|---|---|---|
| Light state | Small CNN or classical color-blob detection on a registered scoring-box ROI; per-frame `{red, green, white_left, white_right, off}` | Modern sabre has no off-target and therefore no white lights — anything off-target simply does not register. Foil does have white lights, and white-only exchanges are **not** priority cases: exclude them. Verify the actual light semantics per apparatus model before trusting the mapping |
| Score / clock OCR | PaddleOCR or EasyOCR on a registered scoreboard ROI, with temporal smoothing and monotonicity constraints | Scores are non-decreasing within a bout except on annulment. Enforce it and flag violations |
| ROI registration | Detect once per broadcast layout, cache per source; verify with a template match every N frames | Layouts are stable within an event and vary across events |
| Exchange bounding | Backward from light onset to the last "en garde" reset, forward to the score update | Yields the phrase window without human input |

**Confounders that must be handled explicitly, and the failure of each if you do not:**

| Confounder | Failure if ignored | Handling |
|---|---|---|
| **Card penalties** award touches with no phrase | A penalty touch becomes a mislabeled phrase | Detect card graphics; drop the exchange when a score change is not preceded by a light event within the expected window |
| **Annulments** reverse a scored touch | Label is inverted or spurious | Enforce monotonic score; a decrement flags an annulment; drop the exchange |
| **Video review reversals** change the call after the fact | Label reflects the initial call, not the final one | Detect review segments (§9.5) and use the **final** score state. Also **record both** — the disagreement is the R5 signal |
| **Priority (coin-toss) touches** at end of a tied bout | A non-phrase becomes a phrase | Detect the priority indicator; drop |
| **Simultaneous in sabre vs. no-touch in foil** differ in meaning | `NONE` conflates two situations | Record weapon with every exchange; treat `NONE` per weapon in the label taxonomy |
| **OCR errors** | Silent label noise at unknown rate | §9.2 Tier 1: human-verify a random sample; **the measured weak-label error rate is a reported number and a gate** |

**Acceptance gate for S1 (blocks P2) — two gates, reported separately, never blended:**

| Path | Sample | Gate | Consequence of failure |
|---|---|---|---|
| **A — double light** | ≥400 auto-extracted exchanges, human-verified | **≥97%** agreement with the human label, residual errors categorized | Fix the pipeline before training on it. Do not lower the gate; restrict the corpus to layouts that clear it (§12 P1 descope) |
| **B — single light, no award** | ≥400 Path-B exchanges, human-verified, sampled independently | **≥90%** agreement, with the residual broken out by the four causes above | Path B stays an auxiliary/pretraining signal only and is excluded from every train/val/test split used for a reported number. This is a demotion, not a blocker — P2 proceeds on Path A alone |

Both numbers are reported whatever they are. **A measured 84% on Path B is a publishable fact about how much free supervision this sport actually affords**; an unmeasured one is label noise at an unknown rate, and training on that is how a project produces a number nobody can defend.

**Reported measures:**
- `[ ] Path A weak-label agreement with human verification, n=[N]:`
- `[ ] Path B weak-label agreement with human verification, n=[N]:`
- `[ ] Path B yield as a multiple of Path A exchange count:`

These belong in the entry file on day one.

### 7.4 S2 — Participant tracking and canonicalization

**Detection:** RTMDet-L (accuracy tier; RTMDet-Tiny is what FERA used and is the speed tier).
**Pose:** RTMPose-X or RTMPose-L, 2D whole-body.
**Tracking:** Norfair with an IoU + centroid distance metric, matching FERA so replication is possible; ByteTrack as the alternate arm.

**Canonicalization** — the step that silently destroys models if done wrong:

- Assign fencers to `LEFT` and `RIGHT` by **strip position**, not by detection order, using the piste homography from S3.
- Handle the referee, coaches, and spectators entering frame: keep the two tracks whose feet are on the strip and whose motion is strip-parallel.
- **Handle side switches.** Fencers change ends between periods and in some formats. A silent side switch inverts every label after it. Detect via score-side association from S1 and assert consistency.
- **Enforce swap equivariance as a tested property, not a hope.** See §11.6.

**Descope condition:** if tracking identity swaps exceed 2% of exchanges after tuning, add a re-identification step on uniform/lamé appearance before proceeding. Do not train through it.

### 7.5 S3 — Body kinematics

**Two representations, both computed, ablated against each other.**

**(a) 2D feature block — FERA-compatible, for replication.** Reimplement FERA's 101-D vector exactly:

| Group | Dim | Contents |
|---|---|---|
| Static | 49 | normalized joints (24), center of mass (2), pairwise distances (11), joint angles (4), torso orientation (2), arm extension (6) |
| Motion | 52 | first- and second-order finite differences of normalized coordinates and CoM |

This exists so that P2 can replicate their published number on their released features. **Do not improve it in P2.** Replicate first, improve after.

**(b) 3D strip-coordinate block — the improvement.** Following VirtualFencer:

- WHAM (or 4D-Humans / HMR2.0) → 3D SMPL body in camera coordinates
- SAM 2 → segment the piste; extract strip boundary lines
- Homography from the **known 14 m × 1.5–2 m strip geometry** → world coordinates

**Why this is not cosmetic.** In strip coordinates, distance between fencers is *metres*, closing velocity is *m/s*, lunge depth is *metres*. In pixel coordinates these are all confounded with camera zoom, angle, and where in frame the action sits. FERA's stated worry about overfitting to individuals is exactly the shape of a model latching onto camera-correlated appearance. **Physical units are the principled fix**, and the fact that no refereeing system uses them while an adjacent generative-fencing paper already solved the pipeline is the opening.

**Derived relational features** (computed in strip coordinates, per frame):

- inter-fencer distance, closing velocity, closing acceleration
- per-fencer arm extension magnitude and its **first derivative sign change** — extension *onset* is the single most decision-relevant scalar in foil
- lunge / flèche detection: CoM forward velocity, rear-leg extension, foot-off events
- torso lean, blade-arm angle
- who crossed a "committed" threshold first, and by how many milliseconds

### 7.6 S4 — Blade perception

**This is the novel technical contribution.** Both prior systems avoid it and say so. FERA:

> *"FERA currently relies on generic 2D pose estimates that do not capture the blade explicitly."*

**Why it is hard, stated precisely.** A foil blade is ~90 cm long and a few millimetres wide, tapering. At 25–30 fps it can traverse more than a metre between consecutive frames. **At the moment that matters, the blade is not an object in the frame — it is a motion-blur streak.** Detectors trained to find objects find nothing. This is the actual reason nobody has done it.

**The reframe this project makes:** *treat the blur streak as the signal rather than as corruption.* A fast blade leaves a coherent, oriented, low-contrast trace. That trace encodes both the blade's path and its speed. Recovering it is a tractable estimation problem, and it is the part of this project that is genuinely research.

**Four-component design:**

**(1) Guard localization — the anchor.** The guard (foil bell, roughly 9.5–12 cm across; sabre knuckle-bow) is a solid, high-contrast, comparatively slow-moving object. It is trackable with ordinary methods. Detect it as a keypoint via a fine-tuned pose head or a small dedicated detector, and treat it as the blade's origin. **Never try to find the blade without first anchoring the guard.**

**(2) Blade direction estimation — the streak.**

| Method | How | Use |
|---|---|---|
| Temporal-residual line extraction | Frame difference against a short-window median background → residual; Radon or Hough transform constrained to rays originating near the guard | Primary. Handles the fast case, which is the case that matters |
| Learned direction head | Small CNN on a guard-centred crop, regressing blade angle + visible length + a visibility flag; trained on annotated tip/guard pairs | Primary. Handles the slow and partially occluded cases |
| Line-segment detection | DeepLSD / ELSD restricted to the guard-forward half-plane | Fallback and cross-check |
| Point tracking | CoTracker3 seeded on the tip once detected, propagating through blur | Temporal smoothing and gap-filling |
| Video segmentation | SAM 2 with the tip/guard as prompts | Ablation arm; likely to struggle on thin fast structures, and reporting that is useful |

**(3) Synthetic pretraining — the answer to label scarcity.** Blade annotation is expensive; blade *rendering* is not. Composite geometrically-plausible synthetic blades onto real fencing frames with simulated linear motion blur at sampled velocities, sampled lighting, and sampled backgrounds. Pretrain the direction head on synthetic, fine-tune on the real annotated set. **Report the synthetic-only, real-only, and synthetic-pretrained numbers separately** — the size of the transfer benefit is its own small result.

**(4) Contact detection — the fusion.**

> **Vision says who and where. Audio says exactly when. Neither alone is sufficient, and no published system uses both.**

Allez Go substitutes audio for vision. FERA uses vision without blades. A1 fuses them: candidate contacts are proposed where the two blades' estimated segments come within a threshold distance in image space, and are confirmed and precisely timed by an audio onset (§7.7) within a matching window. The output is a **contact event** with a timestamp, an estimated location along each blade, and a confidence.

**Blade module metrics — reported independently of downstream accuracy:**

- `[ ]` tip localization error, median and 95th percentile, normalized by fencer height
- `[ ]` guard tracking success rate across exchanges
- `[ ]` blade visibility rate (fraction of frames where any estimate is produced)
- `[ ]` contact-event detection precision / recall / F1
- `[ ]` contact-event timing error, milliseconds
- `[ ]` all of the above **stratified by blade angular velocity** — the whole point is performance in the fast regime, and an aggregate number hides it

**Descope condition:** if median tip error stays above [threshold set at P4b entry] after the full method ladder, **stop and report it.** "Explicit blade tracking at competition frame rates is not achievable to useful precision with these methods, here is the error-vs-velocity curve showing where it breaks" is a legitimate, citable, honest result and it is exactly the documentation §6 of the canonical spec asked for. Do not spend unbounded time converting a negative result into a positive one.

### 7.7 S5 — Audio

Public competition footage carries audio, and it carries three distinct informative signals:

| Signal | What it gives | Detection |
|---|---|---|
| **Blade contact** — the clang | The precise millisecond of a beat, parry, or block | Spectral flux onset detection → small CNN on log-mel patches, classifying `contact / box-buzz / foot / crowd / speech / other` |
| **Scoring box buzz** | Touch registration timing, independent of and more precise than the light-onset video frame | Narrowband tone detection; the box tone is consistent within an apparatus model |
| **Foot strikes** | Lunge and flèche timing, advance/retreat tempo | Same classifier, separate class |

**Sync discipline:** broadcast audio and video can be offset. Estimate and correct A/V offset per source by cross-correlating detected box-buzz onsets with detected light onsets. **This is not optional** — an uncorrected 80 ms offset is 40% of the decision window.

**Training labels for the audio classifier** come from Tier 2 annotation (§9.2) plus, for the box tone, the light events from S1 — which is again free supervision.

### 7.8 S6 — Appearance stream

An optional third stream capturing what pose discards: blade presence, target-area contact, lamé versus off-target, body-to-body contact, referee gestures.

- Backbone: **V-JEPA 2** (frozen features first; fine-tune only if HPC is available and the frozen arm shows signal) or VideoMAE V2 as the alternate arm.
- Input: fixed-length clip crops centred on the exchange.
- Fusion: late fusion into S7 as an additional token stream.

**Treat this as an ablation arm, not a dependency.** It is the most compute-hungry component and the least interpretable. If it does not earn its place in the ablation matrix, cut it. Say so in the README.

### 7.9 S7 — The priority relational transformer

**Input.** A per-frame token sequence of three parallel streams:

| Stream | Per frame | Contents |
|---|---|---|
| `LEFT` | 1 token | body kinematics (2D block, 3D block), blade state (guard, tip, angle, velocity, visibility) |
| `RIGHT` | 1 token | same |
| `REL` | 1 token | inter-fencer distance and derivatives in strip coordinates, blade-blade minimum distance, contact-event indicator + confidence, audio onset energy, apparatus light state, elapsed time within exchange |

**Architecture.**

```
per-stream input projection  ->  d_model = 256
positional encoding          ->  rotary / ALiBi (relative time, not absolute index)
encoder                      ->  6 layers, 8 heads, FFN 1024, dropout 0.2, pre-norm
                                 self-attention within stream
                                 cross-attention LEFT <-> RIGHT, both -> REL
pooling                      ->  masked mean + learned decision token
heads                        ->  see below
```

Deliberately larger than FERA-MDT (3 layers, 8 heads, 512 FFN, 128-D) because D5 removes the latency constraint and §9.2's weak-label scale removes the data constraint that justified the smaller model.

**Heads (multi-task).**

| Head | Output | Loss |
|---|---|---|
| Action recognition | per-frame multi-label over the §8.1 taxonomy, per fencer | focal BCE (rare-class imbalance is stated in FERA's limitations) |
| Event onset | frame-level regression/classification for extension onset, attack initiation, contact, tempo break | soft-target cross-entropy with temporal tolerance |
| Blade line | 5-way {4, 6, 7, 8, other} — FERA-comparable | cross-entropy |
| **Priority** | `LEFT / RIGHT / NONE` | cross-entropy with label smoothing |
| Justification | see §7.11 | see §7.11 |

Multi-task weighting by learned homoscedastic uncertainty (Kendall & Gal), not hand-tuned constants — with a fixed-weight arm in the ablation to prove the learned weighting earned its place.

**Two properties enforced by construction and verified by test (§11.6):**

1. **Swap equivariance.** `f(swap(LEFT, RIGHT)) == swap(f(x))`. Priority is antisymmetric; a model that can distinguish "left fencer" from "right fencer" by anything other than what they did has a bug and a leak. Enforced by shared per-fencer weights and mirrored augmentation; verified by an assertion test on every trained checkpoint.
2. **Temporal causality is *not* enforced** — D5 permits full bidirectional attention over the phrase, and it should be used. State this explicitly in the README so nobody mistakes the model for a real-time system.

**Training regime.**

1. **Self-supervised pretraining** — masked-token modelling on the full unlabeled pose-stream corpus. There will be far more extracted pose than labeled exchanges; this is where that surplus is spent.
2. **Weak-label training** — the S1 score-delta oracle at full corpus scale.
3. **Gold fine-tuning** — Tier 2/3 fully-labeled exchanges.
4. **Semi-supervised refinement** — confidence-thresholded pseudo-labeling on unlabeled exchanges, with the threshold selected on validation, never on test.

**Internal baselines, all trained under the identical protocol** — this list is not optional, it is what makes the headline number mean anything:

| Baseline | Why it exists |
|---|---|
| Majority class | The floor |
| Hand-written pose heuristic | "The thing everyone would try first," per canonical spec §8 |
| BiLSTM (2-layer, 128 hidden) | FERA's baseline, matched |
| TCN (3-layer, k=3, 128 ch) | FERA's baseline, matched |
| BiFenceNet-style stacked TCN | FenceNet's architecture, adapted to two fencers |
| FERA-MDT reimplementation | 3 layers, 8 heads, 512 FFN, 128-D — the direct comparison |
| **A1-PRT** | This model |

### 7.10 S8/S9 — Structured state and the rule engine

**Two arms, both built, compared.**

**Arm A — direct.** Priority head predicts `L/R/None` end to end. Simple, strong, unexplainable.

**Arm B — rule-grounded.** The model predicts **structured state**; a deterministic program applies the FIE rules to that state.

```
predicted structured state
  - attack_initiated_by:  LEFT | RIGHT | SIMULTANEOUS  + onset frame + confidence
  - extension_onset:      per fencer, frame + confidence
  - contact_events:       [ {frame, taker, type: beat|parry|press|froissement, line, conf} ]
  - tempo_breaks:         [ {frame, fencer, cause: hesitation|withdrawal|step_back, conf} ]
  - arrivals:             per fencer, frame, valid_target (from apparatus)
  - blade_line:           per fencer, per frame
        |
        v
  deterministic rule program (§8), per weapon
        |
        v
  call + rule trace  ->  natural-language justification from the trace
```

**Why Arm B is the contribution.** Its explanations are **derived from the decision path** rather than generated alongside it. A language model asked to justify a classifier's output produces a plausible story that is not causally connected to the prediction. A rule trace is the actual reason. That difference is the whole argument for rule-grounded systems and it should be stated in the README in exactly those terms.

**R8 falls out for free:** feed gold structured state into the same rule engine and the resulting accuracy is the rule engine's ceiling. One extra evaluation run, one result nobody has.

### 7.11 S10 — Calibration, abstention, ensembling

D5 permits everything here. Use it.

- **Calibration:** temperature scaling on validation. Report ECE, MCE, Brier — matching FERA's reported calibration metrics so the comparison is direct.
- **Abstention / selective prediction:** risk-coverage curve; report accuracy at 100%, 90%, 70%, and 50% coverage. **The selective number is the deployment-relevant one** — a referee-calibration tool that abstains on the genuinely ambiguous 20% and is highly accurate on the rest is more useful than one that guesses on everything. No prior system reports this.
- **Ensembling:** seed ensemble (≥5 seeds) plus multi-view where multiple camera angles exist. Report single-model and ensemble separately, always. An ensemble number compared against someone else's single-model number is a dishonest comparison.
- **Test-time augmentation:** horizontal mirror with label swap — free, and a direct check that swap equivariance holds in practice.

---

## 8. The rule model

### 8.1 Action taxonomy

**Foil** — start from FERA's 12 classes so the comparison is exact, then extend. FERA's set: `step forward, step backward, half step forward, half step backward, lunge, flèche, wait, parry, beat, counterattack, fake, hit`. Blade lines: `{4, 6, 7, 8, other}`.

**A1 extensions** (each must be justified by its role in a priority decision, not by taxonomic completeness):

| Added class | Priority relevance |
|---|---|
| `remise`, `redoublement`, `reprise` | Continuations after a failed action — named in canonical spec §8 as a failure category |
| `riposte` (immediate / delayed) | Distinguishing these is a common source of referee disagreement |
| `counter-parry` | Changes who holds priority |
| `point-in-line` (established / broken) | An absolute priority state with its own rule branch |
| `derobement` | Evading a beat while in line preserves priority |
| `stop hit in tempo` vs. `counterattack` | The distinction *is* the call in a large class of contested phrases |
| `absence of blade` | Precondition for several rule branches |

**Sabre** — separate taxonomy, overlapping but not identical. Priority turns on initiation and tempo, not blade contact. Add `preparation`, `attack-in-preparation`, `point-in-line`; drop the blade-line classes (sabre has cuts, and line has different meaning).

### 8.2 The rule program

Implement as a **pure, deterministic, unit-tested function** from structured state to `(call, trace)`. It is the one component in this system with a correct answer independent of any model, so it gets tested like a compiler, not like a model.

- Encode the FIE technical rules for foil priority and sabre priority as an explicit ordered decision procedure, one branch per rule clause, each branch citing its article.
- **Every branch carries a citation.** The trace prints the article. This is what makes the justification checkable rather than persuasive.
- **Uncertainty propagates.** Structured-state inputs carry confidences; the engine propagates them and can return `ABSTAIN` when the deciding predicate is below threshold. This is what feeds §7.11's selective prediction.
- Where the rules are genuinely ambiguous — and they are, which is why referees disagree — the engine returns the ambiguity explicitly rather than picking. **The set of phrases where the rule program itself cannot decide is a result** and should be reported.

**Testing:** property-based tests (Hypothesis) over generated structured states, plus a hand-written table of textbook cases from the rulebook with known correct answers. Target 100% branch coverage on the rule module — this is the one place in the repo where that target is meaningful.

### 8.3 Épée as a negative control

Épée has no priority: first touch wins, and simultaneous touches score for both. There is nothing to find.

**The control:** run the identical pipeline on épée exchanges, using the same score-delta labeling. In épée, a double touch scores for *both* fencers — so the "priority" label is degenerate. Construct the control as: given an épée double, predict which fencer the referee "favoured." **There is no such thing.** Accuracy must be at chance.

**If the model beats chance on épée, the pipeline has a leak** — appearance cues, athlete identity, camera-side bias, or apparatus artifacts — and every foil and sabre number is suspect until it is found. This control is cheap, and it is the single best defense against the "your model learned something spurious" question in a technical interview.

**Run it early — P3, not P7.** A leak found in month one is a bug; a leak found in month six is a rewrite.

---

## 9. Data plan

### 9.1 Sources, legality, release posture

**Source:** publicly posted competition footage only (D4).

**Release posture — follow the precedent already set for this exact footage.** FERA: *"All source videos are publicly available competition recordings; we release only anonymized pose features, labels, and code."*

A1 does the same:

| Released | Not released |
|---|---|
| Derived pose features (2D and 3D) | Raw video, ever |
| Blade keypoint annotations | Audio |
| Action, event, and priority labels | Fencer identities in released artifacts (pseudonymous stable IDs only) |
| Referee justification texts | |
| Fixed fold definitions | |
| A manifest of source URLs + timestamps so the corpus is reconstructible | |
| Code and trained weights | |

**Additional requirements:**

- Identities are pseudonymized in the release but **retained internally**, because athlete-disjoint splits (R3) are impossible without them. Store the identity map outside the repo, in a gitignored local file, with the mapping procedure documented.
- Do not release anything that would enable per-athlete performance profiling of named individuals.
- README states the source, the posture, and the reasoning explicitly. `LICENSE` for code; a separate data-use statement for the benchmark.

### 9.2 The four labeling tiers

**Design principle:** each tier is 3–10× smaller than the one above and 3–10× more expensive per item. Labeling effort goes where the information density is highest, and you stop when the curve flattens rather than at a number chosen in advance.

| Tier | What is labeled | Who / how | Target scale | Cost per item |
|---|---|---|---|---|
| **T0 — Free** | Priority call `L/R/None`, exchange bounds, weapon, event, apparatus state | **Automatic**, from the score-delta oracle (§7.3) | **All extractable exchanges.** Target ≥[N] — bounded by corpus size, not by labeling time | ~0 |
| **T1 — Verify** | Confirm/correct the T0 call; mark exchange-boundary quality; flag confounders | Human, fast pass, target ≤10 s/clip | ~3,000, **stratified**: random sample for the error-rate estimate + all low-confidence T0 + all contested (§9.5) | seconds |
| **T2 — Full** | Per-fencer action labels over the §8.1 taxonomy, extension onsets, contact frames, blade line, tempo breaks | Human, frame-by-frame, custom tool | ~1,500–2,500, **actively selected** (see below) | 1–3 min |
| **T3 — Gold** | Everything in T2, plus **written justification**, plus **per-frame blade keypoints** (guard + tip, both fencers), plus multi-annotator labels | Human, careful, plus a second annotator on a subset | ~300–500, weighted toward contested and rare actions | 5–15 min |

**Active selection for T2/T3 — do not label randomly.** Random labeling wastes the scarce resource on phrases the model already gets. Select by:

1. **Model uncertainty** — highest-entropy predictions under the current best model
2. **Rarity** — actions the §8.1 taxonomy says are underrepresented (FERA names flèche and uncommon blade lines specifically)
3. **Contestedness** — everything mined in §9.5
4. **Disagreement** — cases where the direct head (Arm A) and the rule engine (Arm B) disagree; these are maximally informative about which component is wrong
5. **Coverage** — enforce a floor of examples per athlete, per event, per camera setup, so the athlete-disjoint splits are actually populated

Re-select after each training round. This is an **active learning loop**, and it is what makes a few thousand labels do the work of many more.

**The stopping rule — label until the curve flattens.**

```
After each labeling round of size R, retrain and evaluate on the fixed validation set.
Fit priority accuracy as a function of log(label count).
STOP tier T when:
    the accuracy gain from the most recent DOUBLING of tier-T labels
    is < 0.5 percentage points, with the 95% bootstrap CI on that gain
    excluding a gain of 1.0 pp or more.
Then reallocate the remaining effort to the next tier down, or to corpus expansion.
```

Publish the learning curve. **It is a result in its own right** — "how many referee-labeled exchanges does this task actually need" is a question the field has not answered, and answering it tells the next person whether to spend six months labeling.

**Reported measures:**
- `[ ]` T0 exchanges extracted:
- `[ ]` T0 weak-label error rate, measured on the T1 verification sample:
- `[ ]` T1 / T2 / T3 counts at each stopping point:
- `[ ]` labels-to-saturation, per tier:

### 9.3 Annotation tool

A local tool, built once, used for hundreds of hours. Under-building it is a false economy; over-building it is the classic scope trap. The line:

**Required:**
- Frame-stepping with keyboard shortcuts, variable playback speed, and loop-over-selection
- Two-panel view: full frame + guard-centred crops for each fencer (blade annotation is impossible at full-frame zoom)
- Two-click blade annotation: guard, then tip, per fencer, per annotated frame — with **linear interpolation between annotated frames** and a visual overlay of the interpolated track so errors are obvious
- Action labeling from a fixed taxonomy, bound to number keys
- Event marking (extension onset, contact) bound to single keys with sub-frame nudging
- A free-text justification field for T3
- Autosave, resumable sessions, and an append-only annotation log with timestamps so annotation *time* is itself measurable
- **Blind relabeling mode** — hides prior labels, required for R7's intra-rater measurement

**Explicitly not built:** multi-user accounts, a server, a review workflow, a web deployment, or a queue UI. Local, single-user, file-backed.

**Recommended stack:** Python + PySide6 (native, fast frame stepping, no browser video-seek pain) or a minimal local web app with a `<canvas>` overlay if that is faster to build. Frame access via decord or PyAV with a frame-index cache.

### 9.4 Splits

**Five nested split protocols, all evaluated, reported as a ladder (this is R3).**

| Protocol | Constraint | Purpose |
|---|---|---|
| **S-clip** | 5-fold multilabel-stratified at clip level | Matches FERA. The comparison arm |
| **S-bout** | No bout in both train and test | Matches FERA's end-to-end protocol |
| **S-athlete** | No fencer in both train and test | FERA names this as a limitation. **The honest number** |
| **S-event** | No competition in both train and test | Controls camera setup, venue lighting, broadcast layout |
| **S-both** | Athlete- **and** event-disjoint | The hardest and most honest. **This is A1's headline protocol** |

**Additionally:** a **temporal split** — train on everything before date D, test on everything after — as a check on distribution drift. Fencing rules, timing-box parameters, and refereeing conventions all change over time, and a corpus spanning several years spans some of those changes. Check which fall inside the corpus window and note them in `DATA_STATEMENT.md`.

**The lockbox.** A held-out test set, ~15% of gold-labeled data, **stratified by weapon, athlete, event, and contestedness**, that is:

- generated once, at P2, by a script with a fixed seed, and committed as a fold definition
- **never evaluated against until the pre-registered final evaluation** (§10.3)
- accessed through a CI-enforced guard: the lockbox loader refuses to run unless an environment flag is set, and every access is logged to a committed file

If the lockbox is touched more than once, say so in the README. That disclosure is worth more than the number it protects.

### 9.5 The hard-case benchmark — mined, not hand-picked

Canonical spec §8 asks for the subset "where the referee's call was protested or reversed." Here is how to get it without watching everything.

**Broadcast production selects the hard cases for you.** When a touch is contested, the director replays it, and when a fencer requests video review, the broadcast shows the review and the referee's final decision. Both leave detectable signatures.

| Signature | Detection |
|---|---|
| **Replay segment** | Graphic wipe/transition detection, sudden shot-scale change, on-screen replay bug, slow-motion (optical-flow magnitude drops sharply while scene content continues) |
| **Video review** | On-screen review graphic; the clock stops while the bout does not resume; the referee walks to the monitor; extended dwell on the scoreboard |
| **Reversal** | Score state **before** vs. **after** the review differs from what the initial light + score event implied |

**What this yields, and it is a lot:**

1. **The contested subset** — phrases a referee found hard enough to review. This is the honest hard set, mined automatically at corpus scale rather than curated by hand.
2. **The reversal subset** — cases where a second look changed the call. Rarest and most valuable.
3. **A referee-disagreement estimate for free.** The reversal rate on reviewed calls is an empirical lower bound on how often referees are wrong about phrases they themselves found ambiguous. That feeds R7 **without recruiting a single additional referee.**
4. **Higher-temporal-resolution views.** Slow-motion replay is a high-effective-frame-rate view of exactly the phrase that matters most. That is a genuine data windfall for R4.

**Verify the miner.** Human-verify a sample of detected review/reversal events; report precision and recall. A hard-case benchmark built on an unvalidated miner is not a benchmark.

**Reported measures:**
- `[ ]` contested exchanges mined:
- `[ ]` reversals identified:
- `[ ]` review-detection precision / recall on the verified sample:
- `[ ]` empirical reversal rate among reviewed calls:

### 9.6 The explanation corpus

FERA, explicitly: *"We lack ground-truth textual explanations from referees for direct supervision."* **This dataset does not exist. Building it is the most durable artifact in this project.**

**Format** — every T3 justification is structured, not free prose, so it can supervise a model and be evaluated automatically:

```yaml
exchange_id: <id>
weapon: foil
call: LEFT
rationale:
  attack_initiated_by: LEFT
  initiation_evidence: "arm extension begins at frame 41, 120 ms before RIGHT's"
  intervening_actions:
    - {frame: 58, actor: RIGHT, action: parry, line: 4, successful: false}
  decisive_clause: "attack was not deflected; parry missed the blade"
  rule_citation: "<article>"
  confidence: high            # high | medium | low
  ambiguity_note: "..."       # required when confidence != high
free_text: "Left attacks, right's parry-4 is late and finds no blade,
            attack continues and lands. Point left."
```

**Why structured + free text, both.** The structured fields supervise the rule-grounded model directly and support automatic evaluation. The free text preserves how a referee actually talks, which is what makes the corpus useful to anyone else.

**Confidence and ambiguity are mandatory fields.** A referee who marks 15% of phrases `low` confidence has produced a *better* dataset than one who marks none, and those markings are the direct input to R7.

### 9.7 The human ceiling

**Three independent estimates, triangulated:**

1. **Inter-annotator** — a second qualified referee labels a shared subset (target ≥200 exchanges, oversampled for contested). Report Cohen's κ and Krippendorff's α on the three-way call. Recruiting one referee for a few hours is a much smaller ask than it sounds, and it converts a limitation into a headline result.
2. **Intra-annotator** — Daniel relabels a held-out sample ≥30 days later in blind mode. Self-agreement is an upper bound on inter-referee agreement and requires no one else.
3. **Empirical reversal rate** — from §9.5, free.

**Report every model number against this ceiling.** A model at [X]% on a subset where referees agree with each other [Y]% of the time is a fundamentally different claim than [X]% against an implicit 100%. **No paper in this space does this**, and it is the section a knowledgeable reader will remember.

---

## 10. Evaluation protocol

### 10.1 Metrics

**Primary:** priority accuracy (`LEFT / RIGHT / NONE`), reported **separately** under every split protocol in §9.4, with 95% bootstrap CIs (10,000 resamples, clip-level resampling).

**Secondary:**

| Metric | Why |
|---|---|
| Macro-F1 on priority | `NONE` is rarer; accuracy alone hides it |
| Per-class precision/recall/F1 | The `NONE` class is where the interesting errors are |
| Move-recognition macro/micro/weighted F1, Hamming loss | Direct comparison to FERA-MDT's 0.549 ± 0.018 |
| Blade-line macro-F1 | Direct comparison to FERA's ≈0.38 |
| ECE, MCE, Brier | FERA reports these; match them |
| Risk-coverage AUC; accuracy at 90/70/50% coverage | The selective-prediction result nobody has |
| Blade module metrics (§7.6) | Independently of downstream effect |
| Event timing error (ms) for onsets and contacts | The 200 ms claim in the canonical spec becomes measurable |
| **Accuracy relative to the human ceiling** | §9.7. Report as both raw and ceiling-normalized |

**Explanation quality (R6):** structured-field accuracy against the T3 gold rationale (initiator, decisive clause, cited article) — **not** a text-similarity score. BLEU/ROUGE against a referee's free text measures phrasing, not correctness. Additionally: **human referee rating** of generated justifications on a small sample, blind to whether the explanation is model- or human-written.

### 10.2 Baselines

Every baseline in §7.9's table, trained and evaluated under **identical folds, identical features, identical seeds**. Plus, as external reference points with their protocols stated: Allez Go 89.1%, FERA-LM 77.7% (v1/v2), FERA structured 0.624/0.632 (current), FERA-MDT 0.549 macro-F1, BiFenceNet 87.6% (different task).

**Where FERA's released features and folds permit, run A1's model on their data.** That is the one comparison with no distribution-shift caveat attached, and it is worth more than three comparisons that have one.

### 10.3 Statistical protocol

**Pre-registration.** Before the lockbox is opened, write `EVALUATION_PREREGISTRATION.md` and commit it: the hypothesis set (R1–R8), the primary metric, the primary split protocol (S-both), the comparisons to be made, and the correction procedure. **Commit it, then open the lockbox.** The git history is the timestamp, and it is what converts "I ran a lot of experiments and reported the good one" into a defensible claim.

**Tests:**

| Comparison | Test |
|---|---|
| Two models, same test set | McNemar's exact test on paired predictions |
| Model vs. model across folds | Wilcoxon signed-rank |
| Any accuracy figure | Bootstrap 95% CI, 10,000 resamples, resampled at clip level |
| The full ablation matrix | Holm–Bonferroni across the pre-registered family |
| Effect size | Report alongside every p-value. Report both, always |

**Seeds and variance — revised August 27, 2026. The original "≥5 seeds" rule was well-intentioned and statistically wrong.**

The prior rule was: *every reported number is the mean ± std over ≥5 seeds, varying the weight-init seed.* [Bouthillier et al.][bout] show this is the wrong allocation of a fixed compute budget, in two ways that matter here:

1. **Randomizing *all* sources of variation — weight init, data splits (bootstrap), data order, augmentation order, dropout — yields a *lower* standard error than holding them fixed and varying only the init seed**, and their estimator reached comparable statistical quality at **51× less compute**. Their formulation: *"more variation sources with more splits beats fixed hyperparameters with more seeds."* Varying only the init seed measures the least interesting source of variance and understates the real one.
2. **Five seeds cannot certify a small difference, and neither can twenty.** They recommend a probability-of-outperforming criterion, **P(A > B) ≥ 0.75**, and report that reliably detecting an improvement at that threshold takes **~29 runs** (≈5% false positive, ≈30% false negative). Detecting smaller effects is "impractical" — hundreds of runs.

**The revised rule:**

| Rule | Specification |
|---|---|
| **Randomize, don't fix** | Each run draws a fresh weight init, data order, augmentation order, dropout mask, **and bootstrap split**. Seeds are recorded for reproducibility, not held constant to suppress variance |
| **Report a distribution** | Every headline number is reported as a distribution with a bootstrap 95% CI, not `mean ± std` over identically-seeded runs |
| **Primary decision criterion** | **P(A > B)**, estimated over the randomized runs, reported alongside the effect size. Holm–Bonferroni still applies across the pre-registered family |
| **Single-seed numbers** | Still never reported. That part of the old rule stands |
| **Budget allocation** | Screening then confirmation — see §10.4 |
| **Under-powered contrasts** | Where the observed difference sits inside the noise floor, **report it as under-powered and state the run count required to resolve it.** Do not add seeds chasing significance, and do not report it as a null result |

**That last row is a contribution, not an apology.** "This ablation is under-powered at n=[N]; separating these arms at P(A>B) ≥ 0.75 would require ≈[M] runs" is a more honest and more useful sentence than a mean±std that implies a resolution the design does not have. It is the same move §3.1 makes about FERA's moving number: the protocol is the argument.

**Pairing — use it, but not in the same number.** Bouthillier et al. also discuss paired designs (common random numbers across arms), which reduce the variance *of the difference* when nuisance randomness is shared. That targets a different estimand than full randomization. **Use full randomization for the headline variance estimate; use paired designs only for the final head-to-head confirmations** in §10.4's confirmation stage. Never mix the two into one reported figure, and say which was used for every number.

### 10.4 The ablation matrix

Every row is one pre-registered question. Every row runs under S-both.

**Two-stage design (revised August 27, 2026).** The original plan — 16 rows × 5 seeds = 80 runs — spends the budget uniformly, which per §10.3 buys neither a good variance estimate nor the power to separate close arms. Replace it with **screening → confirmation**:

| Stage | What runs | Budget | Purpose |
|---|---|---|---|
| **S1 — Screening** | All 16 rows × **2 fully-randomized runs** | 32 runs | Locate the arms whose effect is plausibly larger than the noise floor. **No claims are made from this stage** |
| **S2 — Confirmation** | The **2–4 contrasts that carry the paper's claims**, deeply seeded toward the ~29-run guidance, paired where appropriate | ~60–120 runs | The reported numbers. P(A > B) with CIs |
| **S3 — Reported-as-underpowered** | Everything screened but not confirmed | 0 additional | Reported with the observed difference, the CI, and the run count that would resolve it |

**Which contrasts get S2 is pre-registered, not chosen after seeing S1.** Name them in `EVALUATION_PREREGISTRATION.md` before screening runs. On current framing they are almost certainly **A1** (blade stream — R1, the headline), **A9** (weak-label pretraining — the free-supervision claim), and **A13** (R8 perception/reasoning decomposition), with **A3** as the pose-only floor everything is measured against. If S1 surprises you, the pre-registration is what stops you from quietly promoting whichever row came out best.

Total: roughly 90–150 runs against the old 80, and the extra runs buy actual statistical power rather than a tighter estimate of the least interesting variance source. Per §11.8 these are small models on cached features — the increase is affordable.


| # | Ablation | Question |
|---|---|---|
| A1 | − blade stream | R1: does blade perception help? |
| A2 | − audio stream | Does audio help beyond blades, and vice versa? |
| A3 | − blade − audio | The pose-only floor — the Option A model from the canonical spec |
| A4 | − 3D strip coordinates (2D only) | Do physical units help? |
| A5 | − appearance stream | Does S6 earn its compute? |
| A6 | − relational token stream | Does explicit relational modelling beat per-fencer tokens? |
| A7 | − cross-fencer attention | Is the architectural claim in §7.9 real? |
| A8 | − self-supervised pretraining | Does the unlabeled surplus pay off? |
| A9 | − weak-label (T0) pretraining | **Does the free-supervision idea work?** The most important row |
| A10 | − active selection (random labels instead) | Does §9.2's selection strategy earn its complexity? |
| A11 | − synthetic blade pretraining | R1 sub-question |
| A12 | Arm A (direct) vs. Arm B (rule-grounded) | Does grounding cost accuracy, and how much? |
| A13 | gold structured state → rule engine | **R8: the perception/reasoning decomposition** |
| A14 | frame rate: 60/50/30/25/12.5 | R4 |
| A15 | single model vs. 5-seed ensemble | Report both, never conflate |
| A16 | learned vs. fixed multi-task weights | Does the complexity earn its place? |

### 10.5 Failure taxonomy

Every test-set error is categorized. The categories are pre-declared:

- simultaneous / near-simultaneous initiation
- remise vs. riposte confusion
- counterattack in tempo vs. stop hit
- parry judged successful vs. missed (blade contact ambiguity)
- point-in-line establishment or breaking
- attack losing tempo (hesitation, withdrawal)
- occlusion — one fencer blocking the other from the camera
- camera angle degeneracy — action along the optical axis
- motion blur beyond blade-module recovery
- apparatus/label error (a T0 error that survived T1)
- **the rule is genuinely ambiguous** — the gold annotator marked confidence `low`

Report the distribution and **compare it against the human error distribution** on the same clips where both are available. If the model fails on the same categories referees do, that is a finding. If it fails on different ones, that is a bigger one.

### 10.6 Leakage audit

Run **before** the lockbox opens. Every check is a committed test.

| Check | Detects |
|---|---|
| Athlete overlap across folds | The FERA limitation, directly |
| Event/venue overlap | Broadcast-layout shortcutting |
| Near-duplicate exchanges (perceptual hash on keyframes) | The same touch from two uploads |
| Same-bout clips across folds | Bout-level correlation |
| **Épée control at chance** (§8.3) | Any spurious signal at all |
| **Swap-equivariance assertion** on the trained model | Side bias |
| **Apparatus-feature exclusion at inference** | The model reading the answer off the scoreboard. **The score delta is the label — it must never be an input.** This is the single most dangerous leak in this design and it needs an explicit, tested firewall between the S1 label path and the S7 feature path |
| Temporal-split degradation | Distribution drift |

**The apparatus firewall deserves emphasis.** §7.3's free supervision is powerful precisely because the label is visible in the frame. That means a model with unrestricted frame access can read the answer. The light-state feature passed to S7 must be **restricted to the light onsets themselves and truncated before any score update**, and there must be a test that fails if a scoreboard region reaches the model. Get this wrong and every number in the project is worthless. Get it right and it is a good story about a trap you saw coming.

---

## 11. Engineering specification

### 11.1 Repository layout

```
a1-fencing-referee/
├── README.md                     # the artifact. related work, protocol, results, honesty
├── EVALUATION_PREREGISTRATION.md # committed before the lockbox opens
├── DATA_STATEMENT.md             # sources, posture, what is and is not released
├── RESULTS.md                    # generated from run artifacts, never hand-edited
├── LICENSE
├── pyproject.toml                # uv-managed
├── Makefile                      # every command in this doc has a make target
├── .pre-commit-config.yaml
├── .github/workflows/ci.yml
│
├── configs/                      # Hydra. every experiment is a committed config
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
│   ├── corpus/         # yt-dlp acquisition, manifest, content-addressed cache
│   ├── apparatus/      # S1: light state, OCR, exchange bounding, weak labels
│   │   └── firewall.py # the §10.6 apparatus firewall. heavily tested
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
├── tools/annotate/     # §9.3 annotation tool
├── tests/
│   ├── unit/           # every module
│   ├── property/       # Hypothesis: rule engine, geometry, feature invariances
│   ├── integration/    # end-to-end on a tiny fixture corpus
│   ├── leakage/        # §10.6, every check
│   └── fixtures/       # 10 short clips + gold labels, committed
│
├── scripts/            # slurm submission, corpus sync, release packaging
├── notebooks/          # exploration only. never imported by src/
└── data/               # gitignored. content-addressed. manifests are committed
```

### 11.2 Stack

| Concern | Choice | Note |
|---|---|---|
| Language | Python 3.11 | |
| Deps | **uv** + `pyproject.toml`, locked | Fast; matters when the same env is rebuilt on Mac and HPC |
| DL | PyTorch 2.x + **Lightning** | Lightning's MPS/CUDA/multi-GPU abstraction is exactly the D3 problem |
| Config | **Hydra** | Every run is a committed config. Required for the §10.4 matrix |
| Detection/Pose | **RTMDet + RTMPose** via MMDetection/MMPose | FERA-matched. **Wrap behind a `PoseEstimator` protocol** — MM installs are brittle on Apple Silicon, and the alternate arms (Ultralytics YOLO-pose, Sapiens) must be swappable by config |
| 3D pose | **WHAM**, alternate 4D-Humans/HMR2.0 | VirtualFencer's choice |
| Tracking | **Norfair**, alternate ByteTrack | FERA-matched |
| Segmentation / points | **SAM 2** (piste, masks), **CoTracker3** (tip propagation) | |
| OCR | PaddleOCR, alternate EasyOCR | Scoreboard |
| Audio | torchaudio + librosa | |
| Video backbone | **V-JEPA 2**, alternate VideoMAE V2 | Frozen first |
| Video I/O | PyAV + decord, frame-index cache | |
| Acquisition | yt-dlp | |
| Tracking/experiments | **MLflow** (local + HPC-offline-friendly), or W&B offline | Must work with no outbound network on a compute node |
| Data versioning | DVC over the content-addressed cache | Manifests committed, bytes not |
| Tables | Polars + Parquet | Feature tables get large; Parquet columnar reads matter |
| Stats | scipy, statsmodels, custom bootstrap | |
| Testing | pytest + **Hypothesis** | |
| Quality | ruff (lint + format), **mypy --strict** on `src/a1` | |
| Hooks | pre-commit | |
| CI | GitHub Actions | §11.7 |
| Containers | Docker (local), **Apptainer** (HPC) from the same definition | Environment parity is the thing that breaks first when moving Mac→HPC |
| Annotation UI | PySide6 | |

**Pin every version. Commit the lock file. Record the resolved environment in every run's artifacts.** D6 makes reproducibility a deliverable, not a nicety.

### 11.3 Configuration

Hydra, composed. Nothing that affects a result is a command-line flag or a constant in code.

```yaml
# configs/config.yaml
defaults:
  - data: corpus_v1
  - features: [pose2d, pose3d, blade, audio, relational]
  - model: prt
  - training: finetune_gold
  - eval: s_both
  - compute: mac_mps
  - _self_

seed: 0
seeds: [0, 1, 2, 3, 4]        # every reported number is mean ± std over these
run_id: ${now:%Y%m%d_%H%M%S}_${hydra:job.override_dirname}
lockbox:
  enabled: false               # flipping this is a committed, logged event
```

**Rule:** if a number appears in `RESULTS.md`, the exact config that produced it is committed and referenced by `run_id`. No exceptions.

### 11.4 Data schemas

All Parquet, all with explicit schemas, all validated on write (Pandera or an equivalent).

**`clips.parquet`** — one row per source video
`clip_id (sha256)` · `source_url` · `event` · `weapon {foil,sabre,epee}` · `date` · `fps` · `width` · `height` · `has_audio` · `has_apparatus_visible` · `broadcast_layout_id` · `duration_s` · `license_note`

**`exchanges.parquet`** — one row per extracted exchange
`exchange_id` · `clip_id` · `start_frame` · `end_frame` · `weapon` · `bout_id` · `athlete_left_id` · `athlete_right_id` · `apparatus_light_state` · `score_before_l/r` · `score_after_l/r` · `label_t0 {LEFT,RIGHT,NONE}` · `label_t0_confidence` · `is_contested` · `was_reviewed` · `was_reversed` · `label_final` · `label_tier {0,1,2,3}` · `confounder_flags[]` · `split_assignment{s_clip,s_bout,s_athlete,s_event,s_both}` · `in_lockbox`

**`poses.parquet`** — one row per (exchange, frame, fencer)
`exchange_id` · `frame_idx` · `fencer {LEFT,RIGHT}` · `track_id` · `bbox` · `keypoints_2d[K,3]` · `keypoints_3d_strip[K,3]` · `smpl_params` · `pose_confidence` · `estimator_version`

**`blade.parquet`** — one row per (exchange, frame, fencer)
`exchange_id` · `frame_idx` · `fencer` · `guard_xy` · `guard_conf` · `tip_xy` · `tip_conf` · `blade_angle` · `visible_length_px` · `angular_velocity` · `method {learned,streak,lsd,track,none}` · `is_annotated`

**`contacts.parquet`** — one row per detected contact event
`exchange_id` · `frame_idx` · `time_ms` · `taker {LEFT,RIGHT,UNKNOWN}` · `contact_type` · `line` · `vision_conf` · `audio_conf` · `fused_conf` · `is_annotated`

**`annotations.parquet`** — one row per (exchange, annotator, tier)
`exchange_id` · `annotator_id` · `tier` · `call` · `call_confidence {high,med,low}` · `actions_left[]` · `actions_right[]` · `extension_onset_l/r` · `tempo_breaks[]` · `blade_line_l/r` · `justification_structured (json)` · `justification_text` · `ambiguity_note` · `annotation_seconds` · `annotated_at` · `is_blind_relabel`

**`predictions.parquet`** — one row per (run, exchange)
`run_id` · `exchange_id` · `arm {direct,rule_grounded}` · `pred` · `probs[3]` · `calibrated_probs[3]` · `abstained` · `structured_state (json)` · `rule_trace (json)` · `justification_text` · `error_category`

### 11.5 Experiment tracking and reproducibility

**Every run writes an artifact directory** containing: the resolved Hydra config, the git SHA (and a dirty-tree flag — **CI fails a reported run from a dirty tree**), the resolved environment lock, the fold definition hash, the seed, per-epoch metrics, final metrics with CIs, predictions Parquet, and the failure-taxonomy breakdown.

**`RESULTS.md` is generated** by `make results` from the artifact directories. Never hand-edited. A number in the README that no artifact directory produced is a bug, and there is a CI check for it.

**The reproducibility contract, stated in the README:** a reader with the corpus manifest and the released features can rerun `make reproduce` and obtain every number in `RESULTS.md` within stated tolerance. If they cannot, that is a filed issue.

### 11.6 Testing

| Layer | What | Notes |
|---|---|---|
| Unit | Every module | Ordinary |
| **Property (Hypothesis)** | Geometry: homography round-trips; feature invariance to translation/scale/mirror; rule engine over generated structured states | The rule engine is a pure function — test it like one |
| **Rule engine table tests** | Textbook cases from the rulebook, hand-written, with cited articles | Target 100% branch coverage on `src/a1/rules` |
| **Swap-equivariance test** | Assert `f(swap(x)) == swap(f(x))` within tolerance on every trained checkpoint | Runs in CI against a committed tiny checkpoint |
| **Leakage tests** | Every §10.6 check, as a test that fails the build | The apparatus firewall test is the most important test in the repo |
| **Lockbox guard test** | Assert the lockbox loader raises without the explicit flag; assert every access is logged | |
| Integration | Full pipeline on the 10-clip fixture corpus, end to end | Must run in CI in under 10 minutes |
| Determinism | Same seed → same metrics within tolerance, twice | |
| Schema | Every Parquet write validated | |

### 11.7 CI

On every push: ruff, mypy strict, unit + property tests, schema tests, leakage tests, integration on fixtures, swap-equivariance on the tiny checkpoint, dirty-tree check, and a `RESULTS.md`-vs-artifacts consistency check.

Nightly (when HPC is available): a small-scale training run to catch silent pipeline breakage.

### 11.8 Compute plan (D3)

**Phase 1 — Mac only. This covers more than it sounds like.**

| Workload | Mac viability | Note |
|---|---|---|
| Corpus acquisition | ✅ | Network- and disk-bound |
| Apparatus / OCR / weak labels | ✅ | CPU, embarrassingly parallel |
| 2D pose extraction | ✅ **but slow** | RTMPose-M on MPS. This is the long pole. Make it **resumable, content-addressed, and incremental** and run it continuously in the background from week 1. Never re-extract |
| FERA replication on their released features | ✅ **easily** | Their features are already computed. A 3-layer transformer over 101-D sequences trains in minutes on CPU |
| PRT training on kinematic features | ✅ | This model is small. Kinematic-only training is genuinely a laptop workload |
| Audio classifier | ✅ | Small |
| Annotation | ✅ | |
| Rule engine, evaluation, statistics | ✅ | |
| 3D pose (WHAM) at corpus scale | ⚠️ | Feasible but slow. Start with the gold subset |
| Blade detector training | ❌ | Needs a real GPU |
| Synthetic blade pretraining | ❌ | Needs a real GPU |
| Video backbone (S6) fine-tuning | ❌ | Needs a real GPU |
| The full 16-row × 5-seed ablation matrix | ❌ | Not the individual runs — the *volume* |

**So: P0 through P3 are fully Mac-viable, and they produce R3, R4, R7, and the épée control.** That is four results before HPC is needed, including two of the more distinctive ones.

**What the GPU is actually for.** Four things, and only four: **blade detector training** (P4), **synthetic blade pretraining** (P4), **optional video-backbone work** (P5/S6, droppable per Q2), and **the volume of the ablation matrix** (P4–P8). The first two are *capability* — a Mac cannot do them. The fourth is *throughput* — a Mac could, given weeks. Everything else in this system runs locally. **Without any GPU at all, P0–P3 still ship R3 (the protocol ladder), R4 (the frame-rate curve), the épée negative control, the FERA replication, and the first component of R7** — four defensible results before a GPU is needed. R2 (cross-weapon transfer, P7) and R5 (hard cases, P8) sit *after* the GPU phases in the current §12 order, but neither is GPU-bound in itself: **if access fails permanently, resequence P7 and P8 ahead of P4 and ship them on kinematic features.** What is lost without a GPU is R1 — blade perception — which is the headline contribution and the reason §0 chose Option B.

---

#### Phase 2 — Access. Three asks, one email, week 1.

**The eligibility fact that reorganizes this whole section:** *(researched Aug 27, 2026)*

> **Every major research-compute program excludes undergraduates as PI.** NSF ACCESS: *"Undergraduate students are not eligible to be PIs."* AWS Cloud Credit for Research: graduate/postgraduate/PhD only. Google Cloud Research Credits: faculty/PhD/postdoc, and explicitly *"Graduate students are not eligible."* NVIDIA's Academic Grant Program is faculty-only **and currently closed to new applications.**

So the compute-grant route and the YCRC route **share a single dependency: a faculty sponsor.** They are not independent fallbacks for one another, and the original §11.8 was wrong to imply otherwise. **The faculty email is the highest-leverage hour in this project's setup**, and it should make all three asks at once:

| Ask | What it costs the sponsor | What it returns | Turnaround |
|---|---|---|---|
| **YCRC account with `gpu` partition access** | An endorsement | Free compute on standard partitions | Case-by-case |
| **[NSF ACCESS "Explore" allocation][access]**, sponsor as PI | **An abstract. ~30 minutes** | **400,000 credits**, 12-month allocation | **~2 weeks** |
| Being listed on either as a project participant | Nothing further | — | — |

**ACCESS Explore is the best value on this page and it was missing from v1.0.** Abstract-only, two-week review, and the credits dwarf what this project needs. Note that all ACCESS tiers **release half the credits up front and the remainder after a progress report** — plan the first milestone accordingly. [NAIRR Pilot][nairr] is a secondary option (3-page proposal, monthly cycle) but its undergraduate eligibility is unclear — verify before spending effort.

**The one thing obtainable alone, today:** [Azure for Students][azure] — **$100, 12 months, no credit card, .edu verification only.** ⚠️ **Unverified: whether the student credit can provision GPU VM SKUs.** Student subscriptions frequently lack GPU quota by default and quota requests on free tiers are often denied. Claim it, then **test GPU provisioning immediately** and do not build the plan on it until that test passes.

**Do not block on any of this.** §12's phase order is arranged so late access costs sequencing, not results.

---

#### Phase 3 — The paid fallback, if every sponsored route fails

**This is comfortable, not desperate. Cost is not the binding constraint on this project — experimental design and feature caching are.**

v1.0 quoted H100 rates (≈$3.29/hr) and "a few hundred GPU-hours," which anchored the budget roughly **20× above the correct tier.** The workloads here are a small detector, one pretraining run, and a pile of small-model runs on cached features. Current rates *(getdeploying, 16 providers, Aug 26 2026)*:

| Tier | GPU | Rate | Note |
|---|---|---|---|
| **Interruptible** | RTX 4090 | **$0.14/hr** (Vast.ai) | **The right tier.** Spot runs 45–67% under on-demand |
| Interruptible | RTX 4090 | $0.17/hr (Novita) | Second source |
| On-demand, cheapest | RTX 4090 | $0.26/hr (Vast.ai) | |
| On-demand, median | RTX 4090 | $0.43/hr across 14 providers | Down ~14% in 90 days |
| Mid-tier, for S6 only | L40S / A100 40GB | $0.99–2.10/hr | Only if the video backbone survives Q2 |

**Interruptible is not a compromise here — it is the correct match.** The ablation is a pile of short, independent, restartable runs, which is the ideal preemptible workload. Vast.ai pauses rather than deletes on preemption, and data remains transferable. **Checkpoint every run to durable storage from inside the training loop.**

**Budget, at the revised §10.4 run count:**

| Item | Estimate |
|---|---|
| Screening + confirmation runs (~90–150 small-model runs on cached features) | **$30–60** at $0.14–0.26/hr |
| Blade detector training + synthetic pretraining | Included above; pretrain **once**, checkpoint, reuse across all arms |
| Optional S6 video-backbone probing on L40S | $50–100, only if Q2 keeps it |
| **Total** | **Well under $150**, against a $300 ceiling |

**Cost traps that have burned people, all verified:**

- **Vast.ai bills storage while an instance is stopped.** *"Storage charges continue even when instances are stopped. Delete instances completely to cease storage billing."* Delete, don't stop.
- **Vast.ai charges bandwidth in both directions at host-set rates.** A cheap GPU behind expensive egress is a net loss — check the host's bandwidth rate, not just $/hr.
- **RunPod volume storage costs *more* idle than running**: $0.20/GB/mo idle vs $0.10/GB/mo active.
- Vast.ai is a heterogeneous marketplace. For a thin-blade detector where dataloading may bottleneck, a cheap GPU on a slow disk can be slower end-to-end than a pricier one. Benchmark one run before committing a batch.
- Lambda has **no spot tier** but also **no egress fees** — worth it only for a long uninterrupted run.

**Free tiers worth wiring up regardless of what else lands:**

| Platform | Offer | Verdict |
|---|---|---|
| **[Kaggle][kaggle]** | **30 GPU-hr/week free**, P100 16GB or T4×2, 12 hr/session, 20 GB persisted | **Best free option.** Genuinely usable for real training |
| **[Modal][modal]** | **$30/mo free credits**, serverless, scriptable batch | Good fit for fire-and-forget ablation runs |
| Lightning AI | 15 credits/mo (~22 T4-hr), persistent storage | Short runs; useful as a persistent IDE |
| Colab Free | T4, 12 hr cap, ~90 min idle disconnect, **no persistence** | Interactive only. Not for training runs |

⚠️ **Persistence is the trap on all free tiers** — Colab and Kaggle wipe the VM. Checkpoints and result rows must be written to durable storage from inside the loop, or an interruption costs the run. *(Colab compute-unit burn rates are deliberately unpublished by Google and third-party figures conflict; do not plan around them.)*

---

#### Phase 4 — Method-level reduction. Do these regardless of which phase you land in.

**These matter more than the provider choice.** In rough order of leverage:

1. **Cache backbone features once (biggest win).** If the ablation varies heads/losses and not the backbone, extract features **once** and have every run read tensors. This is [V-JEPA 2's own protocol][vjepa] — *"we freeze the encoder weights and train a task-specific 4-layers attentive probe"* — so it also makes results directly comparable to the paper. ⚠️ **Real tradeoff for this task:** caching kills stochastic augmentation, and for a thin fast-moving blade, motion-blur and scale augmentation are likely load-bearing. Mitigation: cache **K=3–5 pre-augmented variants** per clip and sample among them. Budget disk for it.
2. **Pretrain on synthetic once, checkpoint, reuse.** Never re-run pretraining per ablation arm.
3. **Prefer an attentive probe over LoRA for S6.** PEFT saves optimizer/gradient memory, not forward FLOPs. Probing on frozen features is cheaper *and* is the published protocol. Reach for LoRA only if probing underperforms.
4. **Resolution is the dominant cost knob for the video backbone.** V-JEPA 2 reports an **8.4× GPU-time reduction** from progressive-resolution training. Blade work likely needs spatial resolution more than temporal depth — ablate that early and cheaply (it is A14-adjacent).
5. **bf16 mixed precision everywhere on Ampere+.** 1.5–5.5× over fp32, full dynamic range, no GradScaler. Enable TF32 for matmuls. Disable autocast around `torch.linalg` ops.
6. **Gradient checkpointing: video backbone only.** ~5× activation-memory savings at **~30% slower** — a memory tool, not a speed tool, and not worth it for the small detector.
7. **Use [ASHA][asha] for hyperparameter *search*, never for ablation arms.** It reports ~10–28× speedups by killing unpromising configs early — but truncating ablation arms biases results toward fast-converging configs. Tune hyperparameters with it, then run every ablation arm to completion.

**Cost ledger.** If any paid path is used, keep a per-experiment cost ledger in `RESULTS.md`. It costs nothing to record and "the full result set cost $47 on interruptible consumer GPUs" is a good sentence to be able to say.

---

### 11.9 Definition of done

The project is done when every one of these is true:

1. Every claim R1–R8 has a result — **including the negative ones**
2. Every number in `RESULTS.md` traces to a committed config and an artifact directory
3. `EVALUATION_PREREGISTRATION.md` predates the lockbox access log
4. Every §10.6 leakage check passes, and the épée control is at chance
5. The released benchmark loads and evaluates from a clean checkout with `make reproduce`
6. The README states, for every published number cited, the version and the protocol
7. The failure taxonomy is reported and compared against the human error distribution
8. The human ceiling is measured and every model number is reported against it
9. The metrics ledger in `profile/entries/a1-fencing-referee.md` has no unfilled checkbox for a completed phase
10. **`make figures` regenerates every README figure from committed artifacts**, and the README contains the split ladder, the ceiling band, and at least one qualitative example with its rule trace (§11.10)

---

### 11.10 Visualization — required, and where the line is

*Added August 27, 2026, resolving an ambiguity in D2.*

`src/a1/viz/` appears in §11.1 and had no specification. D2's "no UI" was written to ban a **product** — a hosted service, accounts, uploads, a deploy someone else depends on. It was never meant to ban **pictures**, and reading it that way would damage the project in three concrete ways.

**The test for anything in this category: who does the interface serve?**

| Serves | Verdict | Examples |
|---|---|---|
| **You, locally** | **Required** | Debug overlays, the §9.3 annotation tool, leak inspection |
| **The reader of the README** | **Required** | Result figures, qualitative examples, rule traces |
| **A stranger, over the network** | **Out of scope (D2)** | Hosted demo, upload flow, accounts, any deploy |

#### 11.10.1 Debug visualization — you cannot verify this system numerically

**This is the load-bearing argument.** A tip-error of `[X]` px is not checkable by inspection. An overlay of the predicted blade track on the source clip shows immediately whether the detector is following the blade or locking onto the opponent's forearm — a failure mode that produces *plausible* error numbers and wrong tracking. The same holds for exchange bounding, pose association, and contact events.

**Required renderers, all writing to video or image files — no interactive app:**

| Renderer | Shows | Catches |
|---|---|---|
| `viz.overlay.blade` | Predicted guard/tip per fencer, interpolated track, confidence | Tracking the wrong object; drift; occlusion failure |
| `viz.overlay.pose` | Skeletons with stable track IDs and colours | Identity swaps at crossings — silent and corrupting |
| `viz.overlay.exchange` | Exchange bounds, light onsets, score-update frame | §7.3 bounding errors; Path B miscategorisation |
| `viz.overlay.contact` | Detected blade-blade and blade-target contacts, with audio onsets aligned | S5 fusion errors; A/V offset |
| `viz.attention` | S7 attention or saliency over the frame | **The apparatus leak (R-2)** — see below |
| `viz.failure` | Sampled clips per §10.5 failure category | Whether a taxonomy bucket is one failure or five |

**`viz.attention` is a safety requirement, not a nicety.** §10.6 calls the apparatus leak *"the single most dangerous leak in this design"* and defends it with a feature-path firewall and the épée control. Both are necessary and neither is sufficient: a firewall tests what you *thought* to exclude, and the épée control is a single aggregate number that can pass while a subtler shortcut operates. **Looking at where the model attends is the check that catches what the other two miss.** Run it at P3 and again whenever a feature stream is added.

#### 11.10.2 Figures for the README — D6 requires them in effect

D6 commits to full public release and §11.9 makes the README the artifact. A right-of-way paper with no pictures is materially weaker than one where the reader sees the thing happen.

**Required, generated by `make figures` from committed run artifacts — never hand-drawn, never hand-edited:**

- The **split ladder** (R3): accuracy across S-clip → S-both with CIs. *The single most important figure in the project.*
- The **frame-rate curve** (R4), and the **error-vs-angular-velocity curve** (R1/P4b)
- **Contested vs. uncontested** accuracy (R5), and the **human-ceiling band** (R7) drawn as a horizontal region on the accuracy axis — this is what makes every other number readable
- **Learning curves** per labeling tier (§9.2's saturation result)
- **Confusion matrices** per weapon; **calibration/reliability** plots (S10)
- **Qualitative examples**: N phrases showing frames, the call, the confidence, and — for Arm B — the rule trace. Include failures, not only successes

#### 11.10.3 The rule-trace renderer

§7.10's rule engine emits a trace with article citations. Render it as a readable timeline — extension onset, contact, tempo break, the article applied, the resulting call — beside the clip.

This is R6's most legible output and the clearest single artifact the project produces: *"the model said LEFT, and here is the rule and the frame it applied it at."* FERA's contribution was written justifications; a rendered trace is the visible form of the same thing.

#### 11.10.4 Constraints, so this does not become the project

- **Static outputs only.** Files on disk: MP4, PNG, SVG. No server, no browser app, no callbacks.
- **Deterministic and regenerable.** `make figures` reproduces every figure from committed artifacts. A figure that cannot be regenerated does not go in the README.
- **matplotlib for plots; OpenCV or PIL for overlays.** No plotting framework beyond that, no JS.
- **Timebox: 2 days total across the project.** Debug renderers are written when the stage they debug is written, not up front.
- **Not in CI**, except a smoke test that every renderer runs on the fixture corpus without raising.

**Descope:** if the timebox is exceeded, cut §11.10.2's optional figures. **Never cut §11.10.1's blade, pose and attention overlays** — those are debugging infrastructure, and cutting them means shipping numbers you could not check.

---

## 12. Phases

Each phase has **entry criteria**, **exit criteria**, and a **descope condition**. A phase is not complete until its exit criteria are demonstrably met — not "mostly working."

### 12.0 Two tracks — the default is to run everything that does not need a GPU

*Restructured August 27, 2026.* The original order implied P4 (blade perception) came before P5–P8 and gated them. **It does not.** Every phase except blade-detector training enters on P3 exit and runs on a Mac. The phase numbers below are retained — the rest of this document references them — but they are **not an execution order.**

| Phase | Track | GPU? | Delivers |
|---|---|---|---|
| **P0** Foundations | **A** | No | Repo, tooling, annotation tool, sponsor email |
| **P1** Free supervision | **A** | No | T0 corpus, Path A + Path B labels |
| **P2** Replication | **A** | No | Harness validated against FERA |
| **P3** Protocol result | **A** | No | **R3, R4**, épée control |
| **P4a** Blade data | **A** | No | Blade keypoint annotation, synthetic generator |
| **P5** Audio fusion | **A** | No | Audio contact detection, A2/A3 |
| **P6** Rules and explanations | **A** | No | **R6, R8**, explanation corpus |
| **P7** Cross-weapon transfer | **A** | No | **R2** — the result nobody has |
| **P8** Hard cases, ceiling, release | **A** | No | **R5, R7**, benchmark release |
| **P4b** Blade detector training | **B** | **Yes** | **R1** — the headline |
| *(S6 video backbone, ablation volume)* | **B** | **Yes** | A5, matrix throughput |

**The rule: run Track A to completion. Do not wait on the cluster for anything.**

Track A alone delivers **R2, R3, R4, R5, R6, R7 and R8** — seven of the eight contributions in §6, the released benchmark, the explanation corpus, and the épée control. That is a complete, publishable, defensible project. Track B adds **R1**, which is the headline and the reason §0 chose Option B, but it is an *addition to a finished system*, not a prerequisite for one.

**Ordering within Track A after P3.** P5, P6, P7, P8 and P4a are mutually independent — all enter on P3 exit. Recommended order, by value per unit effort:

1. **P4a first.** Blade annotation is the slowest labeling in the project and it is the only Track A work that *directly* shortens Track B. Doing it while waiting means the day access lands, you train — you do not start annotating.
2. **P7**, because R2 (cross-weapon transfer) is the cheapest genuinely novel result on the list.
3. **P6**, because R8 and the explanation corpus are the most distinctive artifacts.
4. **P5**, then **P8** last — P8 opens the lockbox and should come after everything that might change a model.

**What changes if access never arrives.** Nothing about Track A. The README leads with the protocol ladder (R3), the hard-case benchmark (R5), the human ceiling (R7) and cross-weapon transfer (R2), and states plainly that blade perception is specified, its data is collected, and it is unrun for want of compute. **That is an honest and complete project.** Per §3.4's framing, the protocol *is* the argument — it never depended on the blade.

---

### P0 — Foundations

**Entry:** none.

**Do:** repo scaffold per §11.1; uv env; Hydra config skeleton; Parquet schemas + validators; CI green; the 10-clip fixture corpus; the annotation tool (§9.3); `profile/entries/a1-fencing-referee.md` created from `_TEMPLATE.md` with **every §15 measure pre-written as an empty checkbox**; a row added to `reference/entry-placement.json`; **the faculty-sponsor email sent** (§11.8).

**Exit:**
- CI green on an empty pipeline
- `make test` passes including property tests on a stub rule engine
- The annotation tool can label a fixture clip end to end and write a valid `annotations.parquet`
- The entry file exists with pre-written empty measures — per `build-plan.md` §7, this is non-negotiable and takes 20 minutes

**Descope:** none. This phase is not optional and it is not long.

> **The sponsor email is the only item here with external latency.** Send it in P0, not later. Everything else in Track A proceeds regardless of the answer, which is exactly why it should be in flight from day one rather than blocking anything.

---

### P1 — Free supervision

**Entry:** P0 exit.

**Do:** corpus acquisition with the source manifest; apparatus light-state detection; scoreboard/clock OCR; exchange bounding; the score-delta oracle; **every confounder handler in §7.3**; the T1 verification pass on a random sample of ≥400.

**Do, additionally:** the **Path B** single-light extractor (§7.3) and its independent T1 verification sample of ≥400.

**Exit:**
- `[N]` exchanges extracted with T0 Path A labels, across ≥[M] events, all three weapons
- **Path A weak-label agreement with human verification ≥ 97%**, with residual errors categorized
- **Path B agreement measured and reported**, with the residual broken out by cause; ≥90% promotes Path B to training use, below that it stays auxiliary-only
- Path A and Path B agreement reported as **two numbers, never blended**
- Confounder handlers demonstrably firing (card, annulment, reversal, coin-toss) with counts reported
- The **apparatus firewall** (§10.6) implemented and its test passing

**Yield sanity check.** ~8,000 clips in roughly one week is the published precedent (§3.4). If P1 is producing an order of magnitude less than that, the bottleneck is ROI registration or source selection, not the method — revisit §7.2 before revisiting §7.3.

**Descope:** if OCR agreement cannot reach 97% on some broadcast layouts, **restrict the corpus to layouts where it can** and report coverage. A smaller clean corpus beats a larger noisy one. Do not lower the gate. Path B failing its gate is **not** a descope trigger — it is a reported result and P2 proceeds on Path A alone.

---

### P2 — Replication

**Entry:** P1 exit. **This phase exists to prove the evaluation harness is correct before it is used to make claims.**

**Do:** obtain FERA's released features, labels, and folds; reimplement their 101-D feature block; reimplement FERA-MDT, BiLSTM, TCN to their stated hyperparameters; run their protocol; run A1's own pose pipeline and compare extracted features against theirs on overlapping footage where possible; generate and commit the lockbox fold definition.

**Exit:**
- FERA-MDT reimplementation reproduces their reported macro-F1 (0.549 ± 0.018) **within their stated variance**, or the discrepancy is characterized and documented
- The current-version structured-classifier number (0.624 / 0.632) is reproduced or the gap explained
- A1's own feature extraction is validated against theirs
- Lockbox generated, committed, and guarded; the guard test passes

**Descope:** if the released artifacts are insufficient to replicate, **that is a reportable finding** ("the released benchmark does not permit replication of the reported number because X"). Proceed with the internal reimplementation and say so plainly in the README. Do not silently skip this phase — a replication attempt that is documented, even when it fails, is worth more than one that never happened.

---

### P3 — The protocol result

**Entry:** P2 exit. **Mac-only. This is the first phase that produces novel results.**

**Do:** build all five split protocols (§9.4); train the PRT on kinematic features only; evaluate the full split ladder; run the **épée negative control**; run the frame-rate ablation (A14); run every leakage check; measure intra-annotator agreement on a blind-relabel sample.

**Exit:**
- **R3 delivered:** the accuracy gap between S-clip and S-both, quantified with CIs
- **R4 delivered:** the frame-rate curve
- **Épée control at chance.** *If it is not, stop everything and find the leak.* This is a hard gate
- Every leakage check green
- Intra-annotator agreement measured (first component of R7)
- Kinematic-only priority accuracy under S-both, with CIs, reported against every published number **with protocols stated**

**Descope:** if S-both accuracy is near chance, the task may not be learnable from body kinematics alone at this data scale — which is itself an argument for P4b and should be reported as the motivation for it, not hidden.

---

### P4a — Blade data and synthetic generation · **Track A, no GPU**

**Entry:** P3 exit. **Mac-viable. Do this while waiting on cluster access — it is the highest-value thing you can do with the wait.**

Splitting P4 is the single change that makes a GPU delay cost almost nothing. Blade keypoint annotation is the slowest human work in the project and needs no compute at all; the synthetic generator is a rendering problem, not a training one. Both are pure prerequisites for P4b.

**Do:** per-frame blade keypoint annotation (guard + tip, both fencers) on the T3 subset via the §9.3 tool, with sparse annotation + interpolation; **the synthetic blade generator** — rendered blades over real backgrounds at realistic angular velocities and blur, with the parameter sweep validated visually; guard localization by classical means where it works; the labeled velocity strata that P4b's metrics require; the annotation-time ledger.

**Exit:**
- T3 blade keypoints complete on the target subset, with **annotation minutes recorded** (this is an R-8 mitigation and a reportable number)
- Synthetic generator produces a corpus at a **declared, validated distribution of angular velocities**, spanning the range measured in real footage
- **Velocity strata defined and populated**, so P4b's error-vs-velocity curve has its bins before training starts
- Blind-relabel sample collected for intra-annotator blade agreement

**Descope:** if blade annotation proves slower than §9.2's estimate, annotate **fewer frames per exchange across more exchanges** (interpolation covers the gap) rather than fewer exchanges. Coverage of the velocity range matters more than density within a clip.

---

### P4b — Blade detector training · **Track B, GPU-gated**

**Entry:** P4a exit **and** GPU access (HPC per §11.8 Phase 2, or the paid fallback per Phase 3). **This is the only phase in the document that cannot start without a GPU.**

**Do:** synthetic pretraining (once — checkpoint and reuse across every arm); the four-method direction ladder (§7.6); CoTracker3 propagation; blade feature block; A1/A3/A11 ablations under §10.4's screening→confirmation design.

**Exit:**
- Blade module metrics reported, **stratified by angular velocity** using P4a's bins
- **R1 delivered:** paired comparison, pose+blade vs. pose-only, identical folds and seeds, with McNemar's test — **in whichever direction it lands**
- The synthetic-pretraining benefit quantified separately

**Descope:** the §7.6 stop condition. Report the error-vs-velocity curve and the negative result. **This is a legitimate ending for this phase** and it satisfies exactly what canonical spec §6 asked for.

**If access never arrives:** P4a's artifacts still ship. The blade annotation set and the synthetic generator are releasable on their own, and "here is the annotated blade-keypoint corpus and the generator; the detector is specified in §7.6 and unrun for want of compute" is an honest README section. It also makes the work trivially resumable by you later or by anyone else.

---

### P5 — Audio fusion

**Entry:** P3 exit. **Track A, Mac-viable.**

**Do:** A/V sync estimation and correction; onset detection; the log-mel event classifier; vision-audio contact fusion; ablations A2, A3.

**Exit:**
- Per-source A/V offset estimated and corrected; residual offset reported in ms
- Audio event classifier metrics per class
- Contact-event timing error in ms, vision-only vs. audio-only vs. fused
- A2/A3 ablation results

**Descope:** if broadcast audio is too noisy in most of the corpus, restrict audio features to the subset where onsets are detectable and report coverage. Partial coverage is a usable feature with a mask, not a failure.

---

### P6 — Rules and explanations

**Entry:** P3 exit. **Track A, Mac-viable.** Independent of P4b and P5 — do not wait on either.

**Do:** the full §8.1 taxonomy; the deterministic rule program with article citations; the structured-state heads; the rule trace → justification generator; T3 explanation corpus collection; ablations A12, **A13**.

**Exit:**
- Rule engine at 100% branch coverage with table tests passing
- **R8 delivered:** gold-state → rule-engine ceiling, and the perception/reasoning decomposition
- **R6 delivered:** explanation-supervised vs. not, on call accuracy
- Explanation quality: structured-field accuracy plus a blind human rating on a sample
- The explanation corpus exists in the §9.6 format, with confidence and ambiguity fields populated

**Descope:** if the T3 explanation corpus is smaller than the R6 experiment needs, **release the corpus anyway** and report R6 as underpowered with the observed effect size and CI. The corpus is the durable artifact; the experiment is one use of it.

---

### P7 — Cross-weapon transfer

**Entry:** P3 exit, plus sufficient sabre corpus. **Track A, Mac-viable** — R2 is the cheapest novel result in the document and it does not need a GPU.

**Do:** sabre taxonomy and rule branch; foil-trained model evaluated zero-shot on sabre; sabre-trained model for the gap; the épée control re-run at full scale; per-weapon failure taxonomies.

**Exit:**
- **R2 delivered:** the zero-shot foil→sabre gap with CIs, plus the gap to a sabre-trained model
- Per-weapon failure taxonomies compared — *which* failures transfer is more interesting than *how many*
- Épée at chance at full scale

**Descope:** if sabre corpus with visible apparatus is too thin for training, report the zero-shot transfer number alone. **That is still the result nobody has**; the sabre-trained comparison is the bonus.

---

### P8 — Hard cases, ceiling, release

**Entry:** P3 exit; ideally all other Track A phases complete. **Track A, Mac-viable.** Run P8 last within Track A — it opens the lockbox, so nothing that could change a model should follow it. **Do not hold P8 for P4b:** if blade results arrive later, they are a documented second lockbox access, disclosed per §9.4.

**Do:** the review/replay miner (§9.5) and its verification; the contested and reversal benchmarks; the second-annotator study; the reversal-rate ceiling estimate; the full failure taxonomy; **pre-registration committed**; **lockbox opened once**; benchmark packaged and released; README written.

**Exit:**
- **R5 delivered:** contested vs. uncontested accuracy gap
- **R7 delivered:** all three ceiling estimates, triangulated, with κ and α
- Miner precision/recall verified and reported
- `EVALUATION_PREREGISTRATION.md` committed **before** the lockbox access log entry
- Benchmark released; `make reproduce` verified from a clean checkout
- README complete: related-work table with versions and protocols, all results, all negative results, the failure taxonomy, the ceiling, and an explicit limitations section

**Descope:** if a second referee cannot be recruited, R7 rests on intra-annotator agreement plus the empirical reversal rate. Say so. Two of three estimates is still two more than anyone else has published.

---

## 13. Risk register

| # | Risk | Severity | Mitigation | Descope |
|---|---|---|---|---|
| R-1 | **Not beating 89.1%** | High to the ego, low to the project | §3.5: 89.1% is on an unstated protocol in a student journal, weapon unspecified. A1's claim is *protocol-matched* comparison plus results nobody else has | Lead the README with R3/R5/R7 — the protocol, the hard cases, the ceiling. Report the accuracy honestly in the table where it belongs |
| R-2 | **The apparatus leak** — model reads the score off the frame | **Catastrophic** | §10.6 firewall, tested. Épée control catches it. Build the firewall in P1, not later | None. This must be right |
| R-3 | Blade tracking does not work well enough | Medium | §7.6 method ladder, synthetic pretraining, velocity-stratified metrics | Report the negative result with the error-vs-velocity curve. Canonical spec §6 already anticipated this |
| R-4 | HPC access denied or slow | **Medium → Low** | §11.8 Phase 3: P0–P3 are Mac-viable and produce five results; the paid fallback is **well under $150** on interruptible consumer GPUs, not "a few hundred dollars" | Vast.ai interruptible 4090 at $0.14–0.26/hr, plus Kaggle's 30 free GPU-hr/week. The budget is genuinely not the constraint |
| R-4b | **No faculty sponsor materializes** | **Medium — and this is the real access risk** | Every research-credit program (ACCESS, AWS, Google, NVIDIA) excludes undergrads as PI, so the grant route and the YCRC route **share one dependency**. §11.8 Phase 2 makes all three asks in one week-1 email. Ask more than one faculty member; the ACCESS Explore ask costs a sponsor ~30 minutes and is the easiest yes | Phase 3 paid fallback, which is affordable enough that this is a schedule risk rather than a project risk |
| R-4c | Azure student credit cannot provision GPU | Low | Claim it and **test provisioning immediately**; do not plan around it until the test passes | It was never load-bearing — Kaggle + Modal + $150 covers the need |
| R-5 | OCR fails on many broadcast layouts | **Medium → Low** (§3.4: an independent implementation reports ~8,000 clips in ~1 week off standardized EFC overlays) | Per-layout ROI caching; **prefer standardized-overlay sources from week 1** (§7.2); restrict to working layouts and report coverage | Smaller clean corpus |
| R-6 | Insufficient sabre footage with visible apparatus | Medium | Prioritize in acquisition from week 1 | Zero-shot transfer only |
| R-7 | Second referee unavailable for R7 | Low | Intra-rater + reversal rate need no one | Two of three estimates |
| R-8 | Annotation burnout | **High and underrated** | The T0 oracle removes the bulk labeling burden; active selection means every label counts; the saturation rule gives a defined end. **Track annotation minutes and report them** | Stop at the current tier's saturation point and report the learning curve |
| R-9 | Scope creep into a product | Medium | D2 is explicit: no hosted service, no accounts, no deploy. **The test is who the interface serves** — §11.10. Tools for you (debug overlays, the annotation tool) and figures for the reader are in scope; anything a stranger would log into is not | Cut on sight. A demo page is deferred to Q8, post-P8 |
| R-10 | FERA revises again mid-build | Low | Cite versions, always. Track the arXiv listing | Report against the version current at submission and note the history |
| R-11 | **It eats the other projects** | **High** | §14 | §14 |
| R-12 | Blade annotation is slower than estimated | Medium | Sparse annotation + interpolation; synthetic pretraining reduces the real-label requirement | Annotate fewer frames per exchange, more exchanges |
| R-14 | **Under-powered ablations reported as results** | **High to credibility** | §10.3: 5 seeds cannot separate close arms and no affordable seed count can. §10.4's screening→confirmation design concentrates power on the 2–4 pre-registered contrasts that carry the claims | Report the contrast as under-powered with the run count that would resolve it. That is a defensible sentence; a mean±std implying absent resolution is not |
| R-13 | **Reinventing prior art and claiming it** | **High to credibility** | §3.4 is one instance, caught late. Before claiming any component is novel, search for it as a *method* and not just as a *system* — the score-delta oracle was published in a blog post, not a paper, and no literature search would have surfaced it. Grep the README for novelty language before release | Cite it and narrow the claim, as §3.2 and §3.4 both did. A narrowed true claim costs nothing; an uncited one costs the interview |

---

## 14. Sequencing against `build-plan.md`

D9 makes A1 the priority. Here is what that costs, written down now rather than discovered in December.

**`build-plan.md` §2 order was:** P1 course-seat alerts (Sep–mid Oct, **hard January deadline**), P4 eval tooling (late Oct), P3 lecture-slides (Nov), P5 search engine (winter break), P7 authz checker (Feb).

**What A1 displaces:**

| Project | Fate | Cost |
|---|---|---|
| **P1 — course seat alerts** | **Protect it.** See below | — |
| **P4 — LLM eval tooling** | Slips to winter break | Closes a requirement named *by name* in two of four postings. Real cost. But P4 is two weeks and is the easiest of the five to compress |
| **P3 — lecture → slides** | **Cut.** A1 subsumes it | None, and this is a gain. P3 existed to move `Machine learning` from Exposure to Working. A1 does that far more convincingly. Building both is redundant |
| **P5 — search engine (C++)** | Slips to summer or the Summer-2028 cycle | Real. P5 is the compiled-language project and it changes what kind of engineer he looks like. It was already scheduled after most Summer-2027 deadlines close |
| **P7 — authz checker** | Slips indefinitely | Low. It was already flexible and already post-deadline |

**P1 must be protected, and here is the argument.**

P1's January deadline is **external and immovable** — no shopping period, no dataset, no project. It is 2–3 weeks. And it is the **only project in the entire catalog that produces a denominator**: real users, real load, numbers that exist because the system exists rather than because it was benchmarked.

A1 cannot produce that. A1 produces a research result and a benchmark. Those are different currencies and a strong page wants both. **Losing P1 to gain three extra weeks of A1 is a bad trade**, and the fact that A1 is more interesting is exactly why the trade needs to be refused in writing now.

**The carve that makes both work:**

```
Sep – mid Oct   P1 focused build (protected)         ||  A1 P0 + P1 running in background
                                                          corpus acquisition and pose extraction
                                                          are COMPUTE-bound, not attention-bound.
                                                          Start them week 1 and let them run.

mid Oct         P1 ships                             ||  A1 becomes the sole focus
Oct – Jan       A1 P2 -> P3 -> P4a -> (P7, P6, P5)       Track A: Mac-only, no HPC needed
Jan             P1's shopping-period dataset lands   ||  A1 P4b if GPU access arrived
Spring          A1 P8, then P4b whenever access lands ||  P4 eval tooling compressed into a break
```

**The insight that makes this work:** A1's longest pole in the early phases is **pose extraction across the corpus**, which is a background compute job, not a thinking job. Start it in week 1 of September and it runs while P1 is being built. By the time P1 ships in mid-October, A1 has a fully extracted corpus waiting. That costs almost no attention and buys six weeks.

**Update `build-plan.md` §2 to reflect this.** A build order that contradicts what is actually being built is worse than no build order.

---

## 15. Measures ledger

**Create `profile/entries/a1-fencing-referee.md` from `_TEMPLATE.md` on day one and paste this in as empty checkboxes.** Per `project-recommendations.md` §5 and `build-plan.md` §7: a number not written down while you have it cannot be recovered honestly.

```markdown
## Workstream: Corpus and free supervision

Measures:
- [ ] exchanges auto-extracted with priority labels, no human labeling (Path A):
- [ ] exchanges auto-extracted via Path B (single light, no award):
- [ ] competitions / bouts / distinct athletes covered:
- [ ] Path A weak-label agreement with human verification, n=[N]:
- [ ] Path B weak-label agreement with human verification, n=[N]:
- [ ] fixed-2s vs. reset-bounded exchange window, priority accuracy delta (§3.4):
- [ ] hours of human labeling this replaced, estimated from measured per-clip time:
- [ ] corpus at >=50 fps, as a fraction of total:

## Workstream: Evaluation protocol

Measures:
- [ ] priority accuracy, clip-level stratified split (FERA-matched protocol):
- [ ] priority accuracy, bout-disjoint:
- [ ] priority accuracy, athlete-disjoint:
- [ ] priority accuracy, event-disjoint:
- [ ] priority accuracy, athlete- AND event-disjoint (headline protocol):
- [ ] the generalization gap, clip-level minus athlete+event-disjoint:
- [ ] epee negative control accuracy (must be chance = 50%):
- [ ] published baselines at time of build, with versions and protocols:
      Allez Go 89.1% (protocol unstated) / FERA-LM 77.7% (v1-v2, bout-disjoint,
      NOT athlete-disjoint) / FERA structured 0.624 acc, 0.632 macro-F1 (current
      version, "shared protocol") / FERA-MDT move macro-F1 0.549 +/- 0.018 /
      BiFenceNet 87.6% (footwork, person-independent)

## Workstream: Blade perception

Measures:
- [ ] blade tip localization error, median, normalized:
- [ ] blade tip localization error, 95th percentile:
- [ ] guard tracking success rate:
- [ ] blade visibility rate across frames:
- [ ] contact-event detection F1:
- [ ] contact-event timing error, ms:
- [ ] all of the above at high angular velocity (the case that matters):
- [ ] priority accuracy, pose-only baseline:
- [ ] priority accuracy, pose + blade, identical folds and seeds:
- [ ] paired significance (McNemar) p and effect size:
- [ ] synthetic-pretraining benefit, isolated:

## Workstream: Audio fusion

Measures:
- [ ] A/V offset, median before correction / residual after:
- [ ] audio event classifier F1, per class:
- [ ] contact timing error: vision-only / audio-only / fused:
- [ ] priority accuracy delta from audio, over pose+blade:

## Workstream: Rules and explanations

Measures:
- [ ] rule engine accuracy given GOLD structured state (the ceiling):
- [ ] end-to-end accuracy, rule-grounded arm:
- [ ] end-to-end accuracy, direct arm:
- [ ] error attributable to perception vs. rule application:
- [ ] explanation structured-field accuracy:
- [ ] blind human rating of generated vs. referee-written justifications:
- [ ] explanation corpus size:
- [ ] priority accuracy with vs. without explanation supervision:

## Workstream: Cross-weapon transfer

Measures:
- [ ] foil-trained accuracy on foil, headline protocol:
- [ ] foil-trained accuracy on sabre, zero-shot:
- [ ] the transfer gap:
- [ ] sabre-trained accuracy on sabre:
- [ ] failure categories that transfer vs. those that do not:

## Workstream: Hard cases and the human ceiling

Measures:
- [ ] contested exchanges mined:
- [ ] reversals identified:
- [ ] review-detection precision / recall:
- [ ] model accuracy, contested subset:
- [ ] model accuracy, uncontested subset:
- [ ] the contested/uncontested gap:
- [ ] inter-referee agreement, Cohen's kappa:
- [ ] inter-referee agreement, Krippendorff's alpha:
- [ ] intra-rater agreement, blind relabel >=30 days later:
- [ ] empirical reversal rate among reviewed calls:
- [ ] MODEL ACCURACY AS A FRACTION OF THE HUMAN CEILING:

## Workstream: Efficiency and reproducibility

Measures:
- [ ] labels-to-saturation, per tier:
- [ ] accuracy per 1,000 human-labeled exchanges (the learning curve):
- [ ] total human annotation hours:
- [ ] GPU-hours consumed, and cost if cloud:
- [ ] wall-clock to reproduce all results from a clean checkout:
```

---

## 16. The bullets it buys

Shape per `resume-rules.md` §3.0: `[Verb] [what it is, in plain English], **[the outcome, with its number]** [by/through/using <technical method>].`

Bracketed placeholders **stay bracketed until measured**. Bolded phrases contain no term from `jargon.txt` and are readable by a non-engineer.

- Built a system that watches a fencing bout and decides which fencer should get the point, **agreeing with the referee's call on [X]% of [N] exchanges where two published systems reach [Y]% and [Z]%**, using body motion, blade tracking, and blade-contact sound together.

- Labeled [N] refereeing decisions automatically by reading the scoreboard instead of by hand, **producing [X] times more training examples than the largest published set at [Y] hours of human labeling instead of [Z]**, by recovering each call from how the score changed.

- Showed that published accuracy on this task **drops [X] points when the same fencer is not allowed to appear in both training and testing**, by rebuilding the evaluation five ways and reporting all of them.

- Measured how often two referees watching the same phrase disagree, **finding a [X]% human agreement ceiling that every previously published number had been implicitly compared against 100%**, from repeat labeling and [N] video-review reversals.

- Built the first visual blade tracker for fencing video, **locating the blade tip to within [X]% of a fencer's height while it moves faster than the camera can freeze it**, by recovering the blade's motion streak instead of trying to detect it as an object.

- Tested whether a model trained on one fencing weapon works on another, **finding a [X]-point drop that no prior work had measured**, and confirmed the pipeline learned the rule rather than a shortcut by checking it scores at chance on the weapon that has no such rule.

*The second and fourth are the strongest. The second is a before/after on labeling effort at matched output — the top rung of `resume-rules.md`'s ladder. The fourth is the kind of sentence that makes an interviewer stop reading and ask a question, which is the entire purpose of the page.*

---

## 17. Open questions

Decisions deliberately deferred, each with a decision point and a default.

| # | Question | Decide at | Default if undecided |
|---|---|---|---|
| Q1 | 3D pose at full corpus scale, or gold subset only? | P3 entry | Gold subset first; expand if A4 shows 3D helps |
| Q2 | V-JEPA 2 or VideoMAE V2 for S6? | P4b entry | V-JEPA 2 frozen; drop S6 entirely if the frozen arm shows nothing |
| Q3 | Recruit a second referee in person, or remotely with a shared tool? | P8 entry | Remote, via a read-only build of the annotation tool |
| Q4 | Release model weights, or features and code only? | P8 | Release weights. Weights without raw video carry no identity risk |
| Q5 | Submit to a venue? | After P8 | Not specified in this PRD, but §10.3's rigor means the option stays open at no extra cost |
| Q6 | Sabre corpus sufficient for training, or zero-shot only? | P7 entry | Zero-shot only; that is the novel result regardless |
| Q7 | Does the T3 explanation corpus get its own DOI / dataset release? | P8 | Yes if R6 is powered; otherwise release as a repo artifact |
| Q8 | A public demo page — clips, overlays, calls, rule traces? | **After P8, never before** | **No.** D2 stands during the build. If revisited: a **static** page of pre-rendered examples from §11.10.2 — no upload, no backend, no accounts — is a packaging decision costing about a day, and is the only form that does not reopen R-9. Anything accepting a user's video is a different project |

---

## 18. References

[az]: https://www.jsr.org/hs/index.php/path/article/view/3394
[fera]: https://arxiv.org/abs/2509.18527
[ferav2]: https://arxiv.org/abs/2509.18527v2
[gh]: https://github.com/sholtodouglas/fencing-AI
[mo]: https://thejasonmo.medium.com/automated-data-collection-from-youtube-6e433b0e3513
[bout]: https://arxiv.org/abs/2103.03098
[access]: https://allocations.access-ci.org/project-types
[nairr]: https://nairrpilot.org/opportunities/allocations
[azure]: https://azure.microsoft.com/en-us/pricing/offers/ms-azr-0170p
[kaggle]: https://www.kaggle.com/product-feedback/173129
[modal]: https://modal.com/pricing
[vjepa]: https://arxiv.org/html/2506.09985v1
[asha]: https://arxiv.org/pdf/1810.05934
[fn]: https://openaccess.thecvf.com/content/CVPR2022W/CVSports/papers/Zhu_FenceNet_Fine-Grained_Footwork_Recognition_in_Fencing_CVPRW_2022_paper.pdf
[vf]: https://arxiv.org/html/2507.00261v1
[ycrc]: https://research.computing.yale.edu/computing-resources/hpc-policies

**Prior art**

- **Allez Go** — Jason Mo, *Journal of Student Research*. Pose estimation + audio for blade contact; Temporal Convolutional Network; ~4,000 clips of international fencing over 7 years; **89.1%**, stated as +20% over prior SOTA. Weapon unspecified; split protocol unstated. [Link][az]
- **FERA** — arXiv `2509.18527`, revised repeatedly under at least three titles. Foil. RTMDet-Tiny + RTMPose-M + Norfair; 101-D kinematic features; encoder transformer; 1,734 clips / 2,386 annotated actions / 969 held-out exchanges; 3 Grand Prix events at 720p **25 fps**, ~130 competitors; annotated by a nine-year competitive foil fencer. **FERA-MDT move macro-F1 0.549 ± 0.018**; **blade-line macro-F1 ≈0.38**; **FERA-LM 77.7%** priority accuracy (v1/v2); **0.624 accuracy / 0.632 macro-F1** in the current abstract under a "shared protocol." Releases anonymized pose features, labels, code, and fixed folds. [Current][fera] · [v2][ferav2]
- **FenceNet / BiFenceNet** — Zhu & Wong, CVPRW 2022. Fine-grained footwork recognition; stacked TCNs, causal + anti-causal; Fencing Footwork Dataset (10 fencers, 6 actions, 652 videos); **85.4% / 87.6%**, vs. JLJA 86.3%, under **person-independent 10-fold CV**. [Link][fn]
- **VirtualFencer** — arXiv `2507.00261`, 2025. Strategy extraction and bout generation from in-the-wild video; WHAM → 3D SMPL, SAM 2 piste-line homography, YOLO detection; 1.5 hours, 40 international bouts, 54 senior FIE fencers. [Link][vf]
- **Automated data collection from YouTube** — Jason Mo (author of Allez Go). The score-delta labeling oracle, published: colour detection on the standardized EFC score overlay to catch light events, a digit recognizer for score tracking, fixed 2-second clips, and labels derived from the award — both-on-target resolved by which fencer is awarded the touch, single-light-no-award resolved to the opposing fencer. **~8,000 clips / ~10 GB in about one week.** Credits `sholtodouglas/fencing-AI`. **This is the prior art for §7.3 — see §3.4.** [Link][mo]
- **sholtodouglas/fencing-AI** — deep learning refereeing. [Link][gh]

**Methodology**

- **Accounting for Variance in Machine Learning Benchmarks** — Bouthillier et al., arXiv `2103.03098`. Randomizing all variance sources (init, splits, data order, augmentation) beats fixed-config seed-varying at **51× less compute**; *"more variation sources with more splits beats fixed hyperparameters with more seeds."* Recommends **P(A > B) ≥ 0.75**, requiring **~29 runs** to reliably detect an improvement. **The basis for §10.3's revised seed rule and §10.4's two-stage design.** [Link][bout]
- **ASHA** — Li et al., arXiv `1810.05934`. Asynchronous successive halving; ~10–28× reported speedups. **Hyperparameter search only — not for ablation arms** (§11.8 Phase 4.7). [Link][asha]
- **Proper Reuse of Image Classification Features Improves Object Detection** — arXiv `2204.00484`. On recovering the accuracy cost of frozen-backbone detection.
- *Unverified and deliberately not planned around:* Colas et al. `1806.08295` seed-count guidance (abstract only retrieved).

**Infrastructure** *(researched Aug 27, 2026 — see §11.8)*

- **Yale Center for Research Computing HPC policies** — standard-tier partitions including `gpu` incur no charge; undergraduate access is limited and generally requires a faculty sponsor. [Link][ycrc]
- **NSF ACCESS allocations** — **"Undergraduate students are not eligible to be PIs."** Explore tier: abstract-only, 400,000 credits, ~2-week turnaround; half the credits released up front, remainder after a progress report. **Requires a faculty PI.** [Link][access]
- **NAIRR Pilot** — 3-page proposal, monthly cycle; undergraduate eligibility unclear. [Link][nairr]
- **AWS Cloud Credit for Research** — graduate/postgraduate/PhD only; students ≤$5,000. **Undergrads ineligible.**
- **Google Cloud Research Credits** — faculty/PhD/postdoc; explicitly *"Graduate students are not eligible."* PhD awards ≤$1,000.
- **NVIDIA Academic Grant Program** — faculty-only, **currently closed to new applications.**
- **Azure for Students** — $100, 12 months, no credit card, .edu verification. ⚠️ **GPU VM quota unverified.** [Link][azure]
- **Kaggle Notebooks** — 30 GPU-hr/week free, P100 16GB or T4×2, 12 hr/session, 20 GB persisted. [Link][kaggle]
- **Modal** — $30/mo free credits, serverless. [Link][modal]
- **GPU spot pricing, Aug 26 2026** (getdeploying, 16 providers / 217 listings): **RTX 4090 interruptible $0.14/hr (Vast.ai)**, $0.17/hr (Novita); on-demand cheapest $0.26/hr, median $0.43/hr — down ~14% in 90 days. RunPod official: 4090 $0.74/hr, L40S $0.99/hr, A40 $0.44/hr, A100 PCIe 80GB $1.39/hr. Lambda: A100 40GB $1.99/hr, no spot tier, **no egress fees**. Modal: L40S $1.95/hr, A100 40GB $2.10/hr.
- **Billing traps:** Vast.ai bills storage while stopped (delete, don't stop) and charges bandwidth both directions at host-set rates; RunPod volumes cost $0.20/GB/mo idle vs $0.10/GB/mo running.
- **V-JEPA 2** — arXiv `2506.09985`. Frozen encoder + 4-layer attentive probe is the paper's own eval protocol; **8.4× GPU-time reduction** from progressive-resolution training. [Link][vjepa]
- *Superseded:* v1.0 of this document quoted H100 rates (≈$3.29/hr) and "a few hundred GPU-hours," anchoring the budget ~20× above the correct tier.

**Internal**

- `pipeline/a1-fencing-referee.md` — canonical rationale document
- `pipeline/build-plan.md` — five-project sequence, superseded in part by §14
- `reference/project-recommendations.md` — the five gates, §2
- `reference/resume-rules.md` — bullet shape, §3.0; truthfulness contract, §0
- `reference/jargon.txt` — terms banned from bolded phrases
- `profile/entries/_TEMPLATE.md` — entry file format for the §15 ledger

---

## Appendix A — Gate check

`reference/project-recommendations.md` §2 requires every idea to pass all five gates.

**Gate 1 — the hard-part test.** *Name the thing that makes this difficult and the specific way a naive implementation fails.* At the moment priority is decided, the blade is not an object in the frame — it is a motion-blur streak crossing more than a metre between consecutive frames. A detector trained to find a thin object finds nothing, and a frame-level classifier is useless because no single frame contains the answer. A beat attack and a parry-riposte have nearly identical body poses and differ only in who contacted whose blade first and whether the attacking arm was already extending. **Passes.**

**Gate 2 — the measurement test.** *Name the numbers before starting, including a baseline being beaten.* §15 pre-writes sixty. Four published baselines with stated protocols. Three internal baselines matched to prior work. A negative control that must land at chance. **Passes, emphatically.**

**Gate 3 — the 45-minute test.** *A design decision with more than one defensible answer.* At least six: streak recovery versus object detection for the blade; audio versus vision versus fusion for contact; rule-grounded structured state versus end-to-end classification; per-fencer versus relational tokenization; free weak supervision at scale versus hand-labeled quality; and the split protocol itself, which is the decision the whole field has quietly gotten wrong. **Passes.**

**Gate 4 — the 500-applicant test.** *Would 500 other new grads have built this?* Labeling this data requires someone who can correctly call right-of-way, which is roughly ten years of the sport. Daniel fences all three weapons, which is what makes the épée negative control and the cross-weapon transfer experiment cheap rather than blocked. A machine learning engineer at Google could not build this without him. **Passes.**

**Gate 5 — the honest-stack test.** *Use the gap technology for what it is actually for.* Temporal models are used because the decision is a property of sequence. Point tracking is used because the object is thin and fast. Audio is used because it resolves an event vision cannot time precisely. Nothing here is a vendor integration. **Passes.**

---

## Appendix B — Day one checklist

Before writing any pipeline code:

- [ ] `profile/entries/a1-fencing-referee.md` created from `_TEMPLATE.md`
- [ ] All §15 measures pasted in as empty checkboxes
- [ ] Row added to `reference/entry-placement.json` as a Projects entry
- [ ] `a1-fencing-referee.md` §4 corrected per §3.1 — both FERA numbers, both versions
- [ ] `a1-fencing-referee.md` §4 extended with FenceNet and VirtualFencer per §3.3
- [ ] `a1-fencing-referee.md` §6 updated — Option B is now the plan, per D1
- [ ] `build-plan.md` §2 updated per §14
- [ ] **Faculty sponsor email sent** for YCRC access
- [ ] Repo scaffolded, CI green
- [ ] Corpus acquisition started — it runs in the background for weeks, so it starts today
