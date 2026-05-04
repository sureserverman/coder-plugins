# Data safety decision table

Map your app's actual behaviour to honest answers in Play Console's Data safety form. **Lying here is a policy violation that gets apps suspended** — Google's automated scanners check the manifest, SDK list, and runtime traffic against your declarations.

## Top-level question

**"Does your app collect or share any user data?"**

| App pattern | Answer |
|---|---|
| Local-only utility (calculator, image viewer, keyboard) | **No** |
| Sends data only to a backend the **user configures** (self-hosted server admin, Matrix client, Mastodon client, custom WebDAV) | **No** — user-supplied destinations are not "collection" |
| Talks to a backend **you operate** | **Yes** |
| Crash logs to Firebase Crashlytics or any third party | **Yes** — crash logs count |
| Analytics SDK present (Firebase Analytics, Mixpanel, etc.) | **Yes** |
| Ads SDK present | **Yes** |
| In-app purchases via Play Billing | **Yes** for purchase history |

If your final answer is **No**, you skip the rest of the form. Most of the table below applies when the answer is **Yes**.

## Per-data-type questions

For every data type you declared, Play asks:

1. **Collected** — sent off-device by your app or any embedded SDK.
2. **Shared** — sent to a third party other than the service provider (i.e. given to anyone other than your backend).
3. **Optional or required** — can the user opt out and still use the app?
4. **Why** — Account management / Analytics / App functionality / Developer communications / Advertising / Personalization / Fraud prevention / Compliance.
5. **Processed ephemerally** or **stored** — does it persist on your servers?

## Common data types and what counts as collection

| Data type | Counts as collection if… | Does NOT count if… |
|---|---|---|
| **Email address** | App sends user's email anywhere (signup, support, telemetry) | App only displays a `mailto:` link the user taps |
| **Name** | Stored in your backend account | Only ever shown locally |
| **User ID** | Backend assigns and stores an ID for the user | Random ID generated on device, never sent |
| **Phone number** | App reads `TelephonyManager.line1Number` and transmits | App reads it only to autofill a form the user submits manually |
| **Address** | Backend stores it | User pastes into a `mailto:` body |
| **Race/ethnicity, religion, sexual orientation, political opinions, etc.** | Any collection at all is "Personal info – sensitive" | n/a |
| **Photos / Videos** | Uploaded to your backend, even temporarily | Read locally and passed to another app via Intent |
| **Audio recordings** | Uploaded to your backend | Recorded only for local playback |
| **Files and documents** | Uploaded | Read locally |
| **Calendar events / Contacts** | Synced to your backend | Read for display only |
| **Approximate / Precise location** | Sent off device | Used only for on-device features (e.g. local geofence) |
| **Web browsing history** | Collected from WebView or app behaviour | Browsing happens in user's browser, not your app |
| **App activity (interactions, search history, screens)** | Sent to your analytics backend | Held only in `Logcat` / on-device crash dumps |
| **Crash logs** | Uploaded to Crashlytics, Sentry, etc. | Only `logcat` (which user reads themselves) |
| **Diagnostics (battery life, latency)** | Sent to your backend / analytics | Held on device |
| **Device or other IDs (AAID, ANDROID_ID, IMEI)** | Read AND transmitted | Never read |

## Encryption in transit

You **must** answer "Yes" to "Is all of the user data collected by your app encrypted in transit?" if you want listing eligibility. That means:

- All non-debug network calls go over HTTPS.
- `usesCleartextTraffic="false"` in the release manifest (or scoped via Network Security Config to debug only).
- No fallback to HTTP for any of the data types you declared.

If a user-configured backend uses HTTP (some self-hosted scenarios), you can:
1. Default to HTTPS-only and require user opt-in for HTTP.
2. Document the opt-in clearly.
3. Answer "Yes, encrypted in transit" because **your default** is HTTPS, with a clear note in the description.

If you genuinely cannot enforce HTTPS, answer "No" honestly. Apps with "No" here rank lower and may get a warning badge.

## Data deletion

"Do you provide a way for users to request that their data be deleted?"

| App pattern | Required answer |
|---|---|
| Local-only data (cache, prefs, on-device DB) | **Yes** — uninstalling is sufficient. Note: "Uninstall the app to delete all locally stored data." |
| User-configured backend (you don't store) | **Yes** — direct user to the backend operator (themselves) |
| Your backend stores data | **Yes** — provide an in-app delete account flow OR an external URL where users can request deletion |
| Your backend stores data, no deletion mechanism | Stop. Build one. Play [now requires](https://support.google.com/googleplay/android-developer/answer/13327251) account-deletion for any app with a "Yes" account-creation flow. |

## Re-doing the form

You must re-open and re-submit Data safety **every time**:

- You add or remove an SDK.
- You add or remove a data type your app collects/shares.
- Google updates the Data safety taxonomy (announced via Play Console).
- A new release changes data handling.

The form is per-listing, not per-release. Updates take effect after Play review (~24 h).

## Quick patterns

### Pattern A: Local-only utility
- Top-level: **No**
- Done.

### Pattern B: Self-hosted server admin / client
- Top-level: **No** (user-supplied backend is not collection)
- If you ship Crashlytics: switch to **Yes**, declare **Crash logs** + **Diagnostics** as collected for **App functionality**, processed ephemerally, optional with crash reporting toggle.

### Pattern C: Backend you operate (typical SaaS app)
- Top-level: **Yes**
- Declare per-type: Email (Account management), User ID (Account management), App activity (Analytics), Crash logs (App functionality).
- Encrypted in transit: **Yes**.
- Deletion: in-app "Delete my account" flow.

### Pattern D: Adsupported app
- Top-level: **Yes**
- Declare AAID and any data the ad SDK sends. Use the SDK vendor's official Data safety guide.
- Encrypted in transit: **Yes**.
- Deletion: depending on backend.
