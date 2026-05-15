---
description: Dispatch the game-design-expert subagent to review a scoped game-project diff for mechanics, game feel, camera/navigation, UX, accessibility, and architecture findings.
argument-hint: "[optional: file path | commit SHA | PR number | branch name]"
---

# /game-review

Delegates a game-project review to the **game-design-expert** subagent.

## Scoping

Given arguments `$ARGUMENTS`, resolve scope in this order:

1. **Empty** → `git diff` (uncommitted working-tree changes) plus `git diff --cached` (staged).
2. **Path to a file or directory** → `git diff -- <path>` if there are changes, else read the file(s) directly.
3. **Starts with `#` or looks like an integer** → treat as PR number, run `gh pr diff <n>`.
4. **Matches a git SHA** (7–40 hex chars) → `git show <sha>`.
5. **Matches a branch name** → `git diff main...<branch>` (fall back to `master` if `main` absent).

If the scope is empty after resolution (no diff, no file), report that and stop.

## Dispatch

Call the game-design-expert subagent with:

- **Run Protocol 1 (Stack Detection) first.** The review must be framed in terms of the project's engine, scope, and pipeline.
- **Then run the protocols relevant to the diff:**
  - Diff touches controller / input / movement files → Protocol 3 (Feel Tune) + Protocol 7 (Architecture).
  - Diff touches camera files → Protocol 4 (Camera Audit).
  - Diff touches UI / HUD / menu / tutorial files → Protocol 5 (UX Review).
  - Diff touches accessibility / settings / subtitle files → Protocol 6 (Accessibility Audit).
  - Diff touches gameplay / entity / system files → Protocol 7 (Architecture Review).
  - Cross-cutting design discussion → Protocol 2 (Mechanic Design).
- **Always do a parallel Protocol 6 (Accessibility) pass** if the project tier is "commercial release" — Basic-tier accessibility is a ship gate.

## Expected output

A markdown report in the **Game Design Review** schema from the agent's spec:

- Stack header.
- Findings severity-ranked: HARD (ship-blocking) / SOFT (recommended) / POLISH (nice-to-have).
- Each finding cites source by name (Nesky / Schell / Sylvester / Swink / Hodent / Nystrom / Unity docs / Godot docs / Unreal docs / GAG).
- Sources-cited section at the bottom.

## Don'ts

- Don't edit code as part of the review unless the user follows up asking for it.
- Don't summarize the diff back to the user — they wrote it.
- Don't apply rules outside the project tier (jam game ≠ commercial; rules apply differently).
