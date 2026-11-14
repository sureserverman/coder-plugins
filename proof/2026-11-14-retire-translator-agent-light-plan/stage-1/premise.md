# Stage 1 premises — 2026-11-14-retire-translator-agent-light-plan

Goal: for anyone with the i18n plugin installed, translation works with no `translator` agent, and nothing in the repo says there is one.
Risk: (none)

Outcomes:
- Works: the catalog is filled. One locale with about 30 entries or fewer is translated in the session, with no subagent. A larger job gets one `general-purpose` subagent per locale. A translation that breaks a placeholder or a plural is fixed and checked again with `validate-placeholders.py` before the report.
- A source string is too ambiguous to translate → that entry is left unwritten, and the report lists it.

These Outcomes are what `Stage N green` is checked against. Changing one after
this point needs the owner's words in its amendment note: owner, <date>: "<words>".

One entry per thing the Goal, Outcomes or Risk assume about what the code does
not control (the platform, another app, a permission, the engine, a service).
Check each on the real environment before building on it. Verdict: holds, false,
or not checkable here — <why>. A false premise is a Stop condition.

## Premise 1
Assumption: staged-planning's plan execution routes a dispatched catalog-translation task to an installed agent whose description matches, else to `general-purpose`, and names no agent of another plugin.
Checked: grep -n -i -E 'catalog|translat|general-purpose' ~/.claude/plugins/cache/staged-planning/planning/2.3.0/skills/executing-plans/references/stack-routing.md
Result: line 52 — "catalog translation | an installed agent whose description matches the stack; otherwise `general-purpose` | the stack's skill, if one is installed"; no `i18n:translator` named.
Verdict: holds

## Premise 2
Assumption: the installed Claude Code CLI can run the live gate as written — load a plugin from a directory (`--plugin-dir`), take an `--allowedTools` list and a `--permission-mode`.
Checked: claude --version; claude --help | grep -E -- '--plugin-dir|--allowedTools|--permission-mode'
Result: 2.1.325 (Claude Code); all three flags listed.
Verdict: holds

## Premise 3
Assumption: a `general-purpose` subagent can load `i18n-translate` from disk when the plugin is not enabled (it has Read; stack-routing tells the executor to inject the skill path).
Checked: grep -n 'general-purpose' stack-routing.md (line 148: "dispatch a `general-purpose` subagent and **inject** ...")
Result: the routing reference documents the inject-from-disk path.
Verdict: holds
