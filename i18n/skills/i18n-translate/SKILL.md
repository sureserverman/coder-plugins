---
name: i18n-translate
description: Use when filling missing or stale translations in a project's i18n catalogs, or scaffolding a new locale from the source catalog. Trigger on "translate to <locale>", "add Spanish translations", "fill in missing translations", "translate these strings".
---

# i18n Translate

Deterministic scripts find missing keys and check placeholders; this skill runs the pipeline and does the translating. Never skip a step.

## Step 1 — Resolve scope

From `$ARGUMENTS` or by asking:
- **Target locale(s)** — empty means all detected target locales. Clarify a bare language name (`es`, `es-ES`, or `es-MX`?).
- **Source locale** — usually `en`.
- **`--include-stale`** — also refill keys whose placeholder set differs from the source.

If the project hasn't been audited yet, run the `i18n-audit` skill first.

## Step 2 — Extract missing entries (script)

```bash
${CLAUDE_PLUGIN_ROOT}/skills/i18n-translate/scripts/extract-missing.py <project-root> --framework <name> --target <locale> [--include-stale]
```

It prints a JSON workpacket: `source_locale`, `target_locale`, `framework`, `style_guide`, and `entries[]` (`key`, `source`, `placeholders`, `context`, `plural`). `context` is null for missing and stale entries: when a short string is ambiguous, read its ARB `@key` metadata, gettext `msgctxt` or preceding Android comment from the source catalog yourself.

## Step 3 — Translate and write back

One locale with about 30 entries or fewer: translate it in this session. More locales or a larger catalog: dispatch one `general-purpose` subagent per locale, in parallel. Never one per entry: context within a locale matters. Its brief carries the workpacket from Step 2, the target catalog path, any project style guide (`STYLEGUIDE.md`, `docs/i18n-style.md`, or what the user supplied) and these rules:

- The style guide wins over any other source (formality, glossary, do-not-translate list).
- Keep every placeholder, format specifier and tag with identical syntax.
- Collect the translations as Step 4's input: `{"target_locale": ..., "framework": ..., "entries": [{"key": ..., "source": ..., "translation": ...}]}`. A subagent runs Step 4 on its own locale before it returns.
- Once Step 4 passes, write to the target catalog directly. Keep its comments, metadata blocks, key order and indentation.
- Follow the project's existing plural convention, and emit every CLDR plural category the target locale needs.
- When an entry cannot be translated with confidence (ambiguous source, missing context), leave it unwritten and list it in the report.

## Step 4 — Validate (script)

```bash
${CLAUDE_PLUGIN_ROOT}/skills/i18n-translate/scripts/validate-placeholders.py <translation-output.json>
```

It checks placeholder sets, ICU brace balance, required CLDR plural categories, HTML tag balance, and `%s`/`%d` swaps. On defects, fix those entries only and run the validator again. Never accept a defective translation.

Watch for these cross-format mistakes in review:

- **Renaming placeholders during translation.** `{name}` → `{nombre}` breaks the runtime call site.
- **Dropping `#` inside ICU plural body.** It's the interpolated count, not a literal.
- **Generating only `one` and `other` for Russian/Arabic/Polish catalogs.** Missing categories fall back to `other`, producing wrong grammar.
- **HTML tag substitution.** `<b>` → `<strong>` changes the rendered styling and may break a unit test selector.
- **Missing single-quote escape in Android XML.** `Don't` parses but Android logs a runtime warning and may truncate; `Don\'t` is correct.
- **Reordering JSON catalog keys.** Diffs become unreviewable and translation memory misses.

## Step 5 — Report

List locales touched, keys translated per locale, defects fixed after validation, keys left untranslated (brand names, identifiers, units, entries left unwritten), and files modified. This skill never commits; the user reviews with `git diff`.

## Scaffolding a new locale

1. Run `${CLAUDE_PLUGIN_ROOT}/skills/i18n-audit/scripts/detect-framework.py <project-root>` to find the framework, source locale, and existing locales. If the locale already exists, fill its gaps instead.
2. Create the catalog at the framework's conventional path for that locale.
3. Unless `--copy-only`, continue with Steps 2–5. With `--copy-only`, leave empty or source-text entries for a human translator or TMS, with no dispatch.

Post-scaffold reminders:
- **Android**: update `<bcp47>` in `locale-config.xml` (Android 13+ per-app language) if the project ships one.
- **iOS**: add the locale to the Xcode project's `knownRegions` so the build copies it.
- **Flutter**: add the locale to `MaterialApp.supportedLocales`.
- **RTL locales** (Arabic, Hebrew, Persian, Urdu): remind the user to check UI mirroring; catalogs carry no direction.
