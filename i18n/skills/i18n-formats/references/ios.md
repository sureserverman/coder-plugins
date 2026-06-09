# iOS — `.strings`, `.stringsdict`, `.xcstrings`

## .strings (legacy, still common)

```
/* Save button on the editor toolbar */
"editor.save" = "Save";
"editor.discard" = "Don't save";
```

- Key-value pairs, semicolon-terminated.
- `/* */` comments only.
- `\"`, `\n`, `\t`, `\\`. UTF-16 typical (UTF-8 increasingly accepted).
- Format placeholders: `%@` (Objective-C object), `%d`, `%lld`, `%f`, `%1$@`, `%2$d`. Use `String(format:NSLocalizedString(…), …)`.

## .stringsdict (XML plist for plurals)

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

## .xcstrings (Xcode 15+)

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
