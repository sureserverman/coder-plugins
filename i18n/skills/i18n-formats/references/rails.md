# Rails — `config/locales/*.yml`

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
