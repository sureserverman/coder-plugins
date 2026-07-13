---
name: i18n-translate
description: Use when filling missing or stale translations in a project's existing i18n catalogs, or scaffolding a new locale by translating from the source catalog. Trigger on "translate to <locale>", "add Spanish translations", "fill in missing translations", "translate these strings", "add a new locale", "machine-translate this catalog", "translate the app to <language>". Preserves placeholders (printf, ICU MessageFormat, Handlebars, positional Android format specifiers) and expands plural forms to the target locale's CLDR plural categories.
---

# i18n Translate

LLM-driven translation pass over a project's translation catalogs. Splits the work: deterministic scripts find missing keys and validate placeholder preservation; the `translator` subagent does the actual translation; this skill orchestrates.

## Instructions

When invoked, follow these steps in order. Never skip a step — each catches a class of regression.

### Step 1 — Resolve scope

Ask (or infer from `$ARGUMENTS`):
- **Target locale(s)** — BCP 47 or Android-style codes. If the user says "Spanish", clarify whether they mean `es`, `es-ES`, `es-MX`, etc. The CLDR rules differ.
- **Source locale** — usually `en`. Verify against the framework's convention (Android `values/`, Flutter `_en.arb`, gettext `.pot`, i18next `locales/en.json`).
- **Which keys** — all missing, only `placeholder_mismatch`, or a specific subset.

If the project hasn't been audited yet, run the `i18n-audit` skill first.

### Step 2 — Extract missing entries (script)

```bash
${CLAUDE_PLUGIN_ROOT}/skills/i18n-translate/scripts/extract-missing.py <project-root> --framework <name> --target <locale> [--include-stale]
```

Outputs a JSON workpacket:

```json
{
  "source_locale": "en",
  "target_locale": "es",
  "framework": "i18next",
  "style_guide": null,
  "entries": [
    {"key": "save_button", "source": "Save", "placeholders": [], "context": null, "plural": false},
    {"key": "items_count", "source": "{count, plural, one {# item} other {# items}}", "placeholders": ["{count}"], "context": null, "plural": true},
    ...
  ]
}
```

For ARB, also pulls the `@key` metadata (description, placeholders). For gettext, pulls `msgctxt` and `# Translator-comment:` lines. For Android XML, pulls preceding `<!-- comment -->`. These go into `context`.

### Step 3 — Look up the format gotchas (skill load)

Read the detected framework's reference file under `skills/i18n-formats/references/` (pick it from the dispatch table in `skills/i18n-formats/SKILL.md`) before dispatching. The translator subagent will use it to:
- Pick the right CLDR plural categories (Arabic has 6, Russian has 3 in some apps but the full CLDR is `one, few, many, other`, English has `one, other`, Japanese has only `other`).
- Apply per-format escaping (Android `\'`, single-quote rule; ARB JSON-escape; gettext `\"`; XML entities; iOS `%@`).
- Preserve placeholder syntax exactly.

### Step 4 — Dispatch the translator subagent

Use the `translator` subagent. Pass it:
1. The workpacket JSON from step 2.
2. The relevant `i18n-formats/references/<format>.md` file(s) (one for source format, one for target format if different).
3. Any project-specific style guide the user supplied or that exists at `STYLEGUIDE.md` / `docs/i18n-style.md` / similar.
4. Batch size — default 30 entries per dispatch for catalogs <300 entries, else split into multiple dispatches.

For large catalogs (>200 entries), dispatch multiple `translator` agents in parallel — one per locale, NOT one per entry. Translation context within a locale matters.

The translator agent is instructed to consult established translation memories (Microsoft Language Portal, Mozilla Transvision, MyMemory) for short common UI strings before inventing a translation — `Save`, `Cancel`, `Settings`, etc. should land on canonical industry-standard variants for the target locale. If the project is offline or the user wants to suppress network lookups (privacy, deterministic builds, air-gapped), pass `--no-tm-lookup` in the dispatch prompt and the agent will translate from its own knowledge only.

### Step 5 — Validate (script)

