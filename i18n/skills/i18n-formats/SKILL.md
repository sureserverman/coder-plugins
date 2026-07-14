---
name: i18n-formats
description: Reference for i18n catalog format gotchas — gettext .po, i18next JSON, Android strings.xml, iOS .strings/.stringsdict, Flutter ARB. Use when authoring or modifying translation catalogs, format-specific escaping or quoting matters, or expanding plural forms for a non-English target.
disable-model-invocation: true
---

# i18n Formats Reference

Source of truth for per-format escaping, quoting, plural-form rules, and metadata conventions. **Read only the reference file for your format** (table below) before generating or editing catalog files — don't load the whole set. Do not invent rules from memory.

## Format dispatch — read the file for your detected framework

| Format / framework | Reference file |
|---|---|
| GNU gettext `.po`/`.pot` (Python, C/C++, Rust rust-i18n, Go go-i18n, PHP, Ruby) | [`references/gettext.md`](references/gettext.md) |
| i18next / react-i18next JSON (React, React Native, Next.js, Node) | [`references/i18next.md`](references/i18next.md) |
| react-intl / FormatJS JSON | [`references/react-intl.md`](references/react-intl.md) |
| Vue i18n JSON/YAML | [`references/vue-i18n.md`](references/vue-i18n.md) |
| Android `res/values*/strings.xml` | [`references/android.md`](references/android.md) |
| iOS `.strings` / `.stringsdict` / `.xcstrings` | [`references/ios.md`](references/ios.md) |
| Flutter `.arb` | [`references/flutter-arb.md`](references/flutter-arb.md) |
| Rails `config/locales/*.yml` | [`references/rails.md`](references/rails.md) |
| Django `locale/*/LC_MESSAGES/django.po` | [`references/django.md`](references/django.md) |
| Qt `.ts` → `.qm` | [`references/qt.md`](references/qt.md) |
| .NET `.resx` | [`references/dotnet-resx.md`](references/dotnet-resx.md) |
| Java `.properties` | [`references/java-properties.md`](references/java-properties.md) |

When source and target use different formats, read both files. The CLDR plural categories, RTL guidance, and cross-format mistakes below apply to **every** format and are kept here on purpose.

## CLDR plural categories

CLDR (Common Locale Data Repository) defines six possible plural categories: `zero, one, two, few, many, other`. Each language uses a subset. Authoritative reference: <https://cldr.unicode.org/index/cldr-spec/plural-rules>.

Common subsets:

| Family | Languages | Categories required |
|---|---|---|
| Only `other` | Japanese (ja), Korean (ko), Chinese (zh), Thai (th), Vietnamese (vi), Indonesian (id) | `other` |
| `one, other` | English (en), German (de), Spanish (es), Italian (it), Portuguese (pt), Dutch (nl), Swedish (sv), Danish (da), Norwegian (no), Finnish (fi), Greek (el), Turkish (tr) | `one`, `other` |
| `one, other` w/ French rules | French (fr) | `one`, `other` (with French rounding: 1.5 → one) |
| Slavic — `one, few, many, other` | Russian (ru), Ukrainian (uk), Polish (pl), Czech (cs), Slovak (sk) | `one`, `few`, `many`, `other` |
| Arabic | Arabic (ar) | `zero`, `one`, `two`, `few`, `many`, `other` |
| Welsh | Welsh (cy) | `zero`, `one`, `two`, `few`, `many`, `other` |
| Romanian | Romanian (ro) | `one`, `few`, `other` |
| Latvian | Latvian (lv) | `zero`, `one`, `other` |
| Lithuanian | Lithuanian (lt) | `one`, `few`, `many`, `other` |
| Hebrew | Hebrew (he) | `one`, `two`, `many`, `other` |

Always emit all required categories for the target locale, even if the source has only `one` and `other`. The runtime picks by CLDR rule; a missing category falls through to `other`, producing grammatically wrong text for many counts.

## RTL languages (Arabic, Hebrew, Persian, Urdu)

The catalog format doesn't carry direction — the framework's runtime does. The translator's job is just translation. Remind the user to verify their UI:

- CSS: `[dir="rtl"]` selectors, `start`/`end` margin/padding instead of `left`/`right`.
- iOS: `Bundle.main.preferredLocalizations` + `UIView.userInterfaceLayoutDirection`.
- Android: `android:layoutDirection="locale"`, `android:supportsRtl="true"` in manifest, use `start`/`end` gravity.
- Web: `<html dir="rtl">`, logical CSS properties.
- Mirror icons that have direction (back arrows, sliders, progress).

## Common cross-format mistakes

- **Renaming placeholders during translation.** `{name}` → `{nombre}` breaks the runtime call site.
- **Dropping `#` inside ICU plural body.** It's the interpolated count, not a literal.
- **Generating only `one` and `other` for Russian/Arabic/Polish catalogs.** Missing categories fall back to `other`, producing wrong grammar.
- **HTML tag substitution.** `<b>` → `<strong>` changes the rendered styling and may break a unit test selector.
- **Missing single-quote escape in Android XML.** `Don't` parses but Android logs a runtime warning and may truncate; `Don\'t` is correct.
- **Reordering JSON catalog keys.** Diffs become unreviewable and translation memory misses.
