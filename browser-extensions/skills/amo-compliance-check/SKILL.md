---
name: amo-compliance-check
description: Use when checking a Firefox extension for addons.mozilla.org (AMO) submission compliance, before packaging or publishing a Firefox WebExtension. Trigger on "AMO rejected my addon", "prep this addon for mozilla", "check firefox extension for AMO", "is this extension signable", "will AMO accept this manifest".
---

# AMO Compliance Check

Systematic review of a Firefox extension against addons.mozilla.org submission requirements.

## Instructions

When invoked, identify the extension root directory (the directory containing `manifest.json` for the Firefox/Mozilla version). If unclear, ask the user.

**Preferred — run the bundled script first:**

```bash
skills/amo-compliance-check/scripts/amo-check.py <extension-dir>
```

It runs sections 1–8 and 10 automatically: manifest parse + required/conditional field validation (regex for version and gecko.id), icon-file existence + SVG attribute check, hidden/binary/case-duplicate scan, referenced-file existence, permission validation against the AMO-allowed set, remote-script and `eval`/`new Function`/string-timer detection, CSP `unsafe-eval` check, cryptominer references, and HTTP (non-HTTPS) URL scan. Output is per-finding lines plus the summary table. Exit 1 if any FAIL was found.

**After the script, still read the sections below** — they are the source of truth for what's checked and cover the pieces that need human judgment: section 5 (is `<all_urls>` actually necessary?), section 7 (obfuscation/minification patterns), section 9 (content-script DOM-injection safety), and MV3 `data_collection_permissions` values. Use the numbered sections as both the script's spec and your manual-pass checklist.

<details>
<summary>Manual pass (fallback — only if the script isn't available)</summary>

Run every check below in order. For each section, report PASS, WARN, or FAIL with a brief explanation. At the end, provide a summary table.

</details>

## 1. Manifest — Required Fields

Read `manifest.json` and verify:

- [ ] `manifest_version` exists and is `2` or `3`
- [ ] `name` exists, is non-empty, no leading/trailing whitespace, max 50 characters
- [ ] `version` exists and matches `^(0|[1-9][0-9]{0,8})([.](0|[1-9][0-9]{0,8})){0,3}$`

## 2. Manifest — Conditional & Recommended Fields

- [ ] If `_locales/` directory exists, `default_locale` must be set. If no `_locales/`, `default_locale` must be absent
- [ ] For MV3: `browser_specific_settings.gecko.id` is present (required for AMO). For MV2: recommended
- [ ] Extension ID format is valid: email-like (`^[a-zA-Z0-9-._]*@[a-zA-Z0-9-._]+$`, max 80 chars) or GUID (`^\{[0-9a-fA-F]{8}-...}$`)
- [ ] `description` is present and max 132 characters
- [ ] `homepage_url` does NOT link to addons.mozilla.org
- [ ] `update_url` is NOT present (forbidden for AMO-hosted extensions)
- [ ] `applications` key is not used (deprecated; use `browser_specific_settings`). Invalid in MV3
- [ ] If `strict_min_version` is set, it does not use `*` wildcard
- [ ] No block comments (`/* */`) in JSON. No duplicate keys

## 3. Icons

- [ ] All icon files referenced in manifest exist on disk
- [ ] Icon files are PNG or SVG (valid extensions)
- [ ] At minimum 48px and 96px icons are provided (recommended for AMO listing)
- [ ] SVG icons (if any) include `viewBox` and `xmlns` attributes

## 4. File Structure

- [ ] No hidden files (dotfiles) in the extension directory
- [ ] No flagged binary extensions (`.exe`, `.dll`, `.so`, `.dylib`, `.bin`)
- [ ] No duplicate filenames that differ only by case
- [ ] All files referenced in `content_scripts` exist and have non-empty filenames
- [ ] All files referenced in `background.scripts` or `background.page` exist
- [ ] All files referenced in `web_accessible_resources` exist

## 5. Permissions

- [ ] Only valid WebExtension permissions are requested
- [ ] No privileged/Mozilla-internal permissions (`mozillaAddons`, etc.)
- [ ] `<all_urls>` or broad host permissions — flag as WARN (requires justification)
- [ ] Permissions appear necessary for the extension's stated functionality (flag unnecessary ones)

## 6. Security — No Remote Code

- [ ] No `<script src="http...">` or `<script src="//...">` tags in HTML files (remote script loading)
- [ ] No `fetch()`/`XMLHttpRequest` calls that load JS for execution (eval of fetched code)
- [ ] No `eval()`, `new Function()`, `setTimeout(string)`, `setInterval(string)` in JS files
- [ ] No `document.write()` usage
- [ ] If `content_security_policy` is customized, it does NOT contain `unsafe-eval`

## 7. Security — Code Quality

- [ ] No obfuscated code (check for common obfuscation patterns: long hex strings, `\x` escape sequences in bulk, base64-encoded blocks executed via eval)
- [ ] No minified code without source submission (WARN if code appears minified)
- [ ] No cryptocurrency mining patterns (`CoinHive`, `coinhive`, `crypto-loot`, miner references)

## 8. Data & Privacy

- [ ] If extension transmits any user data remotely, a privacy policy URL should be noted as required for AMO listing
- [ ] All remote requests use HTTPS, not HTTP
- [ ] No data storage patterns in private browsing context (check for `incognito` handling)

## 9. Content Scripts & Web Page Security

- [ ] Content scripts do not relax or modify page CSP
- [ ] Content scripts properly sanitize any DOM injection (no raw `innerHTML` with unsanitized external data)

## 10. Manifest V3 Specific (if applicable)

- [ ] `background.service_worker` has a `background.scripts` fallback for Firefox compatibility
- [ ] `incognito` is not set to `"split"` (unsupported in Firefox)
- [ ] `browser_specific_settings.gecko.data_collection_permissions` is present with valid values

## Summary Format

After all checks, output a table:

```
| Section                    | Status | Issues |
|----------------------------|--------|--------|
| Manifest Required Fields   | PASS   |        |
| Manifest Conditional       | WARN   | ...    |
| Icons                      | PASS   |        |
| File Structure             | PASS   |        |
| Permissions                | WARN   | ...    |
| Security — Remote Code     | PASS   |        |
| Security — Code Quality    | PASS   |        |
| Data & Privacy             | PASS   |        |
| Content Scripts            | PASS   |        |
| MV3 Specific               | N/A    |        |
```

Then list actionable items sorted by severity (FAIL first, then WARN).

## Delegation (Claude Code only)

> **Skip this section unless you are Claude Code.** The Agent tool with
> `subagent_type:` parameters is a Claude Code feature. Codex, Cursor, Gemini,
> OpenCode, and other hosts do not have it — run the full workflow yourself
> instead.

The manifest read, the permission enumeration, the `web-ext lint` run, and the
file/structure checks are all read-only bulk I/O. If you are running on Opus and
the extension is non-trivial, delegate the scan phase to the `readonly-scanner`
subagent (model: haiku) via the Agent tool with `subagent_type: readonly-scanner`.
Give it the extension root path and ask it to return:

- `manifest.json` parsed, with all fields relevant to AMO policy.
- The permission list, any host permissions, and which scripts declare them.
- `web-ext lint --output=json` raw output if `web-ext` is on PATH.
- File tree summary (size, count, flagged binary/minified files).

Integrate those findings into the compliance verdict yourself — the verdict
itself stays with the caller.
