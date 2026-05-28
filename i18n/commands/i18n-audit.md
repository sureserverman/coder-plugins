---
description: Audit the current project's internationalization state — detect framework, find hardcoded user-facing strings, and diff translation catalogs across locales for missing or stale keys.
argument-hint: "[optional: project path; defaults to CWD]"
---

# /i18n-audit

Runs the `i18n-audit` skill end-to-end against `$ARGUMENTS` (or CWD if empty).

## Steps

1. **Framework detection** — runs `detect-framework.py`. If `none`, asks whether to recommend a framework based on the project's stack.
2. **Hardcoded scan** — runs `scan-hardcoded.py` at `--min medium`. Filters results with LLM judgment for actual user-facing strings (vs log messages, debug, assertions).
3. **Catalog gap analysis** — runs `diff-catalogs.py` per detected framework. Reports missing keys, extra keys, and placeholder mismatches per target locale.

## Output

A summary table with:
- Framework(s) detected
- Source locale / target locales
- Hardcoded user-facing strings still in source (top 10 with file:line and suggested key)
- Per-locale: missing / extra / placeholder-mismatch counts
- Next-actions: `/i18n-fill-gaps` to translate missing keys, `/i18n-add-locale <code>` to scaffold a new locale, `i18n-formats` reference for format-specific gotchas

## Notes

- Read-only — does not modify source files or catalogs.
- For format-specific gotchas surfaced during the audit, defer to the `i18n-formats` skill.
- For multi-module repos, the audit reports per-module.
