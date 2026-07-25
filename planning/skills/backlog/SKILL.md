---
name: backlog
description: Use to read, append, or remove entries in docs/backlog.md — the project's deferred-work register. Triggers on "add to backlog", "defer this", "what's in the backlog", "BL-007 is done — remove it". Append on defer, remove on implement, list on research.
---

# Backlog

The backlog is a single file — `backlog.md` — that holds work the project chose not to do *right now*. Items are appended when deferred, removed when implemented, and consulted when a new plan is being researched.

## Where the file lives (resolver)

The backlog does **not** live in the repo. It lives in the Obsidian vault at the project's portfolio home:

```
<portfolio_home>/backlog.md   where  portfolio_home = <vault_dir>/Portfolio/<area>/<name>/
```

Resolve `portfolio_home` per `../portfolio/references/registry-format.md` (resolver section): read `vault_dir` from `~/.claude/portfolio-config.yaml`, combine with the project's `area`/`name` from `~/.claude/projects-registry.yaml`; the repo's `.claude/vault-context.md` caches it as `portfolio_home`. **If `vault_dir` is unset, refuse and fail loudly — never fall back to `<repo>/docs/backlog.md`** (that would re-fragment the centralized docs). Every `docs/backlog.md` reference below means `<portfolio_home>/backlog.md`.

**Announce at start:** "Using the backlog skill — <add|list|remove|read|unify|complete> on <portfolio_home>/backlog.md."

---

## File format

`docs/backlog.md` is plain markdown. One header, then one section per entry, newest at the top:

```markdown
# Backlog

Deferred items from plan execution, code review, or ad-hoc capture. Entries are removed when implemented; git history is the audit trail.

---

## BL-007 — Add retry on Synapse 5xx

- **Opened:** 2026-05-17
- **Source:** docs/plans/2026-05-13-android-mcp-ephemeral.md — Stage 2, Task 2.3
- **Reason:** Out of scope for current PR; the happy path was enough to unblock Stage 3.
- **Next step:** Standalone plan; depends on the Synapse migration landing first.
- **Tags:** android, synapse, resilience

Optional 1–3 sentence body for context that doesn't fit the bullets.

---

## BL-006 — ...
```

An entry may additionally carry a **parking annotation** among its bullets:

```markdown
- **Parked:** 2026-08-01 — waiting for dry season
```

`- **Parked:** <YYYY-MM-DD or free-text reason>` marks the item as
deliberately not-now: the compass skill excludes parked items from its
`next` recommendations (surfacing them only in `review`, or once a parked
date has passed). Parking is not completion — the entry stays open and is
still removed only when implemented. Add the line when deferring an item
you keep getting nagged about; remove the line to unpark.

**ID rules:**

- Format `BL-NNN`, three digits, zero-padded.
- Next ID = `max(existing BL-NNN) + 1`. **Never reuse a removed ID.** The git history of removals is the audit trail.
- IDs are referenced from plan files and commit messages: `Closes BL-007`.

**Required fields:** `Opened`, `Source`, `Reason`, `Next step`. `Tags` is optional.

---

## Operations

### `add` — append a new entry

Inputs: title, source (plan path + stage/task, or `ad-hoc`), reason, next step, optional tags, optional body.

1. Read `docs/backlog.md`. If the file doesn't exist, create it with the header block above (no entries yet).
2. Compute the next ID: scan for `BL-\d{3}`, take max, add 1.
3. Insert the new entry block immediately below the top `---` separator (newest first).
4. Save.
5. Report: `Appended BL-NNN — <title>.`

**Duplicate guard.** Before writing, scan open entries. If one shares the same `Source` (same plan + same stage/task) OR has ≥80% title token overlap, surface it and ask whether to update that entry instead of opening a new one. Don't silently create a duplicate.

### `remove` — delete an implemented or rejected entry

Inputs: one or more BL-IDs.

1. Read the file.
2. For each ID:
   - If no block matches the exact ID header, report `BL-NNN not found` and skip.
   - Else delete the entry block — from its `## BL-NNN — ...` heading through the next `---` separator (inclusive).
3. Save.
4. Report: `Removed BL-NNN, BL-NNN.` The calling commit message should include `Closes BL-NNN` so the rationale is recoverable from `git log`.

**Hard rules:**

- Only remove by explicit ID. Never bulk-remove by tag, source, or "looks done."
- Implementation status is asserted by a user or by a plan's Close-out — never inferred from a heuristic.
- Don't move entries to an archive section. Removal is removal; git is the archive.

### `list` — show open entries

Optional filters: `tag:<name>`, `source:<plan-path-substring>`, `since:<YYYY-MM-DD>`.

Output a compact table — `ID | Title | Source | Opened` — sorted newest first.

### `read` — return raw file content

For ingestion by other skills (e.g. `planning-projects` Phase 0 research). Returns the whole file as text; the caller does its own parsing.

### `unify` — derive backlog candidates from this project's plans