Before writing back, run:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/i18n-translate/scripts/validate-placeholders.py <translation-output.json>
```

This checks:
- Placeholder set in translation == placeholder set in source. If `{count}` vanishes from a Spanish translation of "You have {count} items", that's a defect.
- ICU MessageFormat structure is balanced (every `{` has a matching `}`).
- Required CLDR plural categories are present for the target locale. Spanish requires `one, other`. Russian requires `one, few, many, other`. Arabic requires `zero, one, two, few, many, other`.
- HTML tags balanced if source has tags.
- No accidental swap of `%s` for `%d` or vice versa.

If validation reports defects: hand them back to the `translator` subagent with the specific defects, ask for a corrected pass on those entries only. Do NOT silently accept defective translations.

### Step 6 — Write back to catalogs

The translator subagent has Edit + Write — it writes directly. Important per-format rules (the agent's prompt enforces these, but verify in review):
- **gettext .po**: preserve header block (Plural-Forms, Content-Type), keep key order, write `msgstr[0]`, `msgstr[1]`, etc. for plurals matching the target's `Plural-Forms` count.
- **ARB**: preserve `@key` metadata blocks unchanged.
- **Android XML**: preserve `<!-- comment -->` blocks and `<resources>` attributes; escape `'`, `"`, `\n`, `\@`, `\?`; use `<plurals>` for plural keys.
- **JSON (i18next/react-intl)**: preserve key order and nested structure; use the project's existing plural convention (i18next `_plural` suffix vs ICU MessageFormat inside one string).
- **iOS .strings**: preserve comments `/* */`; key-value `"key" = "value";` line per entry; UTF-16 BOM if the original had one.
- **Rails YAML**: preserve top-level locale key, indentation, and key order.

### Step 7 — Final report

After write-back, report:
- Locales touched
- Keys translated per locale
- Validation defects fixed in re-dispatch
- Any keys the agent declined to translate (e.g. brand names, code identifiers, units) — list them so the user can sanity check
- Files modified — let the user review with `git diff` before committing

## Scoping from arguments

When invoked with `$ARGUMENTS`:

1. **Empty** → fill gaps for ALL detected target locales.
2. **A single locale code** (`es`, `fr-CA`, `zh-CN`, `pt-BR`) → only that locale.
3. **`--include-stale`** flag (with or without a locale) → also fill keys where the translation exists but the placeholder set differs from the source (stale translations).

## Scaffolding a new locale

When the request is to add a brand-new target locale rather than fill gaps in an existing one:

1. Run `detect-framework.py` to find the project's framework, source locale, and existing locale list.
2. If the requested locale is already present → redirect to filling gaps for that locale instead (see Step 1 above).
3. Create the new catalog file(s) at the framework-conventional path:
   - **Android**: `res/values-<code>/strings.xml` (note `values-es`, `values-zh-rCN`)
   - **Flutter**: `lib/l10n/intl_<code>.arb` (preserve `@@locale` and `@key` metadata blocks from source)
   - **gettext**: `locale/<code>/LC_MESSAGES/messages.po` (initialize from `.pot` via `msginit -l <code>` if available; else handcraft the Plural-Forms header)
   - **iOS**: `<code>.lproj/Localizable.strings` and `.stringsdict` (or a new locale block in `Localizable.xcstrings`)
   - **i18next / json-i18n**: `locales/<code>/translation.json`
   - **react-intl**: `lang/<code>.json`
   - **Vue i18n**: `locales/<code>.json` or `.yml`
   - **Rails**: `config/locales/<code>.yml` with top-level `<code>:` key
   - **Qt**: `translations/myapp_<code>.ts` (initialize via `lupdate`)
   - **.NET**: `Strings.<code>.resx`
   - **Java**: `messages_<code>.properties`
4. **Unless `--copy-only`**, continue with Steps 4–7 above (extract, dispatch the `translator` subagent, validate, write back).

With `--copy-only`: create the catalog with empty/source-text entries for a human translator or TMS (Crowdin / Lokalise) to fill. No LLM dispatch.

Post-scaffold reminders:
- **Android**: update `<bcp47>` in `locale-config.xml` (Android 13+ per-app language) if the project ships one.
- **iOS**: add the locale to the Xcode project's `knownRegions` so the build copies it.
- **Flutter**: add the locale to `MaterialApp.supportedLocales`.

## Notes

- This skill never commits or pushes. The translator subagent writes to files; the user reviews and commits.
- For per-format translation gotchas, ALWAYS consult the matching `i18n-formats/references/<format>.md`. Do not invent escape rules.
- For locales with right-to-left text direction (Arabic, Hebrew, Persian, Urdu), also remind the user to verify their UI's mirroring (CSS `dir="rtl"`, `start`/`end` margins, icon flipping). The catalogs themselves don't carry direction; the framework's runtime does.
- Translation is a quality-driven LLM task; do not delegate it to a smaller model. The `translator` agent is sonnet-pinned for a reason — haiku produces worse translations, especially for idioms, plurals, and short UI strings where context is sparse.
