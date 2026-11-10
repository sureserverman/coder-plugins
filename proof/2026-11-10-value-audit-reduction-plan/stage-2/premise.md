# Stage 2 premises — 2026-11-10-value-audit-reduction-plan

Goal: the owner's Android, browser-extension, translation and release-promo components hold their core and nothing a model already supplies.
Risk: MEDIUM — the cuts are judgment; a cut that drops a core line is silent unless a marker or the gate's reader catches it

Outcomes:
- Works: each shrunk skill still gives the owner fact, script run line or house rule its Dispositions row lists, and triggers on the same requests as before
- Works: `/promote-release` drafts each channel's post in the session, using that channel's skill
- Works: a request that used to load a retired skill is handled by the model with no skill, and nothing in the repo points at the retired name
- A task finds a Stays item missing from the file it is meant to be in → it stops and reports; it does not invent the content
- A plan elsewhere names a retired agent → staged-planning's router falls back to `general-purpose`

These Outcomes are what `Stage N green` is checked against. Changing one after
this point needs the owner's words in its amendment note: owner, <date>: "<words>".

One entry per thing the Goal, Outcomes or Risk assume about what the code does
not control (the platform, another app, a permission, the engine, a service).
Check each on the real environment before building on it. Verdict: holds, false,
or not checkable here — <why>. A false premise is a Stop condition.

## Premise 1
Assumption: every Stays item the Dispositions table names is present in its file before the cuts
Checked: `grep -cF <marker> <file>` for the 16 markers of Tasks 2.1–2.4's Tests (play data-safety table, KEYSTORE_BASE64, validateDebugScreenshotTest, SKIPPED, ui-grading-rubric.md, tabLabels, amo-check.py, single-browser, $count$, knownRegions, "Renaming placeholders" in i18n-formats, translation memory, validate-placeholders, drive-by, "Show HN: ", #SelfHosted)
Result: every count >= 1
Verdict: holds

## Premise 2
Assumption: staged-planning's router falls back to `general-purpose` when no installed agent matches (so retiring post-drafter breaks no route)
Checked: `grep -n general-purpose ~/.claude/plugins/cache/staged-planning/planning/1.4.2/skills/dispatching-parallel-agents/references/stack-routing.md`
Result: line 52 "an installed agent whose description matches the stack; otherwise `general-purpose`"; line 57 "Nothing above fits | `general-purpose`"
Verdict: holds

## Premise 3
Assumption: no open plan in the vault names a Stage 2 retiring component
Checked: `grep -rn 'mock-server-from-app-sources|i18n-formats|post-drafter|android-ui-practices|standard-tools-frameworks' /mnt/vault/Portfolio/*/*/plans/`
Result: hits only in closed coder-plugins plans (2026-07-13, 07-28, 08-27, 10-15), all with Completed lines
Verdict: holds

## Premise 4
Assumption: the engineering-skills port copies these components
Checked: not checked — the port is a separate repo and a later re-port (Task 3.6 files it)
Result: —
Verdict: not checkable here — the re-port is out of scope; Task 3.6 records it in the backlog
