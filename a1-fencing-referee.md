# A1 — Right-of-way referee for fencing

*Working spec. Consolidated Aug 26, 2026 from the A1 section of
`pipeline/personal-projects.md` plus the follow-up conversations about prior art,
weapon scope, and whether blade tracking is buildable. **This file is now the
canonical A1 document** — `personal-projects.md` keeps the short catalog entry,
this one keeps the decisions.*

> **Build spec: [`a1-fencing-referee-prd.md`](a1-fencing-referee-prd.md)** (Aug 26, 2026).
> That document is canonical for *what and how* — contributions, architecture, data plan,
> evaluation protocol, repo spec, and phase gates. **This file stays canonical for *why*.**
> Where they conflict, the PRD wins; PRD §3 lists every conflict. Note in particular that
> PRD §3.1 corrects the FERA number cited in §4 below, §3.2 reports that FERA released a
> benchmark, §3.3 adds two prior systems missing here, **§3.4 (Aug 27) records that Allez Go's
> author published the score-delta labeling oracle the PRD had claimed as novel**, and D1
> supersedes the §6 Option A decision with Option B (full scope, blade tracking included).

**Status:** committed to build. Paired with `distributed-options.md` #1
(offline-first tournament scoring).

---

## 1. What it is

Foil and sabre are decided by right-of-way: when both fencers land, a referee
decides who had priority — who initiated, whether a parry landed, whether the
attack lost tempo. It is the single most argued-about thing in the sport. Build a
model that watches a phrase and calls it.

**In one sentence, for anyone:** *"It watches two fencers and tells you who
should get the point — the thing referees argue about."*

---

## 2. The hard part

This is not object detection, it is **temporal reasoning at 200-millisecond
resolution**. A frame-level classifier is useless because no single frame
contains the answer — priority is a property of *sequence*.

The naive approach runs pose estimation and writes heuristics on top, and it
fails on the exact case that matters: a beat attack and a parry-riposte have
nearly identical body poses and differ only in **who contacted whose blade
first, and whether the attacking arm was already extending.**

The blade is a few pixels wide, moves faster than the frame rate, and
motion-blurs into the background. So the full version needs blade tracking under
motion blur, contact detection, and a model over the temporal sequence of
(extension, contact, direction change) — not over frames.

---

## 3. The unfair advantage

Labeled data for this requires someone who can *correctly call right-of-way*,
which is ten years of the sport. Almost nobody entering ML can produce this
dataset. A machine learning engineer at Google could not build this project
without Daniel. That is the definition of a moat, and it is the answer to "why
did you build this and not someone else."

**Daniel fences all three weapons.** That is the strongest possible version of
this advantage — see §5.

---

## 4. Prior art — researched Aug 25, 2026, and it helps

| System | Approach | Reported result | Scope |
|---|---|---|---|
| **[Allez Go][az]** (Jason Mo, *Journal of Student Research*) | Pose estimation + **audio** for blade contact; Temporal Convolutional Network. **Training data collected automatically via a score-delta labeling pipeline** — [separately published][mo], and the prior art for PRD §7.3; see PRD §3.4 | **89.1%**, stated as +20% over prior SOTA; ~4,000 clips of international fencing over 7 years. The collection pipeline reports ~8,000 clips in ~1 week | Weapon not specified in the paper |
| **[FERA][fera]** (arXiv 2509.18527, Sept 2025) | 2D pose → 101-dim kinematic features → transformer for multi-label action recognition → LM applying right-of-way rules with written justifications | **77.7% priority accuracy on 969 exchanges**; macro-F1 0.549 on 1,734 clips | **Foil** |
| **[sholtodouglas/fencing-AI][gh]** | Deep learning refereeing | — | — |

### Why prior art helps rather than hurts

`reference/project-recommendations.md` gate 2 requires "a baseline he is
beating." Before this research there was none — a reported 80% would have meant
nothing, because nothing said whether 80% was good. **Now there are two published
numbers and a defined state of the art.** Gate 4 is the *500-applicant* test —
whether five hundred other applicants would build this — not whether anyone in
the world has. They would not.

### The gap both systems leave open, in FERA's own words

