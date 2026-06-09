# JSON / YAML — Vue i18n

```json
{ "hello": "Hi, {name}", "items": "no items | {count} item | {count} items" }
```

Rules:

- **Placeholders**: `{name}` (single brace) by default. List-style: `{0}`, `{1}`.
- **Plurals** (built-in, not CLDR-strict): pipe-separated forms `zero | one | many`. Vue i18n's built-in pluralization is simplistic — for Russian and Arabic, switch to ICU via the `@intlify/vue-i18n` plugin and use full ICU MessageFormat.
- **Linked messages**: `@:foo.bar` references another key — preserve the link, don't expand.
- **Modifiers**: `@.lower:foo` lowercases the linked message — preserve.
