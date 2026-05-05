---
name: browser-extensions
description: Use when creating, improving, or packaging browser extensions (WebExtensions) for Chrome, Firefox, or Firefox for Android. Trigger on "my extension won't load", "manifest v3 migration", "chrome store rejected me", "AMO submission", "add a content script", "request a new permission", or any WebExtension work for Chrome/Firefox/Firefox-for-Android.
---

# Browser Extensions — Creation and Improvement

Apply this skill when building or modifying WebExtensions (Chrome MV2/MV3, Firefox desktop, Firefox for Android). It encodes pitfalls to avoid and practices that speed development and pass store checks.

## When to Use

- Adding or changing extension UI, options, popup, or background logic
- Adding localization (i18n) or fixing locale/manifest errors
- Packaging for Chrome Web Store or addons.mozilla.org (AMO)
- Handling permissions (host, storage, tabs) or cross-origin requests
- Implementing error handling or multi-platform builds (chrome / mozilla / mobile)

---

## 0. Scope: single-browser vs multi-browser

**Before recommending Chrome-specific or multi-platform work, check whether the extension targets a single browser.**

- **Check:** README, manifest (`browser_specific_settings`, target docs), and any project docs for stated scope (e.g. “Tor Browser only”, “Firefox only”, “Chrome + Firefox”).
- **If the extension is single-browser or single-platform** (e.g. Tor Browser only, Firefox only): do **not** recommend Chrome Web Store packaging, Chrome MV3 manifest, `optional_host_permissions`, Chrome-specific APIs, or multi-platform build layout unless the user or project explicitly asks for other-browser support.
- **If the extension is multi-browser or scope is unclear:** apply the full skill, including Chrome and multi-platform guidance where relevant.

This keeps advice relevant to the project and avoids unnecessary Chrome/multi-browser work for browser-specific extensions.

---

## 1. Pitfalls to Avoid

### Manifest and locales

- **Do not set `default_locale` until `_locales` exists.** If the manifest has `"default_locale": "en"` but no `_locales/` tree, Chrome and Firefox will fail to load with “Default locale was specified, but _locales subtree is missing.”
- **Add `_locales` and at least one locale (e.g. `_locales/en/messages.json`) before or in the same change as adding `default_locale` and `__MSG_*` in the manifest.**

### i18n message placeholders

- **Never use numeric placeholders like `$1$` in the message string.** Chrome and AMO expect **named** placeholders. The placeholder name in the message must match a key in the `placeholders` object.
  - Wrong: `"message": "Loaded $1$ users"` with `"placeholders": { "count": { "content": "$1" } }` → Chrome: “Variable $1$ used but not defined”; AMO: “placeholder used in the message is not defined.”
  - Right: `"message": "Loaded $count$ users"` with `"placeholders": { "count": { "content": "$1" } }`. In code, pass substitutions as before: `getMessage("usersLoaded", [count])`.
- Use consistent names (e.g. `$count$`, `$user$`, `$domain$`) and keep `placeholders.*.content` as `"$1"`, `"$2"` for the substitution indices.

### Chrome Manifest V3 and host permissions

- **Optional host permissions are not granted by default.** If the manifest has `optional_host_permissions` (e.g. `["<all_urls>"]`) and the extension calls `fetch()` to a user-chosen domain without requesting permission first, the request is blocked and users see generic “Cannot reach” / network errors.
- **Request host permission at runtime before the first request to that origin:** e.g. `chrome.permissions.request({ origins: [`https://${domain}/*`] })` before calling your API. If the user denies, show a clear, localized message and do not call the API.
- Add required permission **`tabs`** if the extension needs to find or reload its own pages (e.g. “reload manage tab when a user is created”).

### Packaging

- **Archive root must be the extension root.** Both Chrome and Firefox expect `manifest.json` at the root of the zip, not inside a subfolder.
  - Wrong: zipping from repo root so the archive contains `chrome/manifest.json` or `moz-mobile/manifest.json` inside a folder.
  - Right: `cd <extension-dir> && zip -r ../out.zip .` so the archive root has `manifest.json`, `_locales/`, etc.
- Chrome: ship a **.zip** (upload to Chrome Web Store). Firefox/AMO: ship a **.xpi** (same zip format, rename or use .xpi extension).

### Mobile and navigation

- On Firefox for Android, opening many tabs is awkward. Prefer **in-tab navigation** between extension pages (e.g. app → options → manage) instead of `browser.tabs.create()`. Use `window.location.href = browser.runtime.getURL("options/options.html")` and provide a “Back” link to the app on options and manage pages.
- Ensure “Back” and other nav links use `runtime.getURL()` so they work from any extension page.

### Localizing errors and messages

