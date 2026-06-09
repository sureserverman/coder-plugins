# GNU gettext (.po / .pot)

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
