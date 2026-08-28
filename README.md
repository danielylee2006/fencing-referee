# A1: Right-of-Way Referee for Fencing

A research system that watches a fencing phrase and calls right-of-way (priority) —
who gets the point when both fencers land.

**The deliverable is a research repository and a released benchmark.** Not a product.

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

## License

Code: Apache-2.0. Released features and labels: CC-BY-4.0.
See `LICENSE` and `DATA_STATEMENT.md`.
