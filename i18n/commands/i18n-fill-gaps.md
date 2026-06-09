---
description: Find missing translations across all configured target locales and fill them via the translator subagent, with placeholder and CLDR-plural validation before write-back.
argument-hint: "[optional: locale code (single locale only)] [--include-stale]"
---

# /i18n-fill-gaps

Drives the `i18n-translate` skill across one or more target locales.

## Scoping

Given `$ARGUMENTS`:

1. **Empty** → fill gaps for ALL detected target locales.
2. **A single locale code** (`es`, `fr-CA`, `zh-CN`, `pt-BR`) → only that locale.
3. **`--include-stale`** flag (with or without a locale) → also fill keys where the translation exists but the placeholder set differs from the source (stale translations).

## Steps

1. Run `detect-framework.py` to find the project's framework(s) and source locale.
2. For each target locale in scope, run `extract-missing.py` to build a workpacket.
3. If a workpacket has 0 entries, skip that locale.
4. Dispatch the `translator` subagent per locale (in parallel, one agent per locale), passing the workpacket plus the relevant `i18n-formats/references/<format>.md`.
5. The agent self-validates with `validate-placeholders.py` before writing back. Any defects it can't fix on its own are reported back here.
6. Report a summary table: locale → entries translated → defects fixed → files modified → keys flagged for human review (brand names, ambiguous source).

## Notes

- Never commits or pushes. After the run, ask the user to review with `git diff` and commit when ready.
- The `translator` agent is sonnet-pinned. For a 200-entry catalog × 5 locales, expect ~10 dispatches.
- For style guides (formality, brand glossary, do-not-translate list), read `STYLEGUIDE.md` / `docs/i18n-style.md` if present and pass to the agent. Otherwise prompt the user once before fanning out.
- For RTL target locales (ar, he, fa, ur), the agent only translates strings; remind the user to verify their UI's mirroring.
