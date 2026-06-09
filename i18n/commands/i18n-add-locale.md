---
description: Scaffold a new target locale by creating the catalog file(s) for the framework and translating from the source catalog via the translator subagent.
argument-hint: "<locale-code> [optional: --copy-only to scaffold empty entries without translating]"
---

# /i18n-add-locale

Adds a new target locale to the project's i18n setup.

## Required argument

A BCP 47 locale code: `es`, `es-MX`, `fr-CA`, `pt-BR`, `zh-CN`, `zh-TW`, `ja`, `ar`, `he`, `ru`, `pl`, `cs`, `nl`, `de`, `it`, `tr`, `ko`, `hi`, `bn`, `id`, `th`, `vi`, …

If the user uses a non-canonical form ("Spanish", "Simplified Chinese"), normalize and confirm before proceeding (`es-ES` vs `es-MX` materially differ; `zh-CN` vs `zh-TW` use different scripts).

## Steps

1. Run `detect-framework.py` to find the project's framework, source locale, and existing locale list.
2. If the requested locale is already present → switch to `/i18n-fill-gaps <locale>` instead.
3. Create the new catalog file(s) at the framework-conventional path:
   - **Android**: `res/values-<code>/strings.xml` (note `values-es`, `values-zh-rCN`)
   - **Flutter**: `lib/l10n/intl_<code>.arb` or project-specific name (preserve `@@locale` and `@key` metadata blocks from source)
   - **gettext**: `locale/<code>/LC_MESSAGES/messages.po` (initialize from `.pot` via `msginit -l <code>` if available; else handcraft the Plural-Forms header from `i18n-formats/references/gettext.md`)
   - **iOS**: `<code>.lproj/Localizable.strings` and `Localizable.stringsdict` (or new locale block in `Localizable.xcstrings`)
   - **i18next / json-i18n**: `locales/<code>/translation.json` (or whatever the project's pattern is)
   - **react-intl**: `lang/<code>.json` (or `lang/<code>/messages.json`)
   - **Vue i18n**: `locales/<code>.json` or `.yml`
   - **Rails**: `config/locales/<code>.yml` with top-level `<code>:` key
   - **Qt**: `translations/myapp_<code>.ts` — initialize via `lupdate -ts translations/myapp_<code>.ts`
   - **.NET**: `Strings.<code>.resx` sibling to `Strings.resx`
   - **Java**: `messages_<code>.properties` sibling to `messages.properties`

4. Run `extract-missing.py --target <code>` — every source key is "missing".
5. **Unless `--copy-only`**, dispatch the `translator` subagent with the full workpacket and the `i18n-formats/references/<format>.md` for the framework.
6. The agent validates with `validate-placeholders.py` before writing back.
7. Report:
   - File(s) created
   - Source keys translated
   - Plural categories emitted (`one, few, many, other` for Russian, etc.)
   - Keys flagged for review

## With --copy-only

Creates the catalog file with empty/source-text entries so a human translator (or a TMS like Crowdin / Lokalise) can fill them. No LLM dispatch.

## Notes

- For Android, also remind the user to update `<bcp47>` in `locale-config.xml` (Android 13+ per-app language) if they ship one.
- For iOS, remind to add the locale to the Xcode project (`PROJECT.pbxproj` `knownRegions`) so the build copies it.
- For Flutter, add the locale to `MaterialApp.supportedLocales`.
- The agent does NOT commit. Review with `git diff` and commit when ready.
