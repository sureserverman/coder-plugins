# Stage 2 premises — 2026-11-17-stack-knowledge-to-vault-sub-03-rollout-and-retire-plan

Goal: CP no longer ships the text the pages replaced, every guard and document agrees, and the versions are set, for the owner who wants one copy of each fact.
Risk: MEDIUM — many pinned files; a missed pin fails CI after the push, not locally

Outcomes:
- Works: the retired skills are no longer offered; a session in a project holding a matching file starts with the stack page (or a line naming it, where the applying pages overflow the budget); `android-fdroid-publish`, `android-ui-design-figma`, `build-readiness-check` and `review-readme` still run and point at the page by name where they used to carry the facts.
- The owner asks for a retired skill by name → Claude Code reports it is not available; the plugin README says where its facts went.
- A project whose loadout settings were written before loadout 0.3.0 → after the update and a loadout re-run there, vault-context is on and the pages arrive *(needs: the merge, the plugin update and a loadout re-run, which happen at close-out after the demo)*.

These Outcomes are what `Stage N green` is checked against. Changing one after
this point needs the owner's words in its amendment note: owner, <date>: "<words>".

One entry per thing the Goal, Outcomes or Risk assume about what the code does
not control (the platform, another app, a permission, the engine, a service).
Check each on the real environment before building on it. Verdict: holds, false,
or not checkable here — <why>. A false premise is a Stop condition.

## Premise 1
Assumption: a `claude -p` session started with `--plugin-dir <CP>/<plugin>` and the installed copy set false offers exactly the skills in that folder, so deleting a skill folder on this branch removes it from the session (the Stage 2 gate's running-artifact check)
Checked: 2026-11-19, Claude Code 2.1.328, scratch git dir; the gate's own `claude -p "List the names of every skill ... Reply NONE if there is none." --plugin-dir android-dev --plugin-dir infra-build --plugin-dir rust-dev --settings {"enabledPlugins":{...:false}} --max-turns 2`, before any deletion
Result: listed `android-dev:android-gradle-build`, `android-dev:android-release-signing`, `infra-build:deb-package`, `infra-build:mac-package`; no `rust-coding` (deleted in Sub-plan 2). The check is red now and can only go green by the deletions
Verdict: holds

## Premise 2
Assumption: `claude plugin validate <folder>` runs on a CP plugin folder and exits 0 on a valid one (Tasks 2.1-2.4's tests)
Checked: `claude plugin validate android-dev|browser-extensions|infra-build|git-github` from the CP root
Result: exit 0 for all four
Verdict: holds

## Premise 3
Assumption: the session-start hook delivers each stack page (or names it on overflow) from the local copy, so a skill that points at `~/.claude/vault-stacks/vault-stack-<slug>.md` still reaches the facts
Checked: Stage 1 Task 1.7 — `stack_page_loads.sh` for all seven new slugs (EV/delivery/claude.log, 8 `LOADED session_start_hook` lines) and the budget sweep (105 projects, 0 dropped); `ls ~/.claude/vault-stacks/` now → 8 copies
Result: 8 copies present; delivery proven at the Stage 1 gate
Verdict: holds
