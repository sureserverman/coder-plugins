# .NET — `.resx`

```xml
<root>
  <data name="save" xml:space="preserve">
    <value>Save</value>
    <comment>Save button</comment>
  </data>
</root>
```

- Satellite assemblies: `Strings.resx` (neutral), `Strings.es.resx` (Spanish), `Strings.es-MX.resx`.
- `xml:space="preserve"` keeps leading/trailing whitespace.
- Placeholders: `String.Format` style — `{0}`, `{1}`. Match positions in translation.
