---
name: code-comment-audit
description: Use when the user asks to add, review, or audit code comments that explain project workflow or non-obvious choices across a codebase — magic numbers, ordering constraints, workarounds, or un-introduced entry points
---

# Code Comment Audit

Disciplined pass over a codebase that proposes concise, high-signal comments explaining **workflow** (how a file fits into the project) and **non-self-explanatory choices** (why a value, why this order, why this workaround). The skill abstains rather than inventing — if it can't state a concrete "why", it flags the location for the human instead of guessing.

This skill is NOT a docstring generator, API doc writer, or source-paraphraser. It does not touch code where no "why" is available.

## Invocation

- `/code-comment-audit` → dry-run report over the whole project (default)
- `/code-comment-audit apply` → dry-run report, then apply the proposed comments and noise removals
- `/code-comment-audit [path]` or `/code-comment-audit apply [path]` → narrow to a file or directory

If the user's invocation is ambiguous, ask whether they want dry-run or apply, and what scope.

## Phase 1 — Orient

Before scanning any code, build a project mental model.

1. Read `README.md`, `CLAUDE.md`, and any obvious `docs/*.md` files at the repo root. **If none exist**, fall back in this order: (a) the nearest `README.md` or `SKILL.md` inside the scope directory, (b) top-of-file headers of the scope's entry point(s), (c) package manifest (`package.json` description, `Cargo.toml` description, `pyproject.toml` description). Never proceed to Phase 2 without *some* anchored source for the Project Map.
2. Identify entry points per language. **If scope is narrowed to a sub-directory**, the entry point is the file that would be invoked by a user of that sub-directory (the `scripts/*.sh` a README tells you to run, the module's `__main__.py`, the shell script referenced by the parent `SKILL.md`). Do not treat helpers sourced by the entry point as separate entry points.
   - **bash**: files with `#!/bin/bash` or `#!/usr/bin/env bash` shebangs
   - **python**: `__main__.py`, files with `if __name__ == "__main__":`, `pyproject.toml` `[project.scripts]`
   - **node/js/ts**: `package.json` `"main"`/`"bin"`, `index.*`
   - **kotlin/android**: `AndroidManifest.xml` main activity, Application class
   - **go**: `main.go`
   - **rust**: `src/main.rs`, `[[bin]]` in `Cargo.toml`
   - **fallback**: whatever the README points at
3. Trace 1–2 hops of the call graph out from each entry point (which files source/import/exec which). Grep is enough — do not attempt full AST parsing.
4. Emit a **Project Map** (≤150 words): one short paragraph per major module, naming each module's role in the workflow.

The Project Map is the context every later comment must be justified against. If a proposed comment can't be traced back to something in the map, do not write it.

## Phase 2 — Scan

Walk every source file. Apply the ignore list (see below). For each file run the four trigger heuristics:

1. **Magic numbers / hardcoded constants** — numeric or string literals that look like configuration: timeouts, port numbers, chmod modes (`0644`, `0755`), retry counts, HTTP codes, buffer sizes. Flag when the literal appears in a function call with no named constant and no existing nearby comment.
2. **Non-obvious ordering** — consecutive operations where the order matters but isn't visible in the names. Examples: `apt-get update` before `apt-get install`; `mount` then `chmod` then `umount`; a socks5h check with a `torsocks` fallback.
3. **Workarounds / fighting the platform** — code that looks wrong at first read. Signals: double negatives, `sleep` before a check, explicit retries, `|| true`, unusual flag combinations, bug/issue numbers in code without context.
4. **Entry-point orchestration** — the file is an entry point per Phase 1 AND lacks a top-of-file header comment naming its role in the workflow. A header counts as adequate if it states (a) what the file does in one sentence AND (b) where it sits relative to the rest of the project (who invokes it, or what step of the pipeline it is). A header that is only a usage block or a table of contents (`Usage:`, `Requires:`, `Options:`) does not count — propose adding a one-sentence role line above it. A header that already explains role **and** usage is adequate; do not rewrite it.

For each hit, gate in this exact order. **First failure drops or reroutes the candidate:**

| Gate | Test | If fails |
|---|---|---|
| Restates the line? | Two checks, either fails: (a) the proposed comment text (minus marker) is a substring of the target line, OR (b) the comment only names the same tokens/operation the line already contains without adding a reason. | skip silently |
| Has a concrete "why"? | The answer can be traced to a specific sentence or named fact in the Project Map or a doc cited during Phase 1. A vague connection ("it's related to the scan") does not count. | reroute to **Flagged for human** with trigger + 1-line question |
| Fits in ≤2 lines inline? | — | promote to a docblock above the function or at top of file |
| Free of hedging (`may`, `might`, `possibly`, `probably`)? | — | reroute to **Flagged for human** |

**Flag vs. skip decision.** If the trigger heuristic fired but Gate 2 fails, the candidate goes to **Flagged for human** only when the literal looks like *configuration a reader would reasonably question* (timeouts, limits, modes, ports, retry counts, ordering constraints, workaround constructs). Do not flag array indices, obvious math, test-data values, or format strings. When in doubt, skip rather than flag — Flagged-for-human is a signal, not a dumping ground.

Also collect **noise-to-remove**: existing comments that restate their line verbatim or near-verbatim (`i++ // increment i`, `# set x to 5` above `x = 5`).

## Phase 3 — Report

Emit a single markdown report with sections in this order:

1. **Project Map** — from Phase 1. Shown first so the user can sanity-check the skill's mental model before trusting any comment below.
2. **Proposed comments** — grouped by file. Each entry:
   ```
   path/to/file.sh:42  [trigger: magic-number]
   - curl ... --connect-timeout 30 "$URL"
   + # 30s: .onion circuits are slow to build; 15s was flaky in practice
   + curl ... --connect-timeout 30 "$URL"
   ```
3. **Flagged for human attention** — `path:line`, trigger, 1-line question. No proposed text. Example: `scripts/install.sh:17  [trigger: magic-number]  why 0o644 here instead of default?`
4. **Noise to remove** — `path:line` and the existing comment to delete.
5. **Summary table** — counts by trigger type and total lines changed:
   ```
   | Trigger          | Proposed | Flagged | Removed |
   |------------------|----------|---------|---------|
   | magic-number     | 3        | 2       | 0       |
   | ordering         | 1        | 0       | 0       |
   | workaround       | 2        | 1       | 0       |
   | entry-point      | 1        | 0       | 0       |
   | noise            | -        | -       | 4       |
   ```

If the user invoked with `apply`, apply the diffs (proposed comments + noise removals) after printing the report. **Flagged-for-human entries are never auto-applied.**

## Hard rules (enforce on every comment written)

- [ ] No comment may be a restatement of its line — not literally (substring) and not semantically (same tokens, no added reason). If unsure, skip.
- [ ] No inline comment exceeds 2 lines. Longer explanations go in a docblock above the function or at top of file.
- [ ] Every comment names the **why**, not just the **what**.
- [ ] No hedging language: `may`, `might`, `possibly`, `probably`, `perhaps`, `seems to`. If unsure, flag for human.
- [ ] No comment may be written that the Project Map doesn't justify. If the connection to the workflow isn't concrete, flag instead.

**Violating the letter of these rules is violating the spirit of these rules.** If you find yourself rationalizing ("it's basically a why comment"), flag for human instead.

## Language handling

| Extensions | Comment syntax |
|---|---|
| `.sh` `.bash` `.py` `.yml` `.yaml` `.toml` `.rb` | `#` |
| `.js` `.ts` `.jsx` `.tsx` `.kt` `.java` `.rs` `.go` `.c` `.cpp` `.h` `.swift` | `//` |
| `.html` `.xml` `.md` | `<!-- -->` |
| `.lisp` `.clj` | `;` |

Unknown extensions: skip the file silently.

## Ignore list

- Directories: `.git/` `node_modules/` `vendor/` `target/` `build/` `dist/` `out/` `.venv/` `__pycache__/`
- Files: `*.min.*` `*.lock` `*.generated.*` `*.pb.go`
- Binaries: files with null bytes in the first 8 KB
- Respect `.gitignore` if present at repo root

## Common mistakes

- **Writing a "why" that just paraphrases the code.** `# increment the counter` is still noise even if you call it a "why". If the line self-explains, skip.
- **Assuming rationale without evidence.** If the Project Map doesn't tell you why `0644` is used, you don't know — flag it.
- **Commenting every magic number.** Only literals that look like **configuration** (timeouts, limits, modes, ports). Array indices, obvious math, and test-data values are not targets.
- **Top-of-file headers that just list what the file contains.** A header must explain the file's role in the workflow, not its table of contents.
- **Skipping the Project Map because "the code is obvious".** Without the map, workflow comments drift into paraphrase. Always do Phase 1 first, even on small projects (it just gets shorter).
- **Auto-applying flagged-for-human entries.** Never. Those exist precisely because the skill does not know the "why".

## Delegation (Claude Code only)

> **Skip this section unless you are Claude Code.** The Agent tool with
> `subagent_type:` parameters is a Claude Code feature. Codex, Cursor, Gemini,
> OpenCode, and other hosts do not have it — run the full workflow yourself
> instead.

Phase 1's Project Map inputs (reading README/CLAUDE.md, walking entry points)
and Phase 2's candidate enumeration (finding magic literals, entry-point files
without headers, ordering clues, workaround markers) are read-heavy. If you
are on Opus and the codebase is non-trivial, delegate those phases to the
`readonly-scanner` subagent (model: haiku) via the Agent tool with
`subagent_type: readonly-scanner`. Ask it to return:

- A file inventory grouped by role (entry points, config, shared, tests, docs).
- A candidate list: `file:line`, `kind` (magic-number, undocumented-entry,
  ordering-dependency, workaround), the surrounding 1–2 lines of context,
  whether an adjacent comment already exists.

Keep the Project Map narrative itself, the gate decisions, the flag-vs-skip
calls, and any actual edits in this session — those are where judgment lives.