> *"FERA currently relies on generic 2D pose estimates that **do not capture the
> blade explicitly**."*

Allez Go routes around the same wall from the other side by substituting
**audio** for visual blade contact. **Neither system tracks the blade visually,
because it is hard.** Explicit blade tracking that measurably improves priority
accuracy over pose-only is a real contribution, not a reimplementation.

### Three more openings FERA names as future work

- *"Rare actions are underrepresented"* — a referee can label the rare cases
  correctly, which is the whole bottleneck
- *"We lack ground-truth textual explanations from referees for direct
  supervision"* — **this dataset does not exist, and Daniel can create it.** A
  referee who can articulate *why* a call was made, at volume, is the scarce
  input for the entire subfield
- *"Some overfitting to individuals remains possible"* — a clean generalization
  study is available

### And one nobody has published at all

Every existing system is foil or unspecified. **Whether a foil-trained model
transfers to sabre is open**, and it almost certainly does not — sabre priority
turns on tempo and initiation rather than blade contact. Measuring that transfer
gap is a novel, cheap result: train once, test on the second weapon.

---

## 5. Weapon scope — settled Aug 26

**A1 is a foil and sabre project. Épée is a control, not a target.**

| Weapon | Priority logic | Role in A1 |
|---|---|---|
| **Foil** | Blade contact and initiation timing | **Primary.** Largest dataset, both baselines to compare against |
| **Sabre** | Tempo and initiation; no blade contact required — moving to attack first is priority | **Transfer target.** Nobody has published on this |
| **Épée** | None — first touch wins, simultaneous is a double | **Negative control.** A model that "finds priority" in épée is finding an artifact |

Blade tracking helps foil and sabre for *different* reasons — in foil it
disambiguates contact location, in sabre it disambiguates whether the blade
reached target. That is two distinct problems sharing a pipeline, not one problem
repeated.

**Daniel fences all three**, which means ground truth is available for every cell
in that table. That is what makes the cross-weapon transfer experiment cheap
rather than blocked.

> Note: the paired distributed-systems project (offline-first tournament scoring)
> is **weapon-agnostic** — partition tolerance, conflict resolution, and causal
> bracket ordering are identical across weapons. Only the scoring rules differ,
> and those are configuration.

---

## 6. Can blade tracking actually be done? — assessed Aug 26

The honest answer: **yes, but not first.**

**Why it is hard.** Two routes exist and both have a catch:

1. **Marker-based** (reflective tape on the blade) — clean ground truth in a
   controlled setting, worthless in competition. Gloves occlude markers, tape
   fails mid-bout, and it is non-regulation so no real tournament allows it.
2. **Vision-only** (the one worth having) — detect a ~90cm, few-pixels-wide blade
   moving faster than the shutter, in a cluttered gym, under bad lighting, with
   arm and glove occlusion and no fixed camera position. This is why neither
   published system does it.

**The decision:**

- **Option A — ship without blade tracking first.** Build the cross-weapon
  action-recognition model, measure against Allez Go and FERA, and document
  exactly where blade occlusion costs accuracy. ~4–5 weeks. **This is the
  committed path.**
- **Option B — blade tracking as the headline from day one.** Becomes two
  projects stacked: a vision result, then a right-of-way result. 8–10 weeks
  minimum, and it competes directly with P1/P4/P5 in `build-plan.md`.

**Chosen: A, then B as an extension.** Blade tracking becomes a T1 extension
after P1 ships in January — an improvement to a working system rather than a
prerequisite for one. The failure-mode documentation from Option A is what makes
the Option B contribution attributable when it happens.

The part no tool can do for you is deciding **where the camera goes in the gym
and which blade states matter**. That is domain expertise, and it is the input
the modeling work waits on.

---

## 7. Build order — stop when it works

1. **One weapon, deep.** Foil first, narrow phrase set, not the whole rulebook.
2. **The hard-case evaluation set**: calls that were **protested or reversed**,
   plus the rare actions FERA says are underrepresented. *This is a contribution
   even if the model is mediocre, because the benchmark is the artifact.*
3. **Cross-weapon transfer**, cheap — test the foil-trained model on sabre and
   report the gap. Do not train a second model. Run épée as the negative control.
