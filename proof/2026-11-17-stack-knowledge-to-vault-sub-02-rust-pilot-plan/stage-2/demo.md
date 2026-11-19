# Plan demo — 2026-11-17-stack-knowledge-to-vault-sub-02-rust-pilot-plan

Environment: Linux, Claude Code 2.1.328, 2026-11-19. Installed: vault-context@obsidian-wiki 0.7.0, rust-dev@coder-plugins 0.6.0 (the released one, which still ships skills/rust-coding). CP branch stack-knowledge-to-vault is unmerged; its rust-dev/ has only bin/, scripts/ and README.md. Six headless `claude -p` sessions were run, all in scratch git projects under the session scratchpad: one through W's tests/live/stack_page_loads.sh, five by hand. grade.py ran only on scratch copies of the PEV run folders. Nothing was written to ~/.claude, the vault, CP or W.

Fill in Verdict and Evidence under each Outcome. Do not edit the quoted lines.

# Stage 1

## Outcome 1
> Works: PEV holds sixteen gradeable baseline runs (`skill` and `bare`, `author` ×5 and `audit` ×3), each `meta.json` saying `"rule_present": false`, and `grade.py` prints per-arm finding sums and lane counts; `V/Portfolio/stacks/rust.md` lints clean with the six house rules and eight gotchas; `rust-dev-validate <root> --json` prints what `validate.sh` prints.
Verdict: holds
Evidence: PEV top level has skill-author-1..5, skill-audit-1..3, bare-author-1..5 and bare-audit-1..3. That is 16 folders. Each meta.json has `"rule_present": false`, `"environment": "ok"` and `"isolated": true`. `grade.py --results <scratch copy> --arms skill,bare` printed a table with runs, gradeable, findings, lane_run, skill_invoked and rule_loaded. Rows: skill/author 5/5, 0 findings, lane 5. skill/audit 3/3, 12 findings, lane 3. bare/author 5/5, 9 findings, lane 0. bare/audit 3/3, 12 findings, lane 0. It also printed per-run rule-id counts and "all expected runs present and gradeable" (exit 0). The page has exactly 6 rule bullets under "Owner rules the scripts check" and 8 numbered gotchas. The installed validate-stacks.sh lints the real vault and printed `verdict: pass (0 error(s), 0 warning(s), 0 info)`. So the synced copy matches the page, every source path exists, and no old copy is left in ~/.claude/rules. I ran CP's `rust-dev/bin/rust-dev-validate <copy of fixture-audit> --json` and `rust-dev/scripts/validate.sh <same> --json`. Their outputs were byte-identical (`cmp`): 0 errors, 6 warnings (cargo-missing-rust-version, cargo-lockfile-missing, rust-serde-missing-deny-unknown, rust-box-dyn-error-in-pub-api, rust-unwrap-outside-tests, rust-unbounded-channel).


## Outcome 2
> The `skill` and `bare` arms cannot be told apart → Task 1.2 and Stage 2 stop and the owner gets `PEV/probe.json`; the page and the commands still land.
Verdict: not shown here
Evidence: The trigger never happened. The arms can be told apart. PEV/probe.json shows skill: `skill_listed: true`, `rust_dev_skills: ["rust-dev:rust-coding"]`. It shows bare: `skill_listed: false`, `plugin_listed: false`. Both have `isolated: true`. Author findings also differ: skill 0, bare 9. So the probe file exists, Stage 2 went ahead, and that was correct. The stop path itself was never exercised. To show it, someone would need a probe run where both arms list the skill the same way (for example, the skill not masked in the bare arm), and then watch Task 1.2 and Stage 2 stop.


## Outcome 3
> A run fails for an environment reason → it is repeated once, and the first attempt stays in PEV marked `"environment": "failure"`.
Verdict: holds
Evidence: PEV/batch-logs/ratelimited-2026-11-18/ has bare-audit-2 and -3. PEV/batch-logs/ratelimited-2026-11-18b/ has rule-author-1..5 and rule-audit-1..3. Each name has two folders. `<name>.envfail/meta.json` is `attempt: 1, environment: "failure", environment_reason: "429"`. `<name>/meta.json` is `attempt: 2`, also a 429 failure. There is never an attempt 3. So the run was repeated once and the first attempt was kept and marked. Those batches were later moved under batch-logs/ (still inside PEV), and the graded top-level runs come from later clean batches, all `attempt: 1`. A side note: batch-logs/aborted-2-settings-masked/skill-author-1..5 have `exit: 1` but `environment: "ok"`. That batch failed from a harness fault (settings masked), not an environment cause. The executor set it aside by hand, not through the retry rule.


# Stage 2

