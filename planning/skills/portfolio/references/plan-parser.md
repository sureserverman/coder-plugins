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

Stage gate sections are **excluded** as candidate sources by design.

- **Stage gate header:** `^### Stage \d+ Gate` — its bullets are integration checks that restate task completion. Emitting them as separate backlog items would double-count work whose root task is already (or will be) a candidate.
- Treat the gate block as terminating the previous Task N.N's scope and otherwise skip its bullets entirely. If a stage gate's bullets are all unchecked, that signals the stage isn't done — but the unchecked Task N.N sections within the same stage already surface that.

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
  - Deferred bullet: `Deferred / bullet K` (K is 1-based index within the Deferred block).
- **`title`** — the item text, stripped of its structural prefix. For a task header the `### Task N.N: ` prefix is removed; for a bullet the `- [ ] ` or `- ` prefix is removed. No further transformation.
- **`signal`** — one of three values:
  - `unchecked-task` — emitted by signal 1 (unchecked checkbox in a Task N.N section). Stage Gate bullets are NOT a source.
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

## Authoritative signal: per-task `Status:` (plans from planning-projects v0.5.1+)

Plans produced after the precision rewrite carry a per-task `- **Status:** [ ]`
field that `executing-plans` flips to `[x]` on green. When a plan has `Status:`
fields, they are **authoritative** — no heuristic, no git archaeology.
Implemented by `parse_plan_status()` in `portfolio-unify.py`:

- **Detection:** any line matching `^\s*-\s*\*\*Status:\*\*\s*\[[ xX]\]` puts the
  whole file on the authoritative path. The checkbox is required: a
  checkbox-less field like `- **Status:** Draft` does NOT trigger the
  authoritative path — the file degrades gracefully to the legacy heuristic
  instead of silently losing its candidates.
- Task with `- **Status:** [x]` → DONE, never a candidate — including any stray
  raw `- [ ]` bullet left in its body (suppressed; Status is the only
  task-state source).
- Task with `- **Status:** [ ]` → unexecuted → exactly ONE candidate per task,
  with `signal: status-unexecuted`, `title` = the task description from its
  `### Task N.N:` header, and `source_locator` = `Stage N / Task N.N` (or
  `Task N.N` when no enclosing stage is detectable). The task's body bullets
  are never emitted as separate candidates.
- Raw unchecked bullets outside task bodies (gates, ad-hoc checklists) are
  likewise ignored — in authoritative mode the ONLY candidate sources are
  `Status: [ ]` fields and Deferred blocks.
- **Deferred sections remain active in both modes.** They are an explicit
  parking register, not a task-state heuristic; their bullets surface with
  `signal: deferred-section` exactly as in legacy plans.
- **Git stage evidence is not consulted** on the authoritative path
  (`done_stages` applies only to the legacy heuristic).
