# Browser Extensions — Reference (Code Patterns & Store Notes)

Use this when you need concrete code patterns or store policy details. The main skill is in SKILL.md.

---

## 1. Localized API errors (error envelope)

**Problem:** API layer throws `new Error("Cannot reach server...")` so the UI cannot show the message in the user’s language.

**Pattern:** In the API module (e.g. `lib/matrix-api.js`), define a helper and use it for every user-facing error:

```javascript
function apiError(key, subs, fallback) {
  const err = new Error(fallback);
  err.errorKey = key;
  err.errorSubs = subs || [];
  return err;
}

// Usage when throwing:
throw apiError("errCannotReachDomain", [domain], `Cannot reach ${domain}. Check the domain and your network connection.`);
```

In the UI (options, popup, manage), when catching:

```javascript
catch (e) {
  const msg = e && e.errorKey ? t(e.errorKey, e.errorSubs || []) : (e && e.message) || String(e);
  showStatus(msg, "error");
}
```

Add a message key in every locale, e.g. in `_locales/en/messages.json`:

```json
"errCannotReachDomain": {
  "message": "Cannot reach $domain$. Check the domain and your network connection.",
  "description": "Discovery network error.",
  "placeholders": { "domain": { "content": "$1" } }
}
```

Use **named** placeholders in the message (`$domain$`) and map them in `placeholders` with `"content": "$1"` (or `$2`, etc.) for the substitution index.

---

## 2. i18n helper (Chrome vs Firefox)

**Chrome** (`lib/i18n.js`):

```javascript
const I18n = {
  getMessage(key, substitutions = []) {
    return chrome.i18n.getMessage(key, substitutions) || key;
  },
  applyDocument() {
    document.querySelectorAll("[data-i18n]").forEach(el => {
      const key = el.getAttribute("data-i18n");
      const msg = this.getMessage(key);
      if (el.hasAttribute("data-i18n-placeholder")) {
        el.placeholder = msg;
      } else {
        el.textContent = msg;
      }
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (key && !el.hasAttribute("data-i18n")) el.placeholder = this.getMessage(key);
    });
  }
};
```

**Firefox:** Same structure but use `browser.i18n.getMessage` instead of `chrome.i18n.getMessage`.

In each page script: load `i18n.js`, then call `I18n.applyDocument()` after DOM is ready. Use a local `t(key, subs)` that calls `I18n.getMessage(key, subs)` for every dynamic string (buttons, status, validation, errors).

---

## 3. Placeholder format in messages.json

Chrome and AMO require **named** placeholders in the message string. The name must match a key in the `placeholders` object; `content` specifies which substitution (e.g. `$1`, `$2`) is used.

| Example key   | Message string           | placeholders                    |
|---------------|---------------------------|---------------------------------|
| usersLoaded   | `"$count$ users loaded."` | `"count": { "content": "$1" }`  |
| removeConfirm | `"Remove $user$?"`        | `"user": { "content": "$1" }`   |
| manageTitle   | `"Manage — $domain$"`     | `"domain": { "content": "$1" }` |

In code: `getMessage("usersLoaded", [42])` → “42 users loaded.” Do **not** use `$1$`, `$2$` in the message; both stores will report it as undefined.

---

## 4. Chrome: request host permission before fetch

If the manifest has `optional_host_permissions: ["<all_urls>"]`, you must request access to each origin before the first request. Example (options page, when saving a server):

