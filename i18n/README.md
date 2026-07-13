# i18n

Internationalization plugin for any project that has user-facing strings. Splits the work between deterministic scripts (framework detection, hardcoded-string scanning, catalog diffing, placeholder validation) and the LLM (translation quality, judgment on what's actually user-facing).

## Install

```
/plugin marketplace add sureserverman/coder-plugins
/plugin install i18n@coder-plugins
```

## What it covers

The audit + translate + formats skills know these catalog formats and their gotchas:

| Ecosystem | Format | Notes |
|---|---|---|
| GNU gettext (C/C++/Python/Rust/Go/PHP/...) | `.po` / `.pot` | CLDR plurals via `Plural-Forms` header, `msgctxt` context, `xgettext` extraction |
| JS/TS (i18next, react-i18next) | nested JSON or flat JSON | ICU MessageFormat (i18next-icu), interpolation `{{name}}`, `_plural` suffix or ICU |
| JS/TS (react-intl / FormatJS) | JSON id→message | ICU MessageFormat is native, `formatjs extract` for extraction |
| JS/TS (Vue i18n) | JSON or YAML | Linked messages `@:foo`, list/named interpolation |
| Android | `res/values*/strings.xml` | Quoting rules, `<![CDATA[`, positional `%1$s`, `<plurals>` with CLDR categories |
| iOS / macOS | `.strings`, `.stringsdict`, `.xcstrings` (Xcode 15+) | `NSStringLocalizedFormatKey` for plurals, key-value pairs |
| Flutter | `.arb` | Metadata under `@key` (description, placeholders), ICU plurals/selects |
| Rails | `config/locales/*.yml` | `i18n-tasks` for gap detection, pluralization keys (`one`, `other`, ...) |
| Django | `locale/<lang>/LC_MESSAGES/django.po` | `makemessages`, `compilemessages`, `{% trans %}` / `{% blocktrans %}` |
| Qt | `.ts` (source) + `.qm` (compiled) | `lupdate` / `lrelease`, plural forms via `<numerusform>` |
| .NET | `.resx` | XML resource format, ResourceManager, satellite assemblies |
| Java | `.properties` (ISO-8859-1 historically, UTF-8 in Java 9+) | `MessageFormat` placeholders `{0}` |

## Skills

- **`i18n-audit`** — detects the framework, finds hardcoded strings still in source, diffs translation catalogs across locales for missing/stale keys. Ships `scripts/detect-framework.py`, `scripts/scan-hardcoded.py`, `scripts/diff-catalogs.py`. Triggers on "audit i18n", "check translation coverage", "find hardcoded strings", "is this app translation-ready".
- **`i18n-translate`** — drives the LLM translation pass via the `translator` subagent. Preserves placeholders (printf, ICU, Handlebars, positional Android format specifiers) and CLDR plural categories. Ships `scripts/extract-missing.py` and `scripts/validate-placeholders.py`. Triggers on "translate to <locale>", "fill in missing translations", "add Spanish translations".
- **`i18n-formats`** — reference doc with per-format gotchas. Loaded on demand by the other two skills.

## Invoking the skills

The skills are model-triggered and also invocable directly:

- `/i18n:i18n-audit` — run the audit pipeline (framework detection → hardcoded scan → catalog gaps).
- `/i18n:i18n-translate` — fill missing keys across configured locales, or scaffold a new locale, via the `translator` subagent. (Argument scoping and new-locale scaffolding — the `--include-stale` and `--copy-only` flows and the per-framework catalog paths — are documented in the skill.)

## Agent

- **`translator`** (sonnet, write-capable) — does the actual translation. Reads source catalog excerpt + target locale + style guide, writes target catalog entries with placeholders preserved and plurals expanded to the target's CLDR categories. Validates with `validate-placeholders.py` before returning.

## How LLM and scripts split the work

| Step | Who does it | Why |
|---|---|---|
| Detect i18n framework | Python script | Deterministic, signature-based |
| List source/target catalogs | Python script | Filesystem walk + parse |
| Find missing keys per locale | Python script | Set difference |
| Decide which hardcoded string is user-facing | LLM | Requires reading surrounding code |
| Translate text into target locale | LLM (translator subagent) | The only thing only an LLM can do well |
| Validate placeholder preservation in output | Python script | Regex/structural check, deterministic |
| Expand plural forms to target CLDR categories | LLM + format reference | Per-locale rule + linguistic judgment |
| Write back to catalog files | LLM (preserves comments/order) | gettext metadata, ARB `@key` blocks, Android `<!-- -->` comments are easy to clobber with naive serializers |

Nothing autoposts. Nothing rewrites source code without showing the diff first. Translations are written to catalog files, not committed.