- A `- **Status:**` field without a preceding `### Task N.N:` header in its
  section (e.g. a master plan's `### Sub-plan N:` register entries) has no task
  context and emits nothing.
- A plan with a `**Completed:** <date>` close-out line and all `[x]` is fully
  done (and, by the rules above, yields zero task candidates).

The heuristic signals above (unchecked `[ ]` bullets, git-stage evidence)
remain the fallback for **legacy plans** that predate the `Status:` field.

## Master plans (plans from planning-projects v0.16.0+ multi-plan decomposition)

Big projects decompose into one **master plan** plus 2–7 **sub-plans** in the same
`plans/` directory (format: `../../planning-projects/references/master-plan-format.md`).
Parsing rules:

- **Detection:** filename ends in `-master-plan.md`, OR the first heading is
  `# Master Plan:`.
- **Register entries are pointers, never candidates.** A master's `### Sub-plan N:`
  sections are links to sub-plan files, not tasks. They MUST NOT be emitted as backlog
  candidates — the sub-plan's own tasks are the sole candidate source. Emitting both
  would double-count every piece of work.
- **Register `- **Status:** [x]` is authoritative for sub-plan done-ness at master
  level** (it mirrors the sub-plan's `**Completed:**` close-out line, which remains
  authoritative inside the sub-plan itself).
- **Master `**Gate:**` bullets are excluded** exactly like stage-gate bullets — they are
  integration checks, not deferred work.
- **Sub-plan files parse as normal plans** (they are standard planning-projects plans
  with a `Master:` backlink below `Date:`); all existing signals apply to them
  unchanged.
- A master plan with a `**Completed:** <date> — sub-plans: <list>` close-out line and
  all register entries `[x]` is fully done.

**Format guarantee (locked by `../tests/test-portfolio-unify.py`):** a master plan
yields **zero** candidates without master-specific code, on both paths. Its register
`- **Status:**` fields put it on the authoritative path, where its lack of
`### Task N.N:` headers means no task context and no candidates; and even under the
legacy heuristic it contains no raw `- [ ]` bullets outside `**Gate:**` blocks. The
rules above are therefore a documented invariant of the format, and the fixture suite
is the regression guard that keeps parser and format in lockstep.

## Architecture docs (from the architecting-projects skill, planning v0.17.0+)

`*-architecture.md` files land in the same `plans/` directory and are scanned like
any other file — there is no filename-based exclusion for them. Their safety is **by
construction**, exactly like master plans: the architecting-projects Document format
forbids raw `- [ ]` bullets and `- **Status:**` fields, so the doc emits nothing on
either parse path (no Status field → legacy heuristic → no unchecked bullets to
match; lists are plain `-` bullets, which only surface inside Deferred sections that
the format doesn't use).

**Format guarantee (locked by `../tests/test-portfolio-unify.py`):** the
`fixtures/plan-parser/sample-architecture.md` fixture — a realistic doc with ARCH-NN
sections, plain-bullet lists, and a fenced directory tree — yields **zero**
candidates, and its mutation twin (one smuggled `- [ ]`) yields exactly one,
proving the invariant is falsifiable.

## Light plans (from planning-projects, planning v0.22.0+)

A **Light plan** (`*-light-plan.md`, format:
`../../planning-projects/references/light-plan-format.md`) is the smallest staged
artifact the pipeline produces: one `## Stage 1:` of 2–5 `### Task 1.N:` tasks, each
carrying a `- **Status:** [ ]` field, plus one `### Stage 1 Gate`. It drops the
long-horizon fields (Preflight section, Risk/Rollback, Blocks/Parallel) but keeps the
three line shapes the parser keys on.

- **Detection:** none needed for the parser — a Light plan is just a Status-field plan,
  so any line matching the `Status:` checkbox regex puts it on the **authoritative path**
  (`parse_plan_status`) exactly like a Standard plan or a sub-plan. (`executing-plans`
  and the format doc detect it separately by the `-light-plan.md` suffix / `# Light Plan:`
  first heading, but the parser never needs to.)
- **In progress:** exactly one `status-unexecuted` candidate per `- **Status:** [ ]`
  task (title = the `### Task 1.N:` description, locator = `Stage 1 / Task 1.N`); its
  `### Stage 1 Gate` bullets are excluded like any gate, a stray `- [ ]` left in a done
  task's body is suppressed, and any `## Deferred` bullets surface as `deferred-section`.
- **Completed:** a Light plan with a `**Completed:** <date>` close-out line and all
  `[x]` tasks yields **zero** candidates — identical to a completed Standard plan.

**Format guarantee (locked by `../tests/test-portfolio-unify.py`):** the
`fixtures/plan-parser/2026-07-14-light-inprogress-plan.md` fixture (mixed statuses, a
gate, a stray bullet in a done task, a Deferred bullet) yields exactly one candidate per
undone task plus its Deferred bullet, and the `2026-07-14-light-completed-plan.md`
fixture yields zero — so the Light format is parser-safe **by construction, with no
parser code**.