```javascript
const domain = inputUrl.value.trim().replace(/^https?:\/\//, "").replace(/\/+$/, "");
const origins = [`https://${domain}/*`];
const granted = await chrome.permissions.request({ origins });
if (!granted) {
  showMessage(t("permissionDeniedHost", [domain]), true);
  return;
}
const serverUrl = await MatrixApi.discoverServer(domain);
// If server URL has a different host (e.g. matrix.example.com), request that too:
const serverHost = new URL(serverUrl).host;
if (serverHost !== domain) {
  const granted2 = await chrome.permissions.request({ origins: [`https://${serverHost}/*`] });
  if (!granted2) {
    showMessage(t("permissionDeniedHost", [serverHost]), true);
    return;
  }
}
// Now call MatrixApi.login(serverUrl, ...), etc.
```

Add message keys for permission denial (e.g. `permissionDenied`, `permissionDeniedHost`) and use them in all locales.

---

## 5. In-tab navigation (e.g. Firefox Android)

Instead of opening options or manage in a new tab, navigate the current tab:

```javascript
const Nav = {
  openApp() {
    window.location.href = browser.runtime.getURL("app/app.html");
  },
  openSettings() {
    window.location.href = browser.runtime.getURL("options/options.html");
  },
  openManage(serverId) {
    window.location.href = browser.runtime.getURL("manage/manage.html?server=" + encodeURIComponent(serverId));
  }
};
```

On options and manage pages, add a “Back” link and set its `href` in JS:

```javascript
document.getElementById("link-back").href = browser.runtime.getURL("app/app.html");
```

Use `data-i18n="back"` and add a `back` message key in all locales.

---

## 6. Reloading an extension tab after an action

If the extension has a “Manage” tab and the user creates an account from the popup/app, reload the manage tab so the list updates. Requires `tabs` permission.

```javascript
async function reloadManageTabIfOpen(serverId) {
  const manageUrl = browser.runtime.getURL("manage/manage.html?server=" + encodeURIComponent(serverId));
  const tabs = await browser.tabs.query({ url: manageUrl });
  for (const tab of tabs) {
    if (tab.id) await browser.tabs.reload(tab.id);
  }
}
// Call after successful createUser in popup/app.
```

Chrome: use `chrome.tabs.query` and `chrome.tabs.reload`.

---

## 7. Packaging commands

From the **repository root**, with extension directories `chrome/`, `mozilla/`, `moz-mobile/`:

**Chrome (zip):**
```bash
cd chrome && zip -r ../matrix-user-manager-chrome.zip . -x "*.git*" && cd ..
```

**Firefox desktop (xpi):**
```bash
cd mozilla && zip -r ../matrix-user-manager-mozilla.xpi . -x "*.git*" && cd ..
```

**Firefox Android (xpi):**
```bash
cd moz-mobile && zip -r ../matrix-user-manager-mobile.xpi . -x "*.git*" && cd ..
```

Ensure `manifest.json` is at the root of each archive (no `chrome/` or `mozilla/` folder inside the zip).

---

## 8. Chrome Web Store — privacy policy

If the extension handles user data (e.g. login, tokens, form data):

- Publish a privacy policy that states what is collected, how it is used, and with whom it is shared.
- Link the policy URL in the Chrome Web Store Developer Dashboard (Privacy practices / single privacy policy URL).
- Ensure dashboard “Privacy practices” and the policy match the extension’s actual behavior; mismatches can result in removal.

---

## 9. AMO — placeholder warning

If AMO shows “A placeholder used in the message is not defined” for a locale file, the message string almost certainly uses a numeric placeholder like `$1$`. Replace it with a named placeholder (e.g. `$count$`, `$user$`, `$domain$`) and ensure that name exists in the `placeholders` object for that message.

---

## 10. Cross-browser quick reference

| Topic | Chrome | Firefox (desktop) | Firefox Android |
|-------|--------|-------------------|-----------------|
| Manifest | MV3 preferred | MV2 | MV2 |
| i18n API | `chrome.i18n.getMessage` | `browser.i18n.getMessage` | same |
| Storage | `chrome.storage.local` | `browser.storage.local` | same |
| Host access | `optional_host_permissions` + `chrome.permissions.request()` before fetch | `permissions: ["<all_urls>"]` | same |
| Tabs | `chrome.tabs.query` / `reload` (needs `tabs`) | `browser.tabs.*` | same; prefer in-tab nav |
| Package | .zip, manifest at root | .xpi (zip), manifest at root | .xpi, manifest at root |
