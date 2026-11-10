# Stage 1 premises — 2026-11-10-value-audit-reduction-plan

Goal: the owner gets correct, dated facts, working script paths, a correct readiness check and agents on the session model, before anything is removed.
Risk: LOW — small edits to known lines, one script fix with a new test

Outcomes:
- Works: a publish, promo or release skill states the current store or venue rule with the date it was checked and its source
- Works: a skill that names a bundled script names a path that resolves from any project directory
- Works: `build-readiness-check` passes a project whose `mac/Makefile` has `pkg`, and warns, naming `pkg`, on one that lacks it
- Works: a dispatched agent runs on the session's model, and a skill starts without an announce line
- A live source cannot be reached → the task stops and names the fact; nothing is rewritten from memory
- A live source contradicts the audit → the source wins and the text follows it, with the date

These Outcomes are what `Stage N green` is checked against. Changing one after
this point needs the owner's words in its amendment note: owner, <date>: "<words>".

One entry per thing the Goal, Outcomes or Risk assume about what the code does
not control (the platform, another app, a permission, the engine, a service).
Check each on the real environment before building on it. Verdict: holds, false,
or not checkable here — <why>. A false premise is a Stop condition.

## Premise 1
Assumption: the build-for-mac workflow runs `make … pkg`, not `make package`
Checked: `grep -n make /home/user/dev/infra/build-for-mac/.github/workflows/build_and_package.yml`
Result: line 87 `make -C "${{ matrix.program }}/mac" pkg \`
Verdict: holds

## Premise 2
Assumption: the real project multitor has `pkg:` and no `package:`, and the current script warns on it
Checked: `grep -nE '^(pkg|package):' /home/user/dev/anon-tools/multitor/mac/Makefile`; `bash infra-build/scripts/validate-readiness.sh /home/user/dev/anon-tools/multitor | grep mac-makefile-target`
Result: `37:pkg: payload`; warning `mac/Makefile has no 'package:' target (the workflow runs make package)`
Verdict: holds

## Premise 3
Assumption: `${CLAUDE_PLUGIN_ROOT}` is substituted in skill, command and agent Markdown bodies
Checked: WebFetch https://code.claude.com/docs/en/plugins-reference § Where each variable resolves (2026-11-10)
Result: "Skill, command, and agent content | Anywhere in the Markdown body"; "Claude Code substitutes the path inline when it loads the content"
Verdict: holds

## Premise 4
Assumption: a subagent with `model: inherit` runs on the main conversation's model
Checked: WebFetch https://code.claude.com/docs/en/sub-agents § Choose a model (2026-11-10)
Result: "inherit: use the same model as the main conversation"
Verdict: holds

## Premise 5
Assumption: the live store and venue pages Task 1.1 reads are reachable
Checked: `curl -sL -o /dev/null -w '%{http_code}'` on the 7 Preflight URLs
Result: all 200
Verdict: holds
