---
name: browser-extensions
description: Use when creating, improving, or packaging browser extensions (WebExtensions) for Chrome, Firefox, or Firefox for Android. Trigger on "my extension won't load", "manifest v3 migration", "chrome store rejected me", "AMO submission".
---

# Browser Extensions — Creation and Improvement

## Scope: single-browser vs multi-browser

**Before recommending Chrome-specific or multi-platform work, check whether the extension targets a single browser.**

- **Check:** README, manifest (`browser_specific_settings`, target docs), and any project docs for stated scope (e.g. “Tor Browser only”, “Firefox only”, “Chrome + Firefox”).
- **If the extension is single-browser or single-platform** (e.g. Tor Browser only, Firefox only): do **not** recommend Chrome Web Store packaging, Chrome MV3 manifest, `optional_host_permissions`, Chrome-specific APIs, or multi-platform build layout unless the user or project explicitly asks for other-browser support.
- **If the extension is multi-browser or scope is unclear:** apply the full skill. A fix to a multi-platform project goes to every target (chrome, mozilla, moz-mobile).

## Pitfalls

1. **Do not set `default_locale` until `_locales` exists.** With `"default_locale": "en"` and no `_locales/` tree, Chrome and Firefox refuse to load: “Default locale was specified, but _locales subtree is missing.” Add `_locales/<locale>/messages.json` in the same change as `default_locale` and `__MSG_*`.
2. **Named i18n placeholders only — never `$1$` in the message string.** The name in the message must match a key in `placeholders`.
   - Wrong: `"message": "Loaded $1$ users"` → Chrome: “Variable $1$ used but not defined”; AMO: “placeholder used in the message is not defined.”
   - Right: `"message": "Loaded $count$ users"` with `"placeholders": { "count": { "content": "$1" } }`; code still calls `getMessage("usersLoaded", [count])`.
3. **Chrome MV3 optional host permissions are not granted by default.** A `fetch()` to a user-chosen domain under `optional_host_permissions` is blocked and surfaces as a generic “Cannot reach” error. Call `chrome.permissions.request({ origins: [`https://${domain}/*`] })` before the first request; on denial, show a localized message and skip the call.
4. **Archive root must be the extension root.** Zip from inside the extension directory (`cd <extension-dir> && zip -r ../out.zip .`) so `manifest.json` sits at the archive root, not under `chrome/` or `moz-mobile/`. Chrome takes the `.zip`; AMO takes the same file as `.xpi`.
5. **Firefox for Android: navigate in-tab.** Many tabs are awkward on mobile. Move between extension pages with `window.location.href = browser.runtime.getURL("options/options.html")` instead of `tabs.create()`, and give each page a “Back” link built with `runtime.getURL()`.

## Stores

- **AMO:** Follow Mozilla's add-on policies (checked 2026-11-10, https://extensionworkshop.com/documentation/publish/add-on-policies/); run the `amo-compliance-check` skill before packaging.

Code patterns (error envelope, i18n helper, packaging commands) and a cross-browser table are in [reference.md](reference.md).
