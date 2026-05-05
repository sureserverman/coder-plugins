# Google Play release preflight checklist

Run through this before every release. Failing any item delays the rollout — Play review can take 1–7 days, and the same release usually has to be re-submitted from scratch when something is missing.

## Build

- [ ] `targetSdkVersion` meets [Google's current floor](https://support.google.com/googleplay/android-developer/answer/11926878).
- [ ] `versionCode` is strictly greater than the last released `versionCode` (not just the last build).
- [ ] `versionName` updated and matches the release tag (`v<versionName>`) to keep CI and store in sync.
- [ ] `./gradlew :app:bundleRelease` produces `app/build/outputs/bundle/release/app-release.aab`.
- [ ] `apksigner verify` (on the AAB's `base.apk` extracted via `bundletool`) reports the upload-key fingerprint, not debug.
- [ ] No `usesCleartextTraffic="true"` in the manifest (or scoped to debug builds only).
- [ ] No `android:debuggable="true"` in release manifest.
- [ ] R8/ProGuard kept rules cover Retrofit, Room entities, kotlinx-serialization, Hilt — verify by smoke-testing the release variant on a device.
- [ ] **Adaptive launcher icon** in the APK/AAB: `mipmap-anydpi-v26/ic_launcher.xml` (and `ic_launcher_round.xml`) declare `<background>`, `<foreground>`, and `<monochrome>` layers; legacy PNGs exist for mdpi/hdpi/xhdpi/xxhdpi/xxxhdpi. Without this, themed icons fail on Android 13+. See `android-ui-design-figma → references/adaptive-icons.md`.

## Signing

- [ ] First upload only: Play App Signing dialog completed.
- [ ] Upload-key fingerprint recorded somewhere durable (commit message, password manager).
- [ ] Backups of `upload.keystore` + passwords exist off-machine.

## Store listing

- [ ] App name ≤ 30 chars, matches `fastlane/metadata/android/en-US/title.txt`.
- [ ] Short description ≤ 80 chars.
- [ ] Full description ≤ 4000 chars; no Play Store links, no "5-star review" CTAs, no IAP solicitations.
- [ ] Icon 512×512 PNG, no transparency, no rounded corners (Play masks).
- [ ] Feature graphic 1024×500 PNG/JPEG.
- [ ] Phone screenshots: ≥ 2, ≤ 8, 16:9 or 9:16, 320–3840 px each side.
- [ ] Tablet screenshots if app supports tablets (otherwise users see "may not work on tablets" warning).
- [ ] Primary category and tags chosen.
- [ ] Contact email is a real address (forwarder is fine).

## App content forms

- [ ] **Privacy policy** URL set, publicly reachable, served over HTTPS.
- [ ] **Data safety** form completed; matches actual app behaviour and SDK list.
- [ ] **App access** — if login-gated, working demo credentials provided in English, with step-by-step instructions.
- [ ] **Content rating** questionnaire submitted; rating displayed on the listing.
- [ ] **Ads** declaration matches reality (no ads → "No").
- [ ] **Target audience** age range set; if any age ≤ 12, Designed for Families review path applies.
- [ ] **News, government, COVID, financial features** — answered "No / Not applicable" or proper documentation attached.
- [ ] **Government apps** declaration if applicable.

## Release

- [ ] Track chosen (Internal / Closed / Open / Production).
- [ ] AAB uploaded, name auto-filled to `<versionName> (<versionCode>)`.
- [ ] Release notes per locale, ≤ 500 chars each, sourced from `fastlane/metadata/.../changelogs/<versionCode>.txt`.
- [ ] Countries / regions selected (default: all).
- [ ] Staged rollout percentage chosen (default for production: 10% → ramp up).
- [ ] If new personal account: ≥ 12 testers active in closed test for ≥ 14 consecutive days before promoting to Production.

## Post-rollout

- [ ] Watch **Crashes & ANRs** dashboard for 24–48 h.
- [ ] Watch **Statistics** for install/uninstall ratio anomalies.
- [ ] Reply to new reviews flagged as "needs response" within 7 days (affects ranking).
- [ ] Tag the release in git (`git tag v<versionName> && git push --tags`) so F-Droid auto-update picks it up.