## Outcome 4
> Works: a session opened (or cleared, or compacted) in a project that holds a `.rs`, `Cargo.toml` or `rust-toolchain.toml` file starts with the house rules and gotchas, added by vault-context's session-start hook from `${CLAUDE_CONFIG_DIR:-~/.claude}/vault-stacks/vault-stack-rust.md`; `rust-dev-validate <root> --json` runs the lane; no `rust-coding` skill is offered.
Verdict: holds (for the branch rust-dev; the installed release still offers rust-coding until CP merges)
Evidence: (a) `TMPDIR=<scratch> stack_page_loads.sh rust src/lib.rs` printed `LOADED session_start_hook` and exited 0. (b) I ran a session by hand in a scratch git copy of fixture-audit. The project's .claude/settings.json turned off the installed rust-dev, and `--plugin-dir CP/rust-dev` loaded the branch copy. SessionStart `hook_response` (exit 0) carried `additionalContext` holding the `vault-context:stack-rule source=rust sha256=550cbd4d…` marker. That text is identical to ~/.claude/vault-stacks/vault-stack-rust.md (same 3530 characters, same sha). Unprompted, the model quoted "Bound every channel; `unbounded_channel` only when capacity is a compile-time small constant (`rust-unbounded-channel`)" under "Owner rules the scripts check". It then ran `rust-dev-validate . --json`, which gave the same 6 rule ids as above. The init event's `skills` list had no rust-dev skill; the only Rust skill was anthropic-skills:rust-project. (c) Clear and compact: the hooks.json matcher is `startup|resume|clear|compact|fork`. I fed stack-context.py hook JSON with source startup, clear and compact for a project with a tracked Cargo.toml. Each returned the page (marker count 1). I did not open a live /clear or /compact in a TTY. (d) Caveat: with the released rust-dev 0.6.0, sessions still list `rust-dev:rust-coding` in init skills (seen in both proj-new sessions). Users stop being offered the skill only after CP merges and rust-dev is updated.


## Outcome 5
> The rust-dev plugin is turned off in a project → the page still arrives, and it says the command is unavailable there.
Verdict: holds
Evidence: Scratch project (fixture-audit copy) with .claude/settings.json `{"enabledPlugins":{"rust-dev@coder-plugins":false}}` and no --plugin-dir. The init `plugins` list has no rust-dev. The SessionStart hook_response still carried the stack-rule page, which includes "Both commands exist only where the rust-dev plugin is enabled. Where it is turned off they are not on PATH; check the rules above by reading the code." In that session `command -v rust-dev-validate` returned rc=1. The model concluded the plugin was off and said it would check the rules by reading the code. Nuance: the page gives this as a fixed condition ("where it is turned off…") for every project. It does not detect, per project, that the command is missing.


## Outcome 6
> A project with no Rust file yet → no page; it arrives at the next session start, or `/clear`, after the first matching file exists.
Verdict: holds, with a caveat: in a git project the file must be tracked or staged
Evidence: First run: a scratch git project with only README.md. No hook_response carried the stack-rule marker, and the model answered `NONE`. I then wrote Cargo.toml. With it still untracked, stack-context.py gave no page for startup, clear or compact (marker 0). After `git add Cargo.toml` it gave the page for all three (marker 1). A new real session then got the page in its SessionStart hook_response, and the model answered `# Rust`. In a non-git folder, an untracked src/lib.rs was enough (marker 1). W's WF-STACK-RULES.md says "a file the project tracks", so this is by design. The outcome's wording ("after the first matching file exists") is looser: a `cargo init` in an existing git repo gets no page until the files are staged.


## Outcome 7
> A project whose loadout settings were written before the loadout release → vault-context stays off there and no page arrives until CP's merge at Sub-plan 3's close ships the always-on change *(needs: CP merged and loadout updated, Sub-plan 3)*.
Verdict: not shown here
Evidence: This needs CP merged at Sub-plan 3's close and loadout updated on this machine, and neither has happened. To show it, a person would take a project whose .claude settings were written by the pre-release loadout. They would confirm that a session there gets no stack-rule hook_response now. Then, after the merge and a loadout update, they would confirm the page arrives. I did not simulate old loadout settings.


## Outcome 8
> The verdict is `no-go` → nothing is deleted; the run stops with the table.
Verdict: not shown here (the real verdict is `go`); the no-go table is shown on a doctored copy
Evidence: Re-grading a scratch copy of all 24 PEV runs with `grade.py --verdict` gave `go`. Its verdict, table, conditions and inputs_sha256 match PEV/verdict.json exactly. All 4 conditions pass. Rule/author has 0 findings against skill 0; rule/audit ran the lane 3 times against skill 3. CP's rust-dev now has no skills/ folder, which fits removal after a `go`. On a second scratch copy I removed rule-author-1. grade.py then printed the full table plus `[FAIL] 1` and `[FAIL] 2` and `verdict: no-go`, with problems `["MISSING rule-author-1"]`. But it exited 0, the same as on `go`. So any stop has to come from reading the verdict, not the exit code. The "nothing is deleted" part is the executor's job in Task 2.6 and could not be exercised: there was no real no-go. To show it, someone would run Stage 2 on a no-go result and confirm rust-dev/skills/rust-coding survives.
