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

3b. **Write session log.** Scan the full conversation and build a chronological log of everything notable that happened. Categorize each entry:
   - **BUILT:** Features, components, files created or modified
   - **BUG:** Problems encountered — what went wrong, what the root cause was, and how it was fixed
   - **DECISION:** Design choices made during the session, with reasoning
   - **LEARNED:** Insights, surprises, or things that turned out differently than expected
   - **DEFERRED:** Work that was planned but intentionally pushed to a later phase

   Be specific and honest. Include failed approaches and wrong assumptions — these are the most valuable entries for future sessions. Each entry should be one line with enough detail that a reader who wasn't in the session understands what happened and why.

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
   - Write the **Session log** from step 3b. Append it under the resume context as a bulleted list with category prefixes (BUG:, BUILT:, DECISION:, LEARNED:, DEFERRED:). Each session's log is kept — don't overwrite previous sessions' logs. Separate sessions with a date header.
   - If the phase is fully done (all exit criteria met), set status to `done`.

6. **Update the rest of `PROGRESS.md`.**
   - Update the Phase Index row (status, owner, branch).
   - Update the **Last updated** timestamp line.

7. **Print summary.** Show a short summary of:
   - What was saved (steps completed, status change).
   - Whether any prior-session work was reconciled.
   - What the next session should pick up (the Next step).
   - Any open questions or gotchas to be aware of.
