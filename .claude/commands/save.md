---
description: Save a work session — save progress, completed steps, and a resume note to PROGRESS.md.
allowed-tools: Read, Edit, Bash(git status *), Bash(git log *), Bash(git diff *), Bash(git add *), Bash(git commit *), Bash(gh api *)
---

**This is the durability mechanism. An un-`/save`d session is lost.** Follow these steps exactly:

1. **Identify context.** Run `gh api user --jq '.login'` to identify the engineer by GitHub username. Determine which phase(s) were worked on this session from the conversation history and from `git status` / `git diff`.

2. **Detect missed `/save` from prior sessions.** For each phase the engineer worked on this session:
   - Check the phase's **Resume context → Last worked** timestamp and **Last commit** in `PROGRESS.md`.
   - Run `git log --oneline --author="<git config user.name>" <branch>` to get the full commit history on the phase branch.
   - Compare the recorded **Last commit** hash against the branch history. If there are commits between the recorded last commit and the start of the current session's work, those are from a session that was never `/save`d.
   - **If missed-session commits are found**, display a warning and ask whether to include that prior work in today's update.

3. **Review session work.** Analyze the conversation to determine:
   - Which **Steps** checkboxes were completed this session.
   - Which **Exit criteria** are now met.
   - Any new steps discovered during the session that should be added.
   - What remains to be done.

4. **Capture git truth.**
   - Run `git status` and `git log --oneline -5`.
   - If there are **uncommitted changes**, warn the engineer and offer to commit them using the `P#: <description>` convention so progress isn't stranded in the working tree.
   - Record the **last commit hash + message**.

5. **Update `PROGRESS.md`.** Read `PROGRESS.md`, then edit the phase's block:
   - Tick completed **Steps** checkboxes (`[ ]` → `[x]`).
   - Tick completed **Exit criteria** checkboxes.
   - Add any new steps discovered during the session.
   - Update **Status** (e.g. → `in progress`, `blocked`, or `done`).
   - Fill the **Resume context**:
     - **Last worked:** current ISO timestamp + engineer name (@username)
     - **Last commit:** short hash + message
     - **Files touched this session:** list file paths changed/created
     - **Next step:** the single most important thing to do next session
     - **Open questions / gotchas:** any blockers, decisions needed, or tricky issues
   - If the phase is fully done (all exit criteria met), set status to `done`.

6. **Update the rest of `PROGRESS.md`.**
   - Update the Phase Index row (status, owner, branch).
   - Update the **Last updated** timestamp line.

7. **Print summary.** Show a short summary of:
   - What was saved (steps completed, status change).
   - Whether any prior-session work was reconciled.
   - What the next session should pick up (the Next step).
   - Any open questions or gotchas to be aware of.
