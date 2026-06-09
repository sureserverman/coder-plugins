# Android — `res/values*/strings.xml`

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
