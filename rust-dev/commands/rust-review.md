---
description: Dispatch the rust-expert subagent to review a scoped Rust diff (uncommitted changes, a file, a commit, or a PR) for idiom, safety, concurrency, and performance.
argument-hint: "[optional: file path | commit SHA | PR number]"
---

# /rust-review

Delegates a Rust code review to the **rust-expert** subagent (Protocol 4 — Review).

## Scoping

Given arguments `$ARGUMENTS`, resolve scope in this order:

1. **Empty** → `git diff` (uncommitted working-tree changes) plus `git diff --cached` (staged)
2. **Path ending in `.rs` or a directory** → `git diff -- <path>` if there are changes, else read the file(s) directly
3. **Starts with `#` or looks like an integer** → treat as PR number, run `gh pr diff <n>`
4. **Matches a git SHA** (7–40 hex chars) → `git show <sha>`
5. **Matches a branch name** → `git diff main...<branch>` (fall back to `master` if `main` absent)

If the scope is empty after resolution (no diff, no file), report that and stop.

## Dispatch

Call the rust-expert subagent with:

- **Stack Report first.** Ask it to run Protocol 1 on the repo before reviewing — the review must be framed in terms of the project's edition, MSRV, runtime, and test layout.
- **Then Protocol 4 (Review)** on the resolved scope.
- Ask it to return findings in the **Rust Review** schema — severity-ranked with category, file:line, Why (cited rule), Fix (code snippet).

## Expected output

1. **Stack Report** (from Protocol 1)
2. **Rust Review** — findings grouped by severity:
   - Blocker (soundness, UB, data race, security)
   - Major (API smell, perf bug, concurrency smell)
   - Minor (idiom nit)
   - Nit (style)
3. **Closing verdict** — `merge | merge-with-nits | request-changes | block`
4. **Optional patches** — if there are obvious trivial fixes (≤5 lines each), the agent may apply them directly via Edit; list applied patches and leave the rest for the human.

## Notes

- This command does not run the full project audit (`cargo audit`, `cargo deny`, unused-dep scan). For that, use the existing `rust-project` skill.
- For a security-focused review with CVE cross-reference, use `/sec-review:sec-review` instead.
- For a multi-model second opinion, use `/request-external-reviews`.
