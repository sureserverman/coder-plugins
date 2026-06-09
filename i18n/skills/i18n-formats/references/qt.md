# Qt — `.ts` (source) → `.qm` (compiled)

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
