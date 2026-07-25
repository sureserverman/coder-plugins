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

Both skills fire on the phrases above and are invocable as `/browser-extensions:<skill>`.

## Linter

The `amo-compliance-check` skill includes a Python linter you can run yourself, in CI or before zipping:

```bash
python3 skills/amo-compliance-check/scripts/amo-check.py path/to/extension/
```

**Exit codes:** `0` — no hard violations; `1` — at least one FAIL finding; `2` — the extension directory or `manifest.json` couldn't be read or parsed. Findings print as a remediation checklist.

**What it checks:** required and conditional manifest fields, icons, referenced files actually existing, permissions (including justification-worthy ones), remote-hosted code, MV3-specific rules, plus quality and privacy heuristics.

**What it does not — read this before trusting a green run.** It is a *static preflight against the rules that can be checked statically*, not a simulation of AMO review. It cannot detect obfuscation that looks like ordinary minification, judge whether your permission justifications are *persuasive*, review bundled third-party code you must also upload sources for, or predict a human reviewer's call on borderline data-collection behavior. **A clean run means "no mechanical violations found", not "AMO will accept this."** A preflight trusted beyond its coverage is worse than none, because it converts a maybe into a false confidence.

## Artifacts

Nothing persisted. The linter prints findings; the authoring skill edits your extension's own source and manifest, showing the diff first. No store submission is ever performed for you.

## Worked example

```text
/plugin install browser-extensions@coder-plugins

"prep this addon for mozilla"
```

`amo-compliance-check` runs the linter, reports (say) a missing `browser_specific_settings.gecko.id` and a `<all_urls>` host permission with no stated justification, and explains what AMO wants for each. You fix them; a re-run exits 0 — which means the mechanical checks pass, and the judgment-dependent parts are still yours to defend in the submission notes.

## Related plugins

- **`ui-design`** — extension popup and options UI is web UI; pair with `ui-web` for a WCAG pass.
- **`planning`** — `project-maturity` records the durable Packaging and Security readiness verdicts for an extension you intend to publish.
- **`release-promo`** — drafts the announcement once the extension is listed.

## License

MIT
