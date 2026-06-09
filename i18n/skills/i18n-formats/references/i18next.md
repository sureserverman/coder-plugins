# JSON — i18next / react-i18next

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
