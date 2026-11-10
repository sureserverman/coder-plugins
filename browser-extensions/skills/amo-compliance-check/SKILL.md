---
name: amo-compliance-check
description: Use when checking a Firefox extension for addons.mozilla.org (AMO) submission compliance, before packaging or publishing. Trigger on "AMO rejected my addon", "prep this addon for mozilla", "check firefox extension for AMO", "is this extension signable".
---

# AMO Compliance Check

Find the extension root (the directory holding the Firefox `manifest.json`); ask if unclear. Run the bundled script first:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/amo-compliance-check/scripts/amo-check.py <extension-dir>
```

It covers the mechanical checks: manifest fields and formats, icons, file structure, referenced files, permission validity, remote code and `eval`-family calls, CSP `unsafe-eval`, miner references, HTTP URLs and the MV3 background and `incognito` rules. It does not check that MV3 `browser_specific_settings.gecko.data_collection_permissions` is present with valid values; check that by hand. Exit 1 means at least one FAIL. For structured findings on the plugin-dev JSON contract, run `bash ${CLAUDE_PLUGIN_ROOT}/scripts/validate.sh <extension-dir> --json`.

A clean run means no mechanical violations, not that AMO will accept it. Then judge the three areas the script cannot decide, reporting PASS, WARN or FAIL for each:

## 1. Permissions necessity

- [ ] Each requested permission is needed for the extension's stated function; flag the unnecessary ones.
- [ ] `<all_urls>` or broad host permissions are WARN unless the functionality clearly requires them; draft the justification for the submission notes.

## 2. Code quality and obfuscation

- [ ] No obfuscated code (long hex strings, bulk `\x` escapes, base64 blocks fed to eval).
- [ ] Minified or bundled code is WARN: AMO requires the source upload for it.

## 3. Content scripts

- [ ] Content scripts do not relax or modify the page CSP.
- [ ] DOM injection is sanitized: no raw `innerHTML` with unsanitized external data.

Finish with one table merging the script's findings and these three verdicts, then list the actionable items, FAIL first, then WARN.
