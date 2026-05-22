# Plan Parser Reference

This document defines the deterministic rules for parsing planning-projects-style plan files (any `docs/plans/*.md` under a tracked project) to identify unexecuted work that should become backlog candidates. All detection is regex + state machine only — no LLM is invoked at any point. The parser is consumed by the `backlog unify` subcommand and by the `portfolio scan` orchestrator.

## Input signals

### 1. Unchecked task checkboxes

Plan files written by the planning-projects skill use `### Task N.N:` section headers, preflight/stage-gate bullets, and sub-task bullets. The parser reads these as a state machine: when a `### Task N.N:` header is entered, it collects all subsequent list items until the next `###`-or-higher heading or a `---` boundary.

Relevant patterns:

- **Task section header:** `^### Task \d+\.\d+:`
- **Unchecked bullet:** `^- \[ \]\s+`
- **Checked bullet:** `^- \[x\]\s+`

A Task N.N section is considered "unchecked" (and therefore a candidate) when either of the following is true:

- The section header is present and the body contains at least one `- [ ]` bullet and zero `- [x]` bullets.
- The section header is present and the body contains no bullets at all (i.e. the task was never started — an orphan header is logged and skipped per the malformed-plan rule below, not emitted as a candidate).

A section with a mix of `- [ ]` and `- [x]` bullets is partially done; each remaining `- [ ]` bullet is its own candidate, attributed to that Task N.N section.

Stage gate sections follow the same rule:

- **Stage gate header:** `^### Stage \d+ Gate`
- Same unchecked/checked bullet patterns apply; unchecked gate bullets are candidates with `source_locator` of the form `Stage N Gate / bullet K`.

### 2. Explicit Deferred sections

Any heading matching `^## Deferred$` or `^### Deferred$` (case-sensitive, no trailing text) opens a Deferred block. All bullet items (both `- [ ]` and bare `- ` items, regardless of checkbox state) under that heading until the next `^## ` heading or a `^---$` boundary are emitted as candidates. Checkbox state is intentionally ignored here — items were explicitly parked and all of them surface.

Pattern for heading detection: `^#{2,3} Deferred$`

Boundary patterns that close the block: `^## ` (any level-2 heading) or `^---$`.

### 3. Stale-plan candidates (opt-in via `--include-stale`)

Staleness is computed from git history only:

```
git log -1 --format=%ct -- <plan-path>
```

This returns the Unix timestamp of the last commit that touched the file. A plan is stale when `(now_unix - last_commit_unix) > 7_776_000` (90 days × 86 400 seconds/day).

This signal is **off by default**. It activates only when `--include-stale` is passed.

When active: any plan that is stale AND has at least one unchecked Task N.N bullet or at least one Deferred bullet emits ALL of its unchecked/Deferred items as candidates, tagged with `signal: stale-plan-unchecked`. Items already emitted by signals 1 or 2 are not duplicated — the `stale-plan-unchecked` tag is applied only to items that would not have been found without this flag (i.e. plans that otherwise would have been skipped because they had no current unchecked tasks under the normal heuristic — this flag lowers the bar to: stale + any unresolved item = surface it).

If `git log` exits non-zero (file untracked, not a git repo), staleness is treated as unknown and the file is excluded from stale detection with a logged note; it is still parsed for signals 1 and 2.

## Candidate output shape

Each candidate is a structured record with the following fields:

```
source_plan:    docs/plans/2026-05-22-foo-plan.md
source_locator: Stage 2 / Task 2.3
title:          Add retry logic to the upload handler
signal:         unchecked-task
```

Field definitions:

- **`source_plan`** — path relative to the project root (never absolute). Always starts with `docs/plans/`. Example: `docs/plans/2026-05-22-foo-plan.md`.
- **`source_locator`** — human-readable pointer to the exact location within the plan. Format varies by signal:
  - Task checkbox: `Stage N / Task N.N` (if a stage grouping is detectable from context) or `Task N.N` alone.
  - Stage gate bullet: `Stage N Gate / bullet K` (K is 1-based index within the gate block).
  - Deferred bullet: `Deferred / bullet K` (K is 1-based index within the Deferred block).
- **`title`** — the item text, stripped of its structural prefix. For a task header the `### Task N.N: ` prefix is removed; for a bullet the `- [ ] ` or `- ` prefix is removed. No further transformation.
- **`signal`** — one of three values:
  - `unchecked-task` — emitted by signal 1 (unchecked checkbox in a Task N.N or Stage Gate section).
  - `deferred-section` — emitted by signal 2 (any bullet under an explicit Deferred heading).
  - `stale-plan-unchecked` — emitted by signal 3 (stale plan, `--include-stale` active).

## Hard rules

1. **Default scope is signals 1 and 2 only.** Signal 3 (staleness) is never active unless `--include-stale` is explicitly passed. This prevents backlog churn from plans that are simply old but already complete.

2. **Source field format in `docs/backlog.md`.** When an accepted candidate is written into a project's backlog by the `backlog add` operation, the `Source:` field MUST be formatted as:

   ```
   Source: <source_plan> — <source_locator>
   ```

   That is: the relative plan path, a space, an em-dash (`—`, U+2014), a space, then the locator string. Example:

   ```
   Source: docs/plans/2026-05-22-foo-plan.md — Stage 2 / Task 2.3
   ```

   The backlog skill's dedup logic compares this string byte-for-byte. Any variation in spacing, dash character (hyphen vs en-dash vs em-dash), or path format will cause a duplicate entry to be created. The em-dash and single space on each side are mandatory.

3. **No LLM in parsing decisions.** Every detection step — header matching, checkbox state, Deferred boundary detection, staleness computation — is pure regex and state machine. The parser must produce deterministic output given identical input files and git history.

4. **Malformed plans are skipped, never aborted.** If a plan file cannot be parsed (e.g. a `### Task N.N:` header with no body before the next heading, a Deferred section with no bullets, a binary file, or a UTF-8 decode error), the parser emits nothing for that file and logs one line:

   ```
   Skipped 1 plan: docs/plans/2026-05-22-broken-plan.md (reason: orphan Task header with no body)
   ```

   The run continues with all other plan files and projects. Skipped-plan counts are aggregated into the final report summary. The parser never raises an exception that stops the enclosing `unify` or `portfolio` run.
