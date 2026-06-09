# JSON — react-intl / FormatJS

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