- **Do not hardcode user-facing error strings in the API layer.** If the API throws `new Error("Cannot reach server...")`, the UI cannot show that in the user’s language.
- Use a small **error envelope**: throw an `Error` that carries a message key and substitutions (e.g. `errorKey`, `errorSubs`). In the UI, if `e.errorKey` is set, call `t(e.errorKey, e.errorSubs || [])`; otherwise fall back to `e.message` or `String(e)`.
- Add a message key for every such error in all locale files (at least in the default locale).

### Privacy and stores

- **Chrome Web Store:** If the extension handles user data (e.g. credentials, tokens, form data), you must provide a **privacy policy** and link it in the Developer Dashboard. The policy must state what is collected, how it is used, and with whom it is shared. Align dashboard “Privacy practices” with the policy and actual behavior.
- **AMO:** Align with [AMO compliance](https://developer.chrome.com/docs/webstore/program-policies/) and use the AMO compliance skill before packaging if needed.

---

## 2. Best Practices

### Manifest

- Use `__MSG_extensionName__` and `__MSG_extensionDescription__` with `default_locale` once `_locales` is in place.
- Chrome MV3: `permissions`: `["storage","tabs"]`; host access via `optional_host_permissions` and runtime `chrome.permissions.request()`.
- Firefox: `permissions`: `["storage","<all_urls>","tabs"]` as needed; `browser_specific_settings.gecko.id` for AMO.

### i18n

- **Shared helper:** One small `lib/i18n.js` (or equivalent) that wraps `chrome.i18n.getMessage` / `browser.i18n.getMessage` and exposes `getMessage(key, substitutions)` and `applyDocument()`.
- **applyDocument():** Query `[data-i18n]` and set `textContent` (or `placeholder` when used with `data-i18n-placeholder`). Also handle elements that have only `data-i18n-placeholder` (set `placeholder` only).
- In HTML, use `data-i18n="messageKey"` for text and `data-i18n-placeholder="placeholderKey"` for input placeholders. In JS, use a short `t(key, subs)` that calls the helper for every dynamic string (buttons, status, errors).
- Add the same keys to every locale file; use English as fallback for missing translations so the UI never shows raw keys.

### API errors and UI

- In the API module, define a small helper that returns an `Error` with `errorKey` and `errorSubs`. Use it for all user-facing errors (network, auth, validation).
- In options, popup, and manage (or any UI that catches errors), display: `e && e.errorKey ? t(e.errorKey, e.errorSubs || []) : (e && e.message) || String(e)`.

### Multi-platform builds

- **Only when the extension targets more than one browser:** Keep shared logic in a single place (e.g. `lib/` with `storage.js`, `matrix-api.js`, `i18n.js`) and only diverge for manifest, API names (`chrome` vs `browser`), and entry points (e.g. popup vs full-page app).
- When adding a feature or bugfix to a multi-platform project, apply it to all targets (chrome, mozilla, moz-mobile) and run a quick sanity check for each.

### Reloading extension pages after actions

- If the extension can open an internal page (e.g. “Manage”) in a tab, and another part (e.g. popup or app) creates a user, query tabs by the manage URL and call `tabs.reload(tab.id)` so the list stays in sync. Requires the `tabs` permission.

---

## 3. Checklists

### When assessing an extension (single vs multi-browser)

- [ ] Check README, manifest, and docs for target browser(s). If single-browser (e.g. Tor Browser / Firefox only), scope recommendations to that platform; do not suggest Chrome or multi-platform work unless requested.

### Before first run or “Load unpacked”

- [ ] If manifest has `default_locale`, `_locales/<locale>/messages.json` exists for that locale.
- [ ] Manifest does not reference missing files (icons, options_ui, background scripts).

### Before adding or changing localized strings

- [ ] New keys exist in **all** locale files (at least default locale); use named placeholders in the message string where needed.
- [ ] Placeholder names in the message (e.g. `$user$`) match keys in `placeholders` and `content` uses `$1`, `$2` for substitution order.

### Before packaging for Chrome

- [ ] Host permission is requested at runtime before first `fetch()` to each domain (if using optional host permissions).
- [ ] Privacy policy exists and is linked in the Chrome Web Store Developer Dashboard; dashboard disclosures match the policy and extension behavior.
- [ ] Package is built from inside the extension directory so `manifest.json` is at the zip root.

### Before packaging for Firefox / AMO

- [ ] Same packaging rule: zip from inside the extension directory, `manifest.json` at root.
- [ ] No `$1$`-style placeholders in `_locales/*/messages.json`; use named placeholders.
- [ ] Run AMO compliance check if applicable (see amo-compliance-check skill).

### When adding a new extension “page” (e.g. manage, options)

- [ ] All user-visible strings go through message keys; no hardcoded English in HTML/JS.
- [ ] Errors from the API are shown via `errorKey`/`errorSubs` and localized keys.
- [ ] On mobile build, consider in-tab navigation and a “Back” link to the main app with `runtime.getURL()`.

---

## 4. Reference

For code patterns (apiError helper, i18n helper, placeholder format) and the cross-browser quick reference table, see [reference.md](reference.md).
