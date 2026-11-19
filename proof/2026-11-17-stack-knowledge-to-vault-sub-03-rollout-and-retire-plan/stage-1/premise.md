# Stage 1 premises — 2026-11-17-stack-knowledge-to-vault-sub-03-rollout-and-retire-plan

Goal: the seven remaining stack pages exist, every owner fact in their sources is accounted for in a ledger, each reaches a Claude Code session on its sample file, and every registry project's set of applying pages is accounted for against the hook's budget, for the owner about to delete the skill text.
Risk: MEDIUM — a fact dropped here is gone once Stage 2 deletes its source; the ledger and the reader check are the guard. A page only named, not inlined, was never measured by the pilot (owner chose to record it, not to cut facts)

Outcomes:
- Works: a session opened (or cleared, or compacted) in a project that tracks a file matching a stack's `paths` starts with that stack page whole.
- The pages that apply to one project total more than 9,500 characters (an Android app with F-Droid metadata and Rust code, as `multitor-android`) → the session starts with the pages that fit, in slug order, and one line naming each page that did not, with its path to read.
- A project that tracks no matching file → no page; `budget.tsv` shows it with nothing applying.

These Outcomes are what `Stage N green` is checked against. Changing one after
this point needs the owner's words in its amendment note: owner, <date>: "<words>".

One entry per thing the Goal, Outcomes or Risk assume about what the code does
not control (the platform, another app, a permission, the engine, a service).
Check each on the real environment before building on it. Verdict: holds, false,
or not checkable here — <why>. A false premise is a Stop condition.

## Premise 1
Assumption: Claude Code adds a SessionStart hook's additionalContext to the session, and vault-context 0.7.0's hook delivers an applying stack copy whole in a real headless session.
Checked: 2026-11-19, the installed vault-context 0.7.0, rust copy in the stacks folder.
Result: `bash /home/user/dev/ai-tools/obsidian-wiki-plugin/tests/live/stack_page_loads.sh rust src/lib.rs` printed `LOADED session_start_hook` (exit 0), run today for Sub-plan 2's master gate; `claude.log` holds `rust LOADED session_start_hook`.
Verdict: holds

## Premise 2
Assumption: the hook inlines applying copies in slug order while the total stays at most 9,500 characters and names each copy that does not fit, with its path.
Checked: scratch `CLAUDE_CONFIG_DIR` holding a 7,043-character marked copy `aaa` and the 3,540-character rust copy; one tracked `src/lib.rs`; `echo '{"cwd":"<scratch>"}' | CLAUDE_CONFIG_DIR=<scratch cfg> python3 ~/.claude/plugins/cache/obsidian-wiki/vault-context/0.7.0/scripts/stack-context.py`.
Result: 7,309 characters out; marker `source=aaa` inlined; one line "The rust stack page applies to this project but did not fit ...; read <path>".
Verdict: holds

## Premise 3
Assumption: in a project that tracks no matching file, the hook adds nothing.
Checked: scratch git project tracking only `notes.txt`; the same hook command with the real stacks folder.
Result: exit 0, 0 bytes of output.
Verdict: holds