4. **Explicit blade tracking**, ablated against the pose-only baseline so the
   improvement is attributable. *Deferred to post-January per §6.*
5. **Referee-written explanations**, if time remains. Highest-value and most open
   item on the list, and it is dataset work rather than modeling.

---

## 8. What you measure

- Agreement with the referee's actual call on held-out bouts, **by weapon**
- Agreement versus a pose-heuristic baseline — the thing everyone would try first
- Agreement on the subset where **the referee's call was protested or reversed**,
  which is the honest hard set
- Foil→sabre transfer gap, reported as a delta
- Where it fails, categorized: simultaneous attacks, remise, counter-attacks in
  tempo
- *(if §6 Option B happens)* pose-only vs. pose+blade, ablated

**Pre-write these as empty checkboxes in `profile/entries/` on day one** — per
`project-recommendations.md` §5 and `build-plan.md` §7. A number not written down
while you have it cannot be recovered honestly.

```markdown
## Workstream: Right-of-way classifier

Measures:
- [ ] agreement with referee call, foil, held-out:
- [ ] agreement, pose-heuristic baseline, same set:
- [ ] agreement on protested/reversed subset:
- [ ] agreement, sabre, zero-shot from foil-trained model:
- [ ] published baselines at time of build: Allez Go 89.1%, FERA 77.7%
```

---

## 9. Real users

Fencing clubs, Daniel's own included. Coaches want it for training review.
Referees want it for calibration. Parents want it because they cannot follow the
sport at all. There is also a live argument in the fencing world about video
review and consistency, so this lands in an ongoing conversation rather than a
vacuum.

---

## 10. Two obligations

**Cite both systems in the README, prominently — and cite Allez Go twice.** Once for the 89.1%
baseline, and once for the [data-collection method][mo] A1's free-supervision layer uses (PRD
§3.4). The second citation matters more than the first: reusing a published method without
crediting it is the one failure mode here that an informed interviewer reads as dishonest rather
than uninformed.

**Cite both systems in the README, prominently.** A write-up that does not
acknowledge Allez Go and FERA reads as either uninformed or dishonest, and an
interviewer who knows this space will check. Citing them and stating precisely
what is different is strictly stronger.

**The bar moved.** 77.7% and 89.1% now exist. A 70% model is no longer a neutral
result — it is a worse one. If the model underperforms, **the honest framing is
the benchmark and the cross-weapon transfer result**, not the accuracy number.
Decide that framing before building, not after seeing the result.

---

## 11. Honest risks

- **Hardest ML project in the catalog** — closer to a research problem than an
  engineering one. Scope narrow and widen only if it works.
- **Data and permissions.** Use publicly posted tournament footage and — better —
  record at the club with consent. Keep the labeled evaluation set built from
  **public footage** so the artifact in the repo is unambiguously shareable.
- **It competes for time with `build-plan.md`.** P1 has a hard January deadline
  (shopping period, or its dataset never exists). A1 must not eat that.

---

## 12. How it pairs

`distributed-options.md` #1 — offline-first tournament scoring — is the second
project. Same sport, same users, same clubs.

> *"I built the referee model and the scoring system for my sport, and clubs use
> both."*

One sentence carrying two projects, and it answers "why you?" in a way that two
unrelated repos do not.

---

## Sources

[az]: https://www.jsr.org/hs/index.php/path/article/view/3394
[fera]: https://arxiv.org/abs/2509.18527v2
[gh]: https://github.com/sholtodouglas/fencing-AI
[mo]: https://thejasonmo.medium.com/automated-data-collection-from-youtube-6e433b0e3513

- [Allez Go — Journal of Student Research](https://www.jsr.org/hs/index.php/path/article/view/3394)
- [Automated data collection from YouTube — Jason Mo](https://thejasonmo.medium.com/automated-data-collection-from-youtube-6e433b0e3513) — the score-delta labeling oracle, published. Prior art for PRD §7.3; see PRD §3.4
- [FERA — arXiv 2509.18527](https://arxiv.org/abs/2509.18527v2)
- [sholtodouglas/fencing-AI](https://github.com/sholtodouglas/fencing-AI)
