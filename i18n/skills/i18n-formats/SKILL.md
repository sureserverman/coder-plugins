---
name: i18n-formats
description: Reference for per-format gotchas across i18n catalog formats — gettext .po (CLDR plural-forms headers, msgctxt, msgid_plural), i18next JSON, react-intl/FormatJS, Vue i18n, Android strings.xml (quoting, plurals, positional %1$s), iOS .strings/.stringsdict/.xcstrings, Flutter ARB (@key metadata, ICU plurals), Rails YAML (i18n-tasks, locale top-key), Django gettext, Qt .ts (numerusform), .NET .resx, Java .properties (Unicode escape rules), CLDR plural categories per language. Use when authoring or modifying translation catalogs, when format-specific escaping or quoting matters, or when expanding plural forms for a non-English target.
---

# i18n Formats Reference

Source of truth for per-format escaping, quoting, plural-form rules, and metadata conventions. Read the section for your format before generating or editing catalog files. Do not invent rules from memory.

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

## GNU gettext (.po / .pot)

Used by: Python, Django, C/C++, Rust (rust-i18n), Go (go-i18n), PHP, Ruby (gettext gem).

```po
# Translator-comment
#. Extracted-comment (developer)
#: src/foo.c:42
#, c-format
msgctxt "menu"
msgid "Save"
msgid_plural "Saves"
msgstr[0] "Guardar"
msgstr[1] "Guardar"
```

Rules:

- **Plural-Forms header** in the file's metadata block determines `nplurals` and the index formula. Russian's typical header:
  `Plural-Forms: nplurals=4; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<12 || n%100>14) ? 1 : n%10==0 || (n%10>=5 && n%10<=9) || (n%100>=11 && n%100<=14) ? 2 : 3);`
  Don't write or change this by hand — generate via `msginit -l ru` or copy from a reference.
- **msgctxt** disambiguates duplicate `msgid` (e.g., "Open" the verb vs "Open" the adjective). Keep it.
- **Placeholders**: printf-style (`%s`, `%d`, `%1$s` positional). For `#, c-format` entries, validation tools (`msgfmt --check`) verify the spec matches between source and translation. Don't drop them.
- **Escaping**: `\n`, `\"`, `\\`. Multi-line via concatenation of `"..."` strings.
- **Extraction**: `xgettext -k_ -kN_ src/*.c -o messages.pot`. Update locale `.po`: `msgmerge --update locale/es/LC_MESSAGES/messages.po messages.pot`.

## JSON — i18next / react-i18next

Used by: React, React Native, Next.js (often), Node.js.

```json
{
  "common": {
    "save": "Save",
    "items_one": "{{count}} item",
    "items_other": "{{count}} items"
  }
}
```

Rules:

- **Placeholders**: `{{name}}` (double braces). i18next-icu adds ICU MessageFormat support, then `{name, plural, one {…} other {…}}` works in a single string.
- **Plurals**: either suffix style (`items_one`, `items_other`, `items_few`, `items_many` for Russian — i18next picks the right one) OR ICU. Don't mix in a single project.
- **Nested keys** are namespaced by dots at runtime: `t('common.save')`.
- **No trailing commas**, no comments. Pure JSON.
- **Extraction**: `i18next-parser` or `i18next-extract` walk source for `t('key')` calls.
- **Watch for**: i18next falls back to the source language for missing keys silently. Use `i18next-parser`'s `removeUnusedKeys: true` carefully — it can delete keys used only via dynamic interpolation.

## JSON — react-intl / FormatJS

```json
{
  "save_button": {
    "defaultMessage": "Save",
    "description": "Button on the editor toolbar"
  },
  "items_count": {
    "defaultMessage": "{count, plural, one {# item} other {# items}}",
    "description": "Item count in the sidebar"
  }
}
```

Rules:

- **Placeholders**: ICU MessageFormat native (`{name}`, `{n, plural, ...}`, `{x, select, ...}`).
- **Stable IDs** required if you want translation memory to work across releases. Use `id` field explicitly:
  ```json
  {"id": "editor.save", "defaultMessage": "Save", "description": "..."}
  ```
- **Extraction**: `formatjs extract 'src/**/*.{ts,tsx}' --out-file lang/en.json`.
- **Compile** for the runtime: `formatjs compile lang/en.json --out-file dist/en.json`.
- `#` inside ICU plural body interpolates the count.

