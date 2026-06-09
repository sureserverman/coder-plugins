# Java — `.properties`

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
