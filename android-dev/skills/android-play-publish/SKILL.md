---
name: android-play-publish
description: Use when preparing an already-signed Android app for publication on Google Play, or navigating Play Console setup, store listing, or policy forms for an existing listing. Trigger on "publish to Google Play", "submit to play store", "Play Console setup", "Data safety form".
---

# Android Google Play Publish

## Prerequisites

- `android-release-signing` already ran (you have an upload keystore and `:app:bundleRelease` produces `app-release.aab`).
- Privacy policy is **publicly hosted** at a stable URL (GitHub-rendered markdown, GitHub Pages, or your own site). Required even for apps that don't collect user data.
- `targetSdkVersion` meets Google's target API floor: API 36 (Android 16) for new phone and tablet apps and updates since 2026-08-31 (Wear OS and Automotive 35, TV and XR 34) (checked 2026-11-10, https://support.google.com/googleplay/android-developer/answer/11926878).

## Quick audit (punchlist)

Audit current state without writing anything:

```bash
test -f app/build.gradle.kts || test -f app/build.gradle
test -f keystore.properties.example
test -f keystore.properties
test -f upload.keystore
test -d fastlane/metadata/android/en-US
test -f fastlane/metadata/android/en-US/images/icon.png
test -f fastlane/metadata/android/en-US/images/featureGraphic.png
ls fastlane/metadata/android/en-US/images/phoneScreenshots/ 2>/dev/null | wc -l
grep -E 'targetSdk\s*=' app/build.gradle.kts
grep -E 'versionCode\s*=' app/build.gradle.kts
grep -E 'versionName\s*=' app/build.gradle.kts
test -f docs/privacy.md && echo "local-privacy-policy"
test -f .github/workflows/release.yml && echo "release-workflow"
```

Then mark each item `[x]` (done), `[ ]` (missing), or `[?]` (needs user input), grouped by Play Console section so the user can map directly to forms:

#### Build prerequisites
- [ ] App module at `app/` with `applicationId` set
- [ ] `targetSdk ≥ 36` for phone/tablet (Play floor since 2026-08-31; checked 2026-11-10, https://support.google.com/googleplay/android-developer/answer/11926878)
- [ ] `versionCode` strictly greater than last released (compare with `git tag` or last AAB if accessible)
- [ ] `keystore.properties` wired and `signingConfigs.release` defined
- [ ] `./gradlew :app:bundleRelease` succeeds and produces `app/build/outputs/bundle/release/app-release.aab`

#### Store listing (Grow users → Store presence → Main store listing)
- [ ] App name ≤ 30 chars (`title.txt`)
- [ ] Short description ≤ 80 chars (`short_description.txt`)
- [ ] Full description ≤ 4000 chars (`full_description.txt`)
- [ ] App icon: 512×512 PNG, no transparency
- [ ] Feature graphic: 1024×500 PNG/JPEG (**required by Play**, not just F-Droid)
- [ ] At least 2 phone screenshots, max 8, in `images/phoneScreenshots/`
- [ ] Tablet screenshots if app supports tablets
- [ ] Release notes for current `versionCode` in `changelogs/<versionCode>.txt` (≤ 500 chars)

#### App content (Policy → App content)
- [ ] Privacy policy at a public HTTPS URL (suggest GitHub: `https://github.com/<owner>/<repo>/blob/main/docs/privacy.md`)
- [ ] Data safety form answered
- [ ] App access — if login-gated, demo credentials prepared
- [ ] Content rating questionnaire planned (the IARC form runs in Play Console — can't pre-fill, but list expected rating)
- [ ] Ads declaration
- [ ] Target audience age range

#### Release infrastructure
- [ ] `.github/workflows/release.yml` builds AAB on tag push (optional but recommended)
- [ ] Service account for `fastlane supply` if automating uploads (optional)

Report the punchlist verbatim, grouped by section. Do not change files during an audit-only pass.

This audit maps to four modes of engagement:

- **check** — audit only (the punchlist above), no writes.
- **init** — full flow: signing → AAB build → store listing scaffold → App content checklist.
- **aab** — only build and verify `app-release.aab`.
- **listing** — only scaffold/repair `fastlane/metadata/android/en-US/` for Play.

## Store limits

Play Console → **Grow users** → **Store presence** → **Main store listing**. The listing reuses the `fastlane/metadata/android/en-US/` tree from `android-fdroid-publish`; `fastlane supply` reads the same tree.

| Field | Source | Constraint |
|---|---|---|
| App name | `title.txt` | ≤ 30 chars |
| Short description | `short_description.txt` | ≤ 80 chars |
| Full description | `full_description.txt` | ≤ 4000 chars |
| App icon | `images/icon.png` | exactly 512×512 PNG, no transparency, no alpha |
| Feature graphic | `images/featureGraphic.png` | exactly 1024×500 PNG/JPEG, **required by Play** |
| Phone screenshots | `images/phoneScreenshots/*.png` | 2–8 images, 16:9 or 9:16 ratio, 320–3840 px each side |
| 7-inch tablet screenshots | `images/sevenInchScreenshots/*.png` | optional |
| 10-inch tablet screenshots | `images/tenInchScreenshots/*.png` | optional |
| Release notes | `changelogs/<versionCode>.txt` | ≤ 500 chars per locale |

New personal accounts created after November 2023 must run a closed test with **≥ 12 testers** for **14 consecutive days** before Production unlocks ([policy](https://support.google.com/googleplay/android-developer/answer/14151465)).

## Reference files

- `references/store-listing-checklist.md` — per-release preflight checklist.
- `references/data-safety-decision-table.md` — common app patterns mapped to correct Data safety answers. Read it before answering the Data safety form.
