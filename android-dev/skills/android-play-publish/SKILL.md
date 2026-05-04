---
name: android-play-publish
description: Use when preparing an Android app for publication on Google Play — building a release AAB, creating the app in Play Console, filling Data safety / App access / Content rating, drafting store listing copy and assets (icon, feature graphic, screenshots), choosing release tracks (Internal / Closed / Production), navigating the 14-day closed-test rule for new accounts, or setting up `fastlane supply` for automated metadata uploads. Trigger on "publish to Google Play", "submit to play store", "Play Console setup", "build AAB for play", "Data safety form", "play store listing", "app access demo credentials", "Play App Signing", "closed test 12 testers", "fastlane supply".
---

# Android Google Play Publish

Get an Android app onto **Google Play**. Play uploads use the **AAB** (Android App Bundle) format, signed with your upload key, then Google re-signs per device with their own app-signing key. This skill covers everything that happens after you have a signed build — Play Console workflow, required forms, store listing, and rollout. Verify each requirement against [Google's official guidance](https://support.google.com/googleplay/android-developer/answer/9859455) before submitting; policies change frequently.

## Prerequisites

- `android-release-signing` already ran (you have an upload keystore and `:app:bundleRelease` produces `app-release.aab`).
- Privacy policy is **publicly hosted** at a stable URL (GitHub-rendered markdown, GitHub Pages, or your own site). Required even for apps that don't collect user data.
- `targetSdkVersion` meets [Google's current target API floor](https://support.google.com/googleplay/android-developer/answer/11926878) (as of this writing: API 35 / Android 15 for new submissions).
- Google account + ability to pay the **one-time $25 USD** developer registration fee.

If `targetSdkVersion` is below the current floor, stop and bump it first — Play rejects the upload otherwise.

## Decision tree

```
Developer account created and fee paid?
├── NO → Step 1
└── YES ↓
App created in Play Console?
├── NO → Step 2
└── YES ↓
AAB built and Play App Signing accepted on first upload?
├── NO → Step 3
└── YES ↓
Store listing complete (name, descriptions, icon, feature graphic, screenshots)?
├── NO → Step 4
└── YES ↓
App content forms complete (Privacy policy, Data safety, App access, Content rating, Ads, Target audience)?
├── NO → Step 5
└── YES ↓
Release track chosen and AAB uploaded with release notes?
├── NO → Step 6
└── YES ↓
New personal account post-Nov-2023?
├── YES → Step 7: 12+ testers, 14-day closed test before Production unlock
└── NO  → Submit to Production directly
```

## Step 1: Developer account

1. Sign in at **https://play.google.com/console** with the Google account you want as the publisher.
2. Accept the Developer Distribution Agreement.
3. Pay the **one-time $25 USD** fee (no subscription, no per-app fee).
4. Complete account details — for **personal** accounts Google requires identity verification (government-issued ID, phone). For **organization** accounts you also need a D-U-N-S number.

**New personal accounts created after November 2023** are subject to the [14-day closed test rule](https://support.google.com/googleplay/android-developer/answer/14151465): you must run a closed test with **≥ 12 testers** for **14 consecutive days** before Production unlocks. Plan around this — start the test as early as possible, even with a placeholder release.

## Step 2: Create the app in Play Console

In Play Console → **Create app**:

| Field | Value |
|---|---|
| App name | ≤ 30 chars, matches `fastlane/.../title.txt` |
| Default language | Locale that matches your fastlane default (usually `en-US` → "English (United States)") |
| App or game | App |
| Free or paid | Free (paid apps require a separate merchant account) |
| Declarations | Tick: complies with Developer Program Policies, complies with US export laws |

Click **Create app**. The dashboard now shows the left sidebar with **Test and release**, **Monitor and improve**, **Grow users**, **Monetize with Play**, and the **Policy** sections.

## Step 3: Build the AAB and accept Play App Signing

```bash
./gradlew :app:bundleRelease
ls -lh app/build/outputs/bundle/release/app-release.aab
```

Verify the AAB's signing cert matches your upload keystore (see `android-release-signing` Step 4).

In Play Console: **Test and release** → **Production** (or **Closed testing** if you're a new personal account) → **Create new release** → **Upload**. On first upload, Play shows the **Play App Signing** screen:

- **Recommended:** Let Google manage the app signing key. You keep your **upload key**; Google holds the **app signing key**. Updates only need to match the upload key.
- **Alternative (legacy):** Upload your own app signing key. Only do this if you have a strict reason — most apps benefit from Google managing the signing key (key recovery, rotation).

Once accepted, **Play App Signing is permanent for this `applicationId`** — the app signing cert fingerprint is pinned forever. Save the fingerprint Google shows you (Play Console → **Setup** → **App signing**) for use elsewhere (e.g. Google Sign-In console, Firebase, deep links).

## Step 4: Store listing

In Play Console → **Grow users** → **Store presence** → **Main store listing**.

Reuse the assets you already created for `android-fdroid-publish` (`fastlane/metadata/android/en-US/`):

| Field | Source | Constraint |
|---|---|---|
| App name | `title.txt` | ≤ 30 chars |
| Short description | `short_description.txt` | ≤ 80 chars |
| Full description | `full_description.txt` | ≤ 4000 chars |
| App icon | `images/icon.png` | exactly 512×512 PNG, no transparency, no alpha |
| Feature graphic | `images/featureGraphic.png` | exactly 1024×500 PNG/JPEG, **required by Play** |
| Phone screenshots | `images/phoneScreenshots/*.png` | 2–8 images, 16:9 or 9:16 ratio, 320–3840 px each side |
| 7-inch tablet screenshots | `images/sevenInchScreenshots/*.png` | optional but improves tablet placement |
| 10-inch tablet screenshots | `images/tenInchScreenshots/*.png` | optional |

Optional but high-leverage:
- **App category** (one primary, e.g. "Tools", "Productivity") — appears in browse rankings.
- **Tags** — pick 5; these influence Play's recommendations more than keywords in the description.
- **Contact email** — public on the listing; use a forwarder.

Save. The listing is editable later, but changes go through Play review (often hours, sometimes days).

## Step 5: App content forms

These are mandatory before any release. Find them under **Policy** → **App content**.

### Privacy policy
Paste the **public URL** of your privacy policy. GitHub-rendered markdown is acceptable: `https://github.com/<owner>/<repo>/blob/main/docs/privacy.md`. URL must remain reachable; Play crawls it periodically.

### Data safety
A questionnaire about what data your app collects/shares. **Lying here is a policy violation that gets apps suspended.** Common honest answers for a self-hosted-server admin or local-only utility:

| Question | Typical answer |
|---|---|
| Does your app collect or share any user data? | **No** if everything stays on device and is sent only to a user-configured backend |
| Is all user data encrypted in transit? | **Yes** if HTTPS-only and `usesCleartextTraffic="false"` |
| Do users have a way to request data deletion? | **Yes** if data is local; describe the in-app delete or uninstall path |
| Personal info / Financial / Location / Messages / Photos / Files / etc. | Tick only what you actually read or transmit |

If you DO collect data: each data type needs (a) collected/shared, (b) optional/required, (c) purpose, (d) processed ephemerally or stored. Re-do this every release that changes data handling.

### App access
If non-trivial functionality is gated behind login, you **must** provide reviewer credentials:

- **Server URL** — reachable from anywhere, no geo-fencing, no IP allowlists.
- **Username + password** — reusable, not OTP-protected.
- **Step-by-step instructions** in English.

Failed reviewer login is the #1 cause of policy rejections for admin / B2B / self-hosted apps. If your app talks to user-supplied backends and you have no public demo, spin up a throwaway server for review only and document it under App access.

### Content rating
Take the IARC questionnaire. For most utilities the answers are all "No" and the result is **Everyone**. The badge appears on the listing automatically.

### Ads
"Does your app contain ads?" — **No** for AOSP-style admin/utility apps. Lying triggers suspension; Google scans for ad-SDK signatures.

### Target audience and content
Pick the age groups your app targets. For **anything ≤ 12**, you trigger Play's [Designed for Families](https://support.google.com/googleplay/android-developer/answer/9893335) program and a much stricter review path. For admin/dev tools pick **18+** and "primarily directed at adults".

### Government apps, COVID-19, news, financial features
Answer "No" or "Not applicable" unless they clearly apply. If you DO ship any of these, Play requires extra documentation (government affiliation letters, news outlet registration, etc.).

## Step 6: Release tracks

Tracks in increasing audience size: **Internal** → **Closed** → **Open** → **Production**.

| Track | Audience | Use for |
|---|---|---|
| Internal testing | ≤ 100 named testers via email | Smoke-testing the AAB itself; near-instant rollout |
| Closed testing | Up to thousands of testers via email lists or Google Groups | Beta groups; **required ≥ 14 days for new personal accounts** |
| Open testing | Anyone with the opt-in link | Optional public beta; visible on Play but tagged as "Early access" |
| Production | Everyone in selected countries | The real release |

To upload:

1. **Test and release** → choose track → **Create new release**.
2. Drag in `app/build/outputs/bundle/release/app-release.aab`.
3. **Release name** auto-fills to `versionName (versionCode)`. Leave it.
4. **Release notes** — one `<en-US>…</en-US>` block per locale, ≤ 500 chars each. Reuse `fastlane/.../changelogs/<versionCode>.txt` content.
5. **Save** → **Review release** → **Start rollout to <track>**.

For production releases, prefer **Staged rollout**: start at 5–10% and increase over days. Lets you catch crash spikes before they hit everyone.

## Step 7: 14-day closed test (new personal accounts only)

Required only for personal accounts created after Nov 2023, before Production unlocks.

1. Create a Google Group (e.g. `myapp-beta@googlegroups.com`) or an email list.
2. **Closed testing** → **Testers** → add the group/list. Need **≥ 12 distinct accounts** that **install** the app from the test link.
3. Push your release to closed testing. Share the opt-in URL Play generates.
4. Wait **14 consecutive days** with the testers actively having the app installed. Play tracks this via opt-in events; uninstalls can reset the counter.
5. **Apply for Production access** under closed testing; Play reviews and unlocks Production within ~48 hours.

Track tester count and uptime in Play Console → **Closed testing** → **Tester progress**.

## Optional: `fastlane supply` for automated uploads

After the first manual upload (which needs human acceptance of Play App Signing), all subsequent uploads can be automated.

1. Play Console → **Setup** → **API access** → create a service account with **Release manager** role.
2. Download the JSON key. Treat it like a keystore — keep it out of git, store in secrets.
3. Add fastlane to the project:

```bash
bundle init
echo 'gem "fastlane"' >> Gemfile
bundle install
bundle exec fastlane init   # pick "Android" → "Automate beta distribution"
```

4. Edit `fastlane/Appfile`:

```ruby
json_key_file("path/to/play-service-account.json")
package_name("com.example.app")
```

5. Edit `fastlane/Fastfile`:

```ruby
default_platform(:android)

platform :android do
  desc "Deploy a new version to internal testing"
  lane :internal do
    gradle(task: "bundleRelease")
    upload_to_play_store(
      track: "internal",
      aab: "app/build/outputs/bundle/release/app-release.aab",
      skip_upload_apk: true,
      skip_upload_metadata: false,         # picks up fastlane/metadata
      skip_upload_changelogs: false,
      skip_upload_images: false,
      skip_upload_screenshots: false,
    )
  end

  desc "Promote internal to production with staged rollout"
  lane :promote do
    upload_to_play_store(
      track: "internal",
      track_promote_to: "production",
      rollout: "0.1",
    )
  end
end
```

6. CI: encode the JSON key as a base64 secret; decode in the workflow before `bundle exec fastlane internal`.

This is the same `fastlane/metadata/android/en-US/` tree you populated for F-Droid — `supply` reads it directly, so the two channels share one source of truth.

## Hard gates

| Gate | Why |
|---|---|
| `targetSdkVersion` ≥ Google's current floor | Play rejects uploads that don't target the required API level |
| AAB signed with upload key (not debug, not Play app signing) | First upload accepts; mismatched signature on later uploads is rejected with no recourse |
| `versionCode` strictly increases | Play rejects same-or-lower versionCode |
| Privacy policy URL is publicly reachable | Play crawls; 404 → suspension |
| Data safety form matches actual behaviour | Mismatch is a policy violation; Google scans SDKs and traffic |
| App access credentials work for reviewers | #1 rejection reason for login-gated apps |
| No prohibited SDKs (banned ad networks, location-misuse, etc.) | Suspension; check the [Developer Program Policies](https://play.google.com/about/developer-content-policy/) |

## Common mistakes

| Mistake | Correct |
|---|---|
| Uploading APK | Play requires AAB for new apps; APK only for legacy listings created before Aug 2021 |
| Forgetting feature graphic | Listing won't go live without 1024×500 `featureGraphic.png` |
| Marking "No data collected" while using Crashlytics/Firebase | Crashlytics counts as collection; declare it under Crash logs |
| Free-text App access "you need a server, contact me" | Reviewers won't email you. Provide working credentials inline. |
| Test track with 11 testers and going to Production | New accounts need ≥ 12 testers AND 14 consecutive days; Production stays locked otherwise |
| Reusing the same `versionCode` for a re-upload | Play rejects; bump even for trivial re-uploads |
| Privacy policy at `localhost` or a private wiki | Must be publicly reachable; GitHub markdown URLs work fine |
| Letting Play App Signing screen sit and re-uploading | First upload locks the cert pin; abandoning mid-flow can leave the listing in an unrecoverable state — finish the dialog |

## Reference files

- `references/store-listing-checklist.md` — printable preflight checklist for every release.
- `references/data-safety-decision-table.md` — common app patterns mapped to correct Data safety answers.
