---
description: Start a work session — load progress, identify engineer, pick a phase to resume.
allowed-tools: Read, Edit, Bash(git config *), Bash(git status *), Bash(git branch *), Bash(git log *), Bash(git checkout *), Bash(gh api *), Bash(gh auth *), Bash(git remote *)
---

Follow these steps exactly:

1. **Load context.** Read `PROGRESS.md` in full to load the current state of the project. Also read `CLAUDE.md` for project rules and phase definitions.

2. **Identify the engineer.** Run `gh api user --jq '.login'` to get the engineer's GitHub username.
   - If this fails (not authenticated), ask the engineer to run `gh auth login` first.
   - Also run `git config user.name` to get their display name for greetings.
   - Greet the engineer by their display name.

3. **Auto-detect new engineer.** Check if the engineer's GitHub username (from step 2) exists in the **Engineers** table in `PROGRESS.md` (the **GitHub** column).
   - **If found:** Continue to step 4.
   - **If NOT found:**
     a. Get the GitHub repo info by running `git remote get-url origin` and extract the `owner/repo`.
     b. Fetch the collaborator list: `gh api repos/{owner}/{repo}/collaborators --jq '.[].login'`
     c. Check if the engineer's GitHub username is in the collaborator list.
     d. **If found in collaborators:** Automatically add them to `PROGRESS.md`:
        - Get their display name from `git config user.name` (or `gh api user --jq '.name'` as fallback).
        - Add a row to the **Engineers** table with their name, GitHub username, role "Engineer", and phases "—" (none yet).
        - Commit: `git add PROGRESS.md && git commit -m "chore: add engineer @<username> (auto-detected from GitHub)"`
        - Tell them: **"Welcome! I've added you to the project. You don't own any phases yet — you can claim unassigned ones below."**
     e. **If not found in collaborators but `git config user.email` matches a collaborator's email:**
        - Treat as a match and add them to `PROGRESS.md` as above.
     f. **If no match:** Warn them and stop.

4. **Detect untracked work.** For each phase owned by this engineer that is `in progress` or `not started`:
   - Check the phase's **Resume context → Last worked** timestamp in `PROGRESS.md`.
   - If the phase has a recorded **branch**, run `git log --oneline --author="<git config user.name>" --after="<Last worked timestamp>" <branch>` to find commits made after the last `/save` session.
   - If there is no recorded branch, run `git log --oneline --author="<git config user.name>" --grep="P#:" --all` to find any commits tagged with this phase ID across all branches.
   - **If untracked commits are found**, display a warning:
     > ⚠️ **Untracked work detected on P#: \<phase name\>**
     > The following commits were made since the last recorded session:
     > *(list the commits)*
     > It looks like a previous session wasn't ended with `/save`, so PROGRESS.md may be out of date.
   - Ask the engineer: **"Would you like to reconcile this now before starting today's session?"**

5. **Show their phases.** From the Phase Index in `PROGRESS.md`, display only the phases owned by this engineer, showing each phase's:
   - ID, name, status, track, branch
   - **Next step** from the Resume context (if any)
   - Format as a numbered list for easy selection.

6. **Ask what to work on.** Ask: **"What would you like to work on today?"**
   - Present their owned phases as options.
   - Highlight phases that are unblocked and ready to start.

7. **Once a phase is chosen:**
   - Run `git status`. If the working tree is dirty or on the wrong branch, warn the engineer before proceeding.
   - If the phase has a recorded branch, offer to `git checkout` that branch.
   - If the phase has no branch yet, offer to create one following the convention `phase/P#-<short-slug>` and update `PROGRESS.md` with the branch name.
   - Print the phase's full **Resume context** (last commit, files touched, next step, open questions) so the engineer can resume exactly where they left off.
   - **If the engineer is starting a phase for the first time** (status is `not started`), also read the phase's exit criteria from `CLAUDE.md` and print them.
