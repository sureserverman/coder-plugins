---
name: backlog
description: Use to read, append, or remove entries in `docs/backlog.md` — the project's deferred-work register. Triggers on "add to backlog", "defer this", "what's in the backlog", "BL-007 is done — remove it", "scan backlog for X", or when executing-plans / planning-projects need to capture or consume deferred items. Append on defer, remove on implement, list on plan research.
---

# Backlog

The backlog is a single file — `docs/backlog.md` — that holds work the project chose not to do *right now*. Items are appended when deferred, removed when implemented, and consulted when a new plan is being researched.

**Announce at start:** "Using the backlog skill — <add|list|remove|read> on docs/backlog.md."

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
