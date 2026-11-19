# Stage 2 premises — 2026-11-17-stack-knowledge-to-vault-sub-02-rust-pilot-plan

Goal: the rule arm is measured against the baseline, the verdict is written by the fixed rule, and on `go` the skill leaves CP, for the owner who wants one copy of these facts.
Risk: HIGH — the stage's Goal relies on model behaviour outside the code, and the comparison is small

Outcomes:
- Works: reading or editing a `.rs` or `Cargo.toml` file loads the house rules and gotchas from `~/.claude/rules/vault-stack-rust.md`; `rust-dev-validate <root> --json` runs the lane; no `rust-coding` skill is offered.
- The rust-dev plugin is turned off in a project → the rule still loads, and it says the command is unavailable there.
- The verdict is `no-go` → nothing is deleted; the run stops with the table.

These Outcomes are what `Stage N green` is checked against. Changing one after
this point needs the owner's words in its amendment note: owner, <date>: "<words>".

One entry per thing the Goal, Outcomes or Risk assume about what the code does
not control (the platform, another app, a permission, the engine, a service).
Check each on the real environment before building on it. Verdict: holds, false,
or not checkable here — <why>. A false premise is a Stop condition.

## Premise 1
Assumption: Claude Code loads a user rule in `~/.claude/rules/` whose `paths:` glob matches a file the session reads, and the InstructionsLoaded hook reports it with `load_reason: path_glob_match`
Checked: master plan Research (2026-11-17, Claude Code 2.1.326): probe rule `zz-probe-vault-stack.md` with `paths: ["**/*.zzprobe"]`; `claude -p` reading `other.txt` answered NONE, reading `sample.zzprobe` answered the canary, hook logged `"load_reason":"path_glob_match"`. Installed now: `claude --version` → 2.1.327
Result: held on 2.1.326; re-checked on 2.1.327 by Task 2.1's own test (`stack_rule_loads.sh rust src/lib.rs`), which is red if it no longer holds. No separate probe rule written (OD-2 covers only the generated rule)
Verdict: holds (2.1.326); re-verified in Task 2.1

## Premise 2
Assumption: a plugin loaded with `--plugin-dir` puts its `bin/` on the Bash tool's PATH, so the rule arm can run `rust-dev-validate` (the rule tells it to)
Checked: scratch git dir; `claude -p "Run exactly this Bash command and reply with its output only: command -v rust-dev-validate" --max-turns 3 --allowedTools Bash --settings {"enabledPlugins":{"rust-dev@coder-plugins":false}} --plugin-dir <CP>/rust-dev`; `ls ~/.claude/plugins/cache/coder-plugins/rust-dev/0.6.0/bin` → absent, so a hit cannot come from the installed copy
Result: `/home/user/dev/ai-tools/coder-plugins/rust-dev/bin/rust-dev-validate`
Verdict: holds

## Premise 3 (amendment 2026-11-18, OD-9..OD-11)
Assumption: a SessionStart hook's JSON `additionalContext` reaches the model, and `--output-format stream-json --verbose` shows the hook's stdout in a `hook_response` event the harness can read
Checked: scratch git project; a SessionStart hook printing `{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"<!-- vault-context:stack-rule source=zzprobe … -->\n# Zebra Canary Heading\nThe canary word is PELICAN-77."}}`; `claude -p "If your context holds a stack page, reply with its first '# ' heading line and the canary word; else reply NONE." --max-turns 1 --output-format stream-json --verbose --settings <that hook>`
Result: `hook_response` exit_code 0 with the marker in stdout; answer `# Zebra Canary Heading` / `PELICAN-77`
Verdict: holds. Premise 1 (path-glob load) held but does not deliver in practice: 7 of 8 rule runs read the rule first and the glob load never fired (Stage 2 amendment)