## JSON / YAML — Vue i18n

```json
{ "hello": "Hi, {name}", "items": "no items | {count} item | {count} items" }
```

Rules:

- **Placeholders**: `{name}` (single brace) by default. List-style: `{0}`, `{1}`.
- **Plurals** (built-in, not CLDR-strict): pipe-separated forms `zero | one | many`. Vue i18n's built-in pluralization is simplistic — for Russian and Arabic, switch to ICU via the `@intlify/vue-i18n` plugin and use full ICU MessageFormat.
- **Linked messages**: `@:foo.bar` references another key — preserve the link, don't expand.
- **Modifiers**: `@.lower:foo` lowercases the linked message — preserve.

## Android — `res/values*/strings.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<resources>
    <!-- Save button on the editor toolbar -->
    <string name="save">Save</string>
    <string name="save_quoted">Don\'t go</string>
    <string name="save_format">Hello %1$s, you have %2$d items</string>
    <plurals name="items">
        <item quantity="one">%d item</item>
        <item quantity="other">%d items</item>
    </plurals>
</resources>
```

Rules:

- **Escaping** (Android docs <https://developer.android.com/guide/topics/resources/string-resource>):
  - `'` → `\'` (always escape single quotes)
  - `"` → `\"`
  - `\n` for newline, `\t` for tab
  - `\\` for backslash
  - `\@` `\?` to escape resource refs and special chars at start
  - Leading/trailing whitespace requires `<string>"   Hello   "</string>` (wrap in `"`)
  - HTML allowed: `<b>`, `<i>`, `<u>`. For complex markup, use `<![CDATA[...]]>` and `Html.fromHtml()`.
- **Positional placeholders**: `%1$s`, `%2$d` (always specify the position for multi-arg strings — `%s` alone is fine for one arg). String formatting via `getString(R.string.foo, arg1, arg2)`.
- **Plurals via `<plurals>` element**. Quantity attribute must be one of CLDR categories. For `values-ru/strings.xml` you need `one`, `few`, `many`, `other`. Use `getQuantityString(R.plurals.items, count, count)`.
- **Locale directory naming**: `values-es`, `values-es-rMX`, `values-zh-rCN` (note `-r` before region code). `values-en-rGB` is British English.
- **string-array** for ordered lists, **integer-array** for numbers. Translate `<string-array><item>…</item></string-array>` in order.
- **`translatable="false"`** on `<string>` excludes it from translation tools. Respect it.

## iOS — `.strings`, `.stringsdict`, `.xcstrings`

### .strings (legacy, still common)

```
/* Save button on the editor toolbar */
"editor.save" = "Save";
"editor.discard" = "Don't save";
```

- Key-value pairs, semicolon-terminated.
- `/* */` comments only.
- `\"`, `\n`, `\t`, `\\`. UTF-16 typical (UTF-8 increasingly accepted).
- Format placeholders: `%@` (Objective-C object), `%d`, `%lld`, `%f`, `%1$@`, `%2$d`. Use `String(format:NSLocalizedString(…), …)`.

### .stringsdict (XML plist for plurals)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "...">
<plist version="1.0">
<dict>
    <key>%d items</key>
    <dict>
        <key>NSStringLocalizedFormatKey</key>
        <string>%#@items@</string>
        <key>items</key>
        <dict>
            <key>NSStringFormatSpecTypeKey</key>
            <string>NSStringPluralRuleType</string>
            <key>NSStringFormatValueTypeKey</key>
            <string>d</string>
            <key>one</key>
            <string>%d item</string>
            <key>other</key>
            <string>%d items</string>
        </dict>
    </dict>
</dict>
</plist>
```

- The `%#@items@` syntax injects the variable named `items` (the inner dict's key).
- For Russian, add `<key>few</key>` and `<key>many</key>` siblings.
- Apple's plural rule data follows CLDR.

### .xcstrings (Xcode 15+)

Single JSON catalog per project:

