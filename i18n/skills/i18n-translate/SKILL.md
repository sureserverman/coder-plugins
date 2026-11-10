---
name: i18n-translate
description: Use when filling missing or stale translations in a project's i18n catalogs, or scaffolding a new locale from the source catalog. Trigger on "translate to <locale>", "add Spanish translations", "fill in missing translations", "translate these strings".
---

# i18n Translate

Deterministic scripts find missing keys and check placeholders; the `translator` subagent translates; this skill runs the pipeline. Never skip a step.

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

It prints a JSON workpacket: `source_locale`, `target_locale`, `framework`, `style_guide`, and `entries[]` (`key`, `source`, `placeholders`, `context`, `plural`). `context` carries ARB `@key` metadata, gettext `msgctxt` and translator comments, and Android `<!-- -->` comments.

## Step 3 — Dispatch the translator subagent

Pass the `translator` subagent:
1. The workpacket from Step 2.
2. The target catalog path.
3. Any project style guide (`STYLEGUIDE.md`, `docs/i18n-style.md`, or what the user supplied).

Batch about 30 entries per dispatch. For large catalogs, dispatch in parallel one agent per locale, never one per entry: context within a locale matters. Pass `--no-tm-lookup` in the dispatch prompt when the user wants no network lookups (offline, air-gapped, deterministic builds).

## Step 4 — Validate (script)

```bash
${CLAUDE_PLUGIN_ROOT}/skills/i18n-translate/scripts/validate-placeholders.py <translation-output.json>
```

It checks placeholder sets, ICU brace balance, required CLDR plural categories, HTML tag balance, and `%s`/`%d` swaps. On defects, re-dispatch the translator on those entries only, naming each defect. Never accept a defective translation.

Watch for these cross-format mistakes in review:

- **Renaming placeholders during translation.** `{name}` → `{nombre}` breaks the runtime call site.
- **Dropping `#` inside ICU plural body.** It's the interpolated count, not a literal.
- **Generating only `one` and `other` for Russian/Arabic/Polish catalogs.** Missing categories fall back to `other`, producing wrong grammar.
- **HTML tag substitution.** `<b>` → `<strong>` changes the rendered styling and may break a unit test selector.
- **Missing single-quote escape in Android XML.** `Don't` parses but Android logs a runtime warning and may truncate; `Don\'t` is correct.
- **Reordering JSON catalog keys.** Diffs become unreviewable and translation memory misses.

## Step 5 — Report

List locales touched, keys translated per locale, defects fixed on re-dispatch, keys left untranslated (brand names, identifiers, units), and files modified. This skill never commits; the user reviews with `git diff`.

## Scaffolding a new locale

1. Run `${CLAUDE_PLUGIN_ROOT}/skills/i18n-audit/scripts/detect-framework.py <project-root>` to find the framework, source locale, and existing locales. If the locale already exists, fill its gaps instead.
2. Create the catalog at the framework's conventional path for that locale.
3. Unless `--copy-only`, continue with Steps 2–5. With `--copy-only`, leave empty or source-text entries for a human translator or TMS, with no dispatch.

Post-scaffold reminders:
- **Android**: update `<bcp47>` in `locale-config.xml` (Android 13+ per-app language) if the project ships one.
- **iOS**: add the locale to the Xcode project's `knownRegions` so the build copies it.
- **Flutter**: add the locale to `MaterialApp.supportedLocales`.
- **RTL locales** (Arabic, Hebrew, Persian, Urdu): remind the user to check UI mirroring; catalogs carry no direction.
