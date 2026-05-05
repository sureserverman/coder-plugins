# browser-extensions

Authoring and shipping browser extensions (WebExtensions) for Chrome, Firefox, and Firefox for Android.

## Installation

Add the marketplace:
```bash
/plugin marketplace add sureserverman/coder-plugins
```

Install the plugin:
```bash
/plugin install browser-extensions@coder-plugins
```

## Skills

### `browser-extensions`

End-to-end authoring help for WebExtensions: manifest v3 migration, content scripts, background service workers, permissions, host permissions, message passing, MV2 → MV3 changes, the Firefox-for-Android caveats, store rejection patterns from both Chrome Web Store and addons.mozilla.org.

**Triggers:** "my extension won't load", "manifest v3 migration", "chrome store rejected me", "AMO submission", "add a content script", "request a new permission", "background service worker", "Firefox for Android extension".

### `amo-compliance-check`

Preflight audit for addons.mozilla.org submission. Checks `manifest.json` against AMO's hard rules: addon ID, permissions justification, no minified third-party sources without source upload, no obfuscated code, no remote-hosted code in MV3, valid update URL behavior. Ships a `scripts/amo-check.py` linter you can run before zipping the extension.

**Triggers:** "AMO rejected my addon", "prep this addon for mozilla", "check firefox extension for AMO", "is this extension signable", "will AMO accept this manifest", "amo compliance".

## Linter

The `amo-compliance-check` skill includes a Python linter:

```bash
python skills/amo-compliance-check/scripts/amo-check.py path/to/extension/
```

It exits non-zero on hard violations and prints a remediation checklist.

## License

MIT
