---
name: code-comment-audit
description: Use when the user asks to add, review, or audit code comments that explain project workflow or non-obvious choices across a codebase — magic numbers, ordering constraints, workarounds, or un-introduced entry points
---

# Code Comment Audit

Propose short comments that explain **workflow** (how a file fits the project)
and **non-obvious choices** (why this value, order or workaround). Abstain
rather than invent: with no concrete "why", flag the spot for the human. Not a
docstring or API-doc generator.

## Invocation

- `/code-comment-audit` → dry-run report over the whole project (default)
- `/code-comment-audit apply` → dry-run report, then apply the proposed comments and noise removals
- `/code-comment-audit [path]` or `/code-comment-audit apply [path]` → narrow to a file or directory

If the invocation is ambiguous, ask: dry-run or apply, and what scope.

## Phase 1 — Project Map

Read `README.md`, `CLAUDE.md` and root `docs/*.md` (else the scope's nearest
README/SKILL.md, entry-point headers, or manifest description). Find the entry
points and trace 1–2 hops of what they source/import/exec. Write a **Project
Map** (≤150 words). Every comment must trace back to it.

## Phase 2 — Scan

Triggers: **magic-number** (config-like literals: timeouts, ports, modes,
retries, sizes, with no named constant or comment), **ordering** (order matters
but names don't show it), **workaround** (`sleep` before a check, retries,
`|| true`, odd flags, bare issue numbers), **entry-point** (an entry point with
no header saying what it does and who invokes it; a bare `Usage:` block does
not count; an adequate header is left alone).

Gate each hit in this exact order. **First failure drops or reroutes the candidate:**

| Gate | Test | If fails |
|---|---|---|
| Restates the line? | Two checks, either fails: (a) the proposed comment text (minus marker) is a substring of the target line, OR (b) the comment only names the same tokens/operation the line already contains without adding a reason. | skip silently |
| Has a concrete "why"? | The answer can be traced to a specific sentence or named fact in the Project Map or a doc cited during Phase 1. A vague connection ("it's related to the scan") does not count. | reroute to **Flagged for human** with trigger + 1-line question |
| Fits in ≤2 lines inline? | — | promote to a docblock above the function or at top of file |
| Free of hedging (`may`, `might`, `possibly`, `probably`)? | — | reroute to **Flagged for human** |

**Flag vs. skip.** A Gate-2 failure goes to Flagged for human only when the
literal looks like configuration a reader would question (timeouts, limits,
modes, ports, retry counts, ordering, workarounds). Array indices, obvious math,
test data and format strings are skipped. When in doubt, skip.

Also collect **noise-to-remove**: existing comments that restate their line.

## Phase 3 — Report

One markdown report, sections in this order:

1. **Project Map** — first, so the user can check it before trusting any comment.
2. **Proposed comments** — grouped by file:
   ```
   path/to/file.sh:42  [trigger: magic-number]
   - curl ... --connect-timeout 30 "$URL"
   + # 30s: .onion circuits are slow to build; 15s was flaky in practice
   + curl ... --connect-timeout 30 "$URL"
   ```
3. **Flagged for human attention** — `path:line`, trigger, 1-line question, no proposed text. Example: `scripts/install.sh:17  [trigger: magic-number]  why 0o644 here instead of default?`
4. **Noise to remove** — `path:line` and the comment to delete.
5. **Summary table**:
   ```
   | Trigger          | Proposed | Flagged | Removed |
   |------------------|----------|---------|---------|
   | magic-number     | 3        | 2       | 0       |
   | ordering         | 1        | 0       | 0       |
   | workaround       | 2        | 1       | 0       |
   | entry-point      | 1        | 0       | 0       |
   | noise            | -        | -       | 4       |
   ```

With `apply`, apply the proposed comments and noise removals after printing the
report. **Flagged-for-human entries are never auto-applied.**
