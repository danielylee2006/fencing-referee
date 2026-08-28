# Data Statement

## Release posture

- **Code:** Apache-2.0
- **Released features and labels:** CC-BY-4.0
- **Raw video:** Never released. All source footage is publicly posted competition
  video accessed via yt-dlp. Manifests (URLs, metadata) are committed; bytes are not.

## Sources

All footage is publicly posted competition video from official FIE, national federation,
and broadcast channels. No club footage, no private recordings (D4).

Corpus acquisition uses yt-dlp against the committed source manifest. Videos are
content-addressed (SHA-256) and cached locally. The manifest records source URL,
event, weapon, date, and license note for each clip.

## What is released

Following FERA's precedent (arXiv 2509.18527v2 §3.2):

1. **Extracted features** (pose, kinematics, blade, audio) — derived representations,
   not raw frames
2. **Labels** — priority calls with tier, path, and confounder metadata
3. **The benchmark** — exchange IDs, split definitions, evaluation protocol
4. **Code and weights** — full pipeline, all baselines, trained checkpoints

## What is NOT released

- Raw video frames or clips — these remain on the original platforms
- Any footage from private or non-public sources (none exists in this project)

## Ethical considerations

- All footage is from publicly broadcast professional competition
- No minors are included (professional FIE events)
- Athlete identities are used only for split stratification (ensuring athlete-disjoint
  evaluation) and are not released as a feature
- The system makes no claim about referee correctness — it predicts the call that
  was made, not the call that should have been made