```json
{
  "sourceLanguage": "en",
  "strings": {
    "editor.save": {
      "comment": "Save button on the editor toolbar",
      "localizations": {
        "en": {"stringUnit": {"state": "translated", "value": "Save"}},
        "es": {"stringUnit": {"state": "translated", "value": "Guardar"}}
      }
    },
    "%d items": {
      "localizations": {
        "ru": {
          "variations": {
            "plural": {
              "one":  {"stringUnit": {"value": "%d элемент"}},
              "few":  {"stringUnit": {"value": "%d элемента"}},
              "many": {"stringUnit": {"value": "%d элементов"}},
              "other":{"stringUnit": {"value": "%d элемента"}}
            }
          }
        }
      }
    }
  }
}
```

- `state` values: `"translated"`, `"needs_review"`, `"new"`, `"stale"`. New translations: `"translated"`.
- Preserve `comment` and unknown sibling fields verbatim.

## Flutter — `.arb` (Application Resource Bundle)

```json
{
  "@@locale": "en",
  "save": "Save",
  "@save": {
    "description": "Save button on the editor toolbar"
  },
  "items": "{count, plural, one{# item} other{# items}}",
  "@items": {
    "description": "Item count in the sidebar",
    "placeholders": {
      "count": {"type": "int"}
    }
  }
}
```

Rules:

- Keys starting with `@` are **metadata** for the preceding key. Translation tools and `flutter gen-l10n` use them. Keep them.
- `@@locale` identifies the file's locale.
- Placeholders: ICU MessageFormat (`{name}`, `{n, plural, ...}`, `{x, select, ...}`).
- For each locale ARB, copy `@key` blocks from the source unchanged (description and placeholder metadata are language-neutral). Flutter's generator will complain if a target ARB references a placeholder not declared in source's `@key`.

## Rails — `config/locales/*.yml`

```yaml
en:
  activerecord:
    models:
      user: User
  hello: "Hello, %{name}"
  items:
    one: "1 item"
    other: "%{count} items"
```

Rules:

- Top-level key is the **locale code** (`en`, `es-MX`).
- Placeholders: `%{name}` (Rails-specific).
- Plurals: standard CLDR keys (`zero, one, two, few, many, other`) as sub-keys.
- Rails ships with built-in i18n data for many locales but you still author your app keys. `i18n-tasks` (gem) finds missing/unused keys.

## Django — `locale/<lang>/LC_MESSAGES/django.po`

Standard gettext .po — see gettext section. Specifics:

- Extract with `python manage.py makemessages -l es` (template `{% trans %}` and `{% blocktrans %}`, Python `gettext`/`gettext_lazy`/`ngettext`).
- Compile with `python manage.py compilemessages` (produces `.mo`).
- Locale codes are CLDR (`es`, `es-mx` — note lowercase region).

## Qt — `.ts` (source) → `.qm` (compiled)

```xml
<?xml version="1.0" encoding="utf-8"?>
<TS version="2.1" language="es_ES" sourcelanguage="en_US">
<context>
    <name>MainWindow</name>
    <message numerus="yes">
        <source>%n item(s)</source>
        <translation>
            <numerusform>%n elemento</numerusform>
            <numerusform>%n elementos</numerusform>
        </translation>
    </message>
</context>
</TS>
```

- `<context>` groups messages by class. Preserve it.
- Plurals: `<message numerus="yes">` with one `<numerusform>` per locale plural category (Qt matches CLDR for known locales).
- Extract via `lupdate`, compile via `lrelease`.

## .NET — `.resx`

```xml
<root>
  <data name="save" xml:space="preserve">
    <value>Save</value>
    <comment>Save button</comment>
  </data>
</root>
```

- Satellite assemblies: `Strings.resx` (neutral), `Strings.es.resx` (Spanish), `Strings.es-MX.resx`.
- `xml:space="preserve"` keeps leading/trailing whitespace.
- Placeholders: `String.Format` style — `{0}`, `{1}`. Match positions in translation.

## Java — `.properties`

```
save=Save
items.one=1 item
items.other={0} items
greeting=Hello, {0}
```

- Plain key=value. Backslash line continuation. Comments with `#` or `!`.
- **Encoding**: ISO-8859-1 historically; Java 9+ reads UTF-8. For older Java, non-Latin-1 chars must be `\uXXXX`-escaped — `native2ascii` (or modern toolchain equivalents) does this.
- Placeholders: `MessageFormat` style — `{0}`, `{1}`. ICU MessageFormat via `MessageFormat.format()`.
- File naming: `messages.properties` (default), `messages_es.properties`, `messages_es_MX.properties`.

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
