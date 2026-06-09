# Flutter — `.arb` (Application Resource Bundle)

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
