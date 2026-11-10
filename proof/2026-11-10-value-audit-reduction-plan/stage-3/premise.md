# Stage 3 premises — 2026-11-10-value-audit-reduction-plan

Goal: the owner's Rust, git, packaging and business components hold their core, `game-dev` is gone, and the result is versioned and recorded so the ports and the next plan can follow it.
Risk: MEDIUM — the same judgment risk as Stage 2, plus a marketplace entry is removed

Outcomes:
- Works: each shrunk component still gives what its Dispositions row lists, and triggers on the same requests as before
- Works: a review the owner asks for is done by the built-in `/code-review`, and a plan's review pass by `planning:code-reviewer`; `gate-audit` names that agent for its independent read
- A session asks for `git-github:code-reviewer` → the type is unknown to the host; the caller uses `planning:code-reviewer`, or a general agent briefed read-only when planning is not installed
- Works: `rust-dev`'s script lane still flags a real manifest fault from a fresh project directory
- Works: every remaining plugin installs from the marketplace; `game-dev` is not offered
- An install of `game-dev@coder-plugins` is attempted → the CLI refuses it as unknown
- A plan elsewhere names `rust-dev:rust-expert` → the router falls back to `general-purpose`; the one known open plan is in the backlog
- A task finds a Stays item missing from its file → it stops and reports

These Outcomes are what `Stage N green` is checked against. Changing one after
this point needs the owner's words in its amendment note: owner, <date>: "<words>".

One entry per thing the Goal, Outcomes or Risk assume about what the code does
not control (the platform, another app, a permission, the engine, a service).
Check each on the real environment before building on it. Verdict: holds, false,
or not checkable here — <why>. A false premise is a Stop condition.

## Premise 1
Assumption: every Stays marker Tasks 3.1–3.3 grep for is present before the cuts
Checked: `grep -ciF <marker> <file>` for NVPTX, validate.sh, deny_unknown_fields (rust-coding); validate-workflows.sh, `git push origin <tag>`, "Flagged for human", "Never grow the README" (git-github); audit.sh, heredoc (bash-script-audit); `{metric, target, by}` (revenue-model)
Result: every count >= 1
Verdict: holds

## Premise 2
Assumption: rust-dev's script lane flags an edition 2024 crate declaring Rust 1.70, from a directory outside the repo
Checked: mktemp project with that Cargo.toml; `bash rust-dev/scripts/validate.sh "$T" --json | grep cargo-edition-msrv-mismatch`
Result: `cargo-edition-msrv-mismatch`
Verdict: holds

## Premise 3
Assumption: one known open plan names a retiring agent (multitor's macOS network-extension plan names `rust-dev:rust-expert`)
Checked: `grep -n rust-expert /mnt/vault/Portfolio/anon-tools/multitor/plans/2026-09-19-macos-network-extension-apple-gated-plan.md`
Result: line 132 "`rust-dev:rust-expert`, Task 5.1 → `general-purpose`"
Verdict: holds — Task 3.6 records it in the backlog

## Premise 4
Assumption: staged-planning ships `planning:code-reviewer` (the replacement for git-github's reviewer) and the router falls back to general-purpose
Checked: `ls ~/.claude/plugins/cache/staged-planning/planning/1.4.2/agents/`; stack-routing.md lines 52, 57
Result: code-reviewer.md present; fallback rows present
Verdict: holds

## Premise 5
Assumption: the claude CLI refuses to install a plugin a marketplace does not list
Checked: deferred to the Stage 3 gate's install check (it runs `! claude plugin install game-dev@coder-plugins` on a fresh config dir)
Result: —
Verdict: not checkable here — the marketplace still lists game-dev until Task 3.4; the gate command decides it