Inputs: optional `--project <absolute-repo-path>` (limit the sweep to one project; matched against the registry's `path` field, so a bare name will match nothing), optional `--write` (off by default — dry-run is the default behavior). There are no other flags.

**Plans source.** Always `<portfolio_home>/plans/` (resolver). There is no repo-mode and no plans-dir override: storage is vault-canonical, so a project that still keeps plans in `docs/plans/` must be migrated (`portfolio migrate`) before `unify` can see them.

Returns a structure of the shape:

```
{
  "candidates":         [ { source_plan, source_locator, title, signal }, ... ],
  "existing":           [ { id: "BL-NNN", source: "...", title: "..." }, ... ],
  "duplicates_skipped": N
}
```

Operation:

1. Resolve the plans directory: `<project-path>/<plans-dir>`. If it does not exist, return `{candidates: [], existing: [...], duplicates_skipped: 0}` with a note in the report; this is not an error.
2. Read every `*.md` file in that directory. For each, apply the parser rules documented in `../portfolio/references/plan-parser.md`: task `Status:` fields that are not done, unchecked bullets inside a Task section, and Deferred-section bullets.
3. Construct each candidate's `Source` string as `<plans-dir>/<plan-filename> — <source_locator>` (em-dash, single space each side), matching the byte-for-byte equality the dedup rule requires.
4. Read the project's `docs/backlog.md` (auto-create from the standard header template if missing). Build the set of existing `Source` values.
5. For each candidate whose `Source` exactly matches an existing entry's `Source`, drop it and increment `duplicates_skipped`. (This is exact string equality — no fuzzy match, no token overlap; the duplicate-guard in `add` already handles fuzzy-title cases.)
6. Return the structure above. **Do not write** unless `--write` was passed. The caller (the `portfolio` orchestrator, or the user via ad-hoc invocation) presents the candidate list and confirms; on confirm, each accepted candidate is appended via the existing `add` op.

When `--write` is set, every candidate becomes a new BL entry via `add`, with auto-filled fields:

- `Source:` the constructed `Source` string from step 3
- `Opened:` today's ISO date
- `Reason:` one-line auto-summary including the signal — one of `status-unexecuted` (a task whose `Status:` is `[ ]`), `status-partial` (`[~]` — started but unfinished; residual work is still open work), `unchecked-open` (an unchecked bullet inside a Task section), or `deferred-section` (a bullet under an explicit Deferred heading)
- `Next step:` `TBD — opened by unify on <date>; review and refine.`
- `Tags:` `auto-unified` plus the plan's filename date stamp as a tag (e.g. `2026-04-15`)

**Hard rules for `unify`:**

- Dry-run (no `--write`) is the default. Writes only happen on explicit confirm or `--write`.
- Dedup is exact `Source` equality. Never fuzzy. Never re-summarize an existing entry's text.
- **There is no staleness signal.** A `--include-stale` flag and a stale-plan candidate signal were documented here for months but never implemented; the enumeration above is the complete set the parser emits. Tracked as a feature request in the backlog rather than left as a false claim.
- Malformed or unparseable plan files are skipped with a one-line log entry; the run continues.
- Re-running `unify --write` immediately after the previous accept produces zero new candidates (idempotency by construction, because every accepted candidate's `Source` now lives in `docs/backlog.md` and matches by step 5).

### `complete` — mark a backlog item implemented and archive a short summary

Inputs: `<BL-NNN>` (one ID at a time), `--summary "<one-paragraph text>"` (required, non-empty).

Operation:

1. Read `docs/backlog.md` and locate the `## BL-NNN` block. If absent: report `BL-NNN not found` and abort.
2. Capture the block's title from the heading line (`## BL-NNN — <title>`).
3. Slugify the title for the filename: lowercase, alnum + `-`, max 40 chars.
4. Write a new file at `<portfolio_home>/plans/YYYY-MM-DD-<slug>-done.md` (today's date; same vault home as the backlog) with this template:
   ```markdown
   # Done: <title>
   Date: <YYYY-MM-DD>
   Source backlog ID: BL-NNN (removed in the same commit)

   ## Summary
   <the --summary text, verbatim>

   ## Context
   - **Opened:** <Opened field from BL block>
   - **Originating source:** <Source field from BL block>
   - **Tags:** <Tags field from BL block, if present>
   ```
5. Invoke the existing `remove` op on `BL-NNN` to delete the block from `docs/backlog.md`.
6. Report: `Completed BL-NNN — wrote <portfolio_home>/plans/<filename>-done.md, removed from backlog.`

**Hard rules for `complete`:**

- `--summary` is required and must be non-empty after whitespace trim. Reject the call otherwise.
- One BL-ID per call. Never batch.
- The commit that lands this work should include `Closes BL-NNN` so the audit trail in `git log` is consistent with the existing convention.
- The `*-done.md` file lives in `<portfolio_home>/plans/` (vault) so it is co-located with active plans but visually distinguished by the `-done.md` suffix. It is *not* an active plan; orchestrator tools should treat it as a historical record (parsers may skip files matching `*-done.md`).
- Never re-open: if a `*-done.md` exists for a slug and `complete` is invoked again with the same slug, append a numeric suffix (`-done-2.md`) rather than overwriting.

---

## Integration

- **executing-plans** — calls `add` whenever the user defers a task, a Red-Green cycle budget exhausts and the user chooses to skip, or a stage gate exposes scope outside the plan. Calls `remove` in Phase Close-out for every backlog item the executed plan implemented (the closing report should list them by ID).
- **planning-projects** — calls `read` in Phase 0 (Research). Open entries whose `Tags` or `Source` touch the new plan's scope are surfaced to the user; they decide which fold into the new plan vs. remain deferred. Plan tasks that resolve a backlog item should reference it (`Closes BL-NNN`) so executing-plans knows what to remove on close-out.
- **Ad-hoc** — invoke directly via natural language ("add to backlog: ...", "list backlog", "BL-007 is done, remove it").

---

## Safety rails

- The file is git-tracked. Don't `rm` it, don't rewrite it whole — only append/remove discrete blocks.
- Never auto-remove from a "looks implemented" heuristic — only on explicit instruction or `Closes BL-NNN` declared in a plan's Close-out.
- Preserve unrelated entries byte-for-byte during any edit. If the file's structure looks corrupt (missing `---` separators, duplicate IDs), stop and surface to the user.

## Remember

- Append on defer, remove on implement, list on research.
- IDs are immutable and never reused.
- Git history — not an in-file archive — is the record of what was closed and why.
