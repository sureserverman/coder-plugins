# Stage 1 premises — 2026-11-17-stack-knowledge-to-vault-sub-02-rust-pilot-plan

Goal: the two baseline arms are measured before the rule exists, and the page that will replace the skill is written, for the owner deciding whether the move is safe.
Risk: MEDIUM — the arms must really differ; a harness that runs three identical arms would pass while measuring nothing

Outcomes:
- Works: PEV holds sixteen gradeable baseline runs (`skill` and `bare`, `author` ×5 and `audit` ×3), each `meta.json` saying `"rule_present": false`, and `grade.py` prints per-arm finding sums and lane counts; `V/Portfolio/stacks/rust.md` lints clean with the six house rules and eight gotchas; `rust-dev-validate <root> --json` prints what `validate.sh` prints.
- The `skill` and `bare` arms cannot be told apart → Task 1.2 and Stage 2 stop and the owner gets `PEV/probe.json`; the page and the commands still land.
- A run fails for an environment reason → it is repeated once, and the first attempt stays in PEV marked `"environment": "failure"`.

These Outcomes are what `Stage N green` is checked against. Changing one after
this point needs the owner's words in its amendment note: owner, <date>: "<words>".

One entry per thing the Goal, Outcomes or Risk assume about what the code does
not control (the platform, another app, a permission, the engine, a service).
Check each on the real environment before building on it. Verdict: holds, false,
or not checkable here — <why>. A false premise is a Stop condition.

## Premise 1
Assumption: a per-run `--settings` file that enables or disables `rust-dev@coder-plugins` changes whether `claude -p` offers the `rust-coding` skill, so the `skill` and `bare` arms are different sessions
Checked: `claude -p "Reply OK." --max-turns 1 --output-format stream-json --verbose --settings <f>` in a scratch git dir, once with `{"enabledPlugins":{"rust-dev@coder-plugins":true}}` and once with `false`; `jq 'select(.type=="system" and .subtype=="init") | .skills, .plugins'`
Result: enabled → skills `["rust-dev:rust-coding"]`, plugins `["rust-dev"]`; disabled → `[]`, `[]` (note: the init event is not line 1; hook events come first)
Verdict: holds

## Premise 2
Assumption: `rust-dev/scripts/validate-safety.sh` reports all six house-rule ids the grader counts
Checked: `grep -l <id> rust-dev/scripts/*.sh` for each of the six ids
Result: each of the six is in `validate-safety.sh`
Verdict: holds

## Premise 3
Assumption: the vault (NFS) is writable for the page and the evidence folder
Checked: `mkdir -p /mnt/vault/Portfolio/stacks && touch …/.w-probe && rm …/.w-probe`; PEV created at Preflight
Result: both succeed
Verdict: holds

## Premise 4
Assumption: headless `claude -p` runs work from this session and a Rust toolchain exists for the fixtures
Checked: Preflight headless check; `command -v cargo rustc`
Result: READY returned; `/home/user/.cargo/bin/cargo`, `/home/user/.cargo/bin/rustc`
Verdict: holds
