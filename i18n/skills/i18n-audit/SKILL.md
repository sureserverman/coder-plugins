---
name: i18n-audit
description: Use when auditing a project for internationalization (i18n) readiness — detecting which i18n framework (if any) it uses, finding hardcoded user-facing strings that haven't been wrapped for translation yet, and diffing translation catalogs across locales for missing or stale keys. Trigger on "audit i18n", "is this app translation-ready", "check translation coverage", "find hardcoded strings", "what's missing in our French translations", "are our locales in sync", "what i18n framework does this project use", "how internationalized is this codebase".
---

# i18n Audit

Three-phase audit of a project's internationalization state. Each phase has a deterministic script that produces machine-readable output; the LLM then interprets the output and asks the user where ambiguous.

## Instructions

When invoked, identify the project root (CWD unless told otherwise). Run the three phases in order. After each phase, report results in a short table or list, then proceed to the next.

### Phase 1 — Framework detection (script)

```bash
${CLAUDE_PLUGIN_ROOT}/skills/i18n-audit/scripts/detect-framework.py <project-root>
```

Outputs JSON with detected framework(s), catalog file globs, source-language code, and target-language codes. Multiple frameworks can co-exist (e.g. Android `strings.xml` + a Flutter ARB sub-project). Report each one detected.

If detection returns `{"framework": "none"}`:
- Look at the project's language/runtime (Cargo.toml, package.json, build.gradle, pubspec.yaml, requirements.txt, go.mod, *.csproj) and consult the `i18n-formats` dispatch table to recommend a framework that matches the stack.
- Stop here unless the user wants to proceed with hardcoded-string scanning anyway.

### Phase 2 — Hardcoded string scan (script + LLM judgment)

```bash
${CLAUDE_PLUGIN_ROOT}/skills/i18n-audit/scripts/scan-hardcoded.py <project-root> [--framework <name>]
```

The script applies framework-aware heuristics:
- Skips test files, generated code, vendored deps, fixtures.
- Skips strings that look like identifiers, URLs, MIME types, regexes, log keys, or technical messages with no spaces.
- Flags strings ≥ 3 chars containing at least one space OR at least two letters and used in a UI context (passed to `setText`, `Text(...)`, JSX children, `print`/`console.log` in UI files, alert/notification APIs, button labels).
- Output: TSV of `file<TAB>line<TAB>likelihood<TAB>snippet`.

**Then apply LLM judgment.** The script's `likelihood` is heuristic-only. For each high-likelihood hit:
1. Read the surrounding context (5 lines).
2. Decide: is this actually user-facing? (Log messages, dev-only assertions, error messages thrown to programmer-facing console — these are NOT user-facing.)
3. Group findings by file and present a triage table: file, line, suggested key name, suggested replacement (call to the project's i18n API).

Never edit the source files automatically. Show the diff and ask before applying.

### Phase 3 — Catalog gap analysis (script)

```bash
${CLAUDE_PLUGIN_ROOT}/skills/i18n-audit/scripts/diff-catalogs.py <project-root> [--framework <name>] [--source-locale <code>]
```

Outputs:
- `missing[locale]` — keys present in source but absent from this locale.
- `extra[locale]` — keys in this locale that don't exist in source (likely stale).
- `stale[locale]` — keys whose source text changed after the locale was last touched (uses git blame; falls back to mtime).
- `placeholder_mismatch[locale]` — keys where the placeholder set differs between source and target.

Report counts per locale, then a sorted list of which locales need attention.

## Output schema

End the audit with a single summary block:

```
i18n Audit — <project>
  Framework:        <name> (or "none detected")
  Source locale:    <code>
  Target locales:   <list>
  Hardcoded strings (likely user-facing): <count>
  Missing translations:  locale=<count>, ...
  Stale translations:    locale=<count>, ...
  Placeholder mismatches: locale=<count>, ...

Top 5 hardcoded strings to wrap:
  1. <file>:<line> — "<snippet>"
  ...

Next actions:
  - Run /i18n:i18n-translate to translate missing keys
  - Run /i18n:i18n-translate <code> to add a new target locale
  - For format-specific gotchas, read the matching `skills/i18n-formats/references/<format>.md` (per the dispatch table in that skill)
```

## Determinism boundary

The mechanical lane now emits the shared plugin-dev finding contract. For catalog
parity and placeholder/CLDR-plural integrity, prefer running the deterministic
orchestrator over re-deriving gaps in prose:

```bash
${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh <project-root> --json
```

It discovers `validate-catalog-diff.sh` (`i18n-missing-key` / `i18n-stale-key` /
`i18n-extra-key`) and `validate-placeholders.sh` (`i18n-placeholder-mismatch`,
`i18n-missing-plural-categories`, …), wrapping the same Python the phases above
call. Report its findings verbatim. Framework detection, hardcoded-string triage,
and any translation/judgment stay LLM work.

## Notes

- For format gotchas (Android quoting, ARB metadata, gettext plural headers), consult the matching `i18n-formats/references/<format>.md` (`android.md`, `flutter-arb.md`, `gettext.md`). Do not invent escape rules from memory.
- For multi-module projects (an Android repo with separate `app/`, `lib1/`, `lib2/` modules each with their own `res/values*/strings.xml`), the script runs per-module and reports per-module.
- The diff script does NOT fix stale translations. Use `/i18n:i18n-translate` to re-translate them.
