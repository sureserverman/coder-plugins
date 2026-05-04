---
description: Prepare an Android app for Google Play submission — signing, AAB build, store listing, App content checklist
argument-hint: [check|init|aab|listing] [applicationId]
allowed-tools: [
  "Read",
  "Write",
  "Edit",
  "Glob",
  "Grep",
  "Bash(./gradlew:*)",
  "Bash(keytool:*)",
  "Bash(awk:*)",
  "Bash(ls:*)",
  "Bash(find:*)",
  "Bash(test:*)",
  "Bash(git:*)",
  "Bash(cat:*)",
  "Bash(stat:*)",
  "Bash(file:*)",
  "Bash(mkdir:*)",
  "Bash(magick:*)",
  "Bash(identify:*)"
]
---

# Android Prepare Play

Walk through everything needed to submit the current Android app to Google Play: release signing, AAB build, store listing copy and assets, and the App content checklist (Privacy policy, Data safety, App access, Content rating). The user uploads to Play Console themselves — this command produces and validates the artefacts.

## Arguments

The user invoked this command with: $ARGUMENTS

## Modes

- **check** (default if no args) — audit current state and report a punchlist of what's missing.
- **init** — full flow: signing → AAB build → store listing scaffold → App content checklist.
- **aab** — only build and verify `app-release.aab`.
- **listing** — only scaffold/repair `fastlane/metadata/android/en-US/` for Play.

If the user passed an `applicationId` (e.g. `com.example.app`) as the second arg, use it. Otherwise read it from `app/build.gradle.kts` and confirm.

## Instructions

### 1. Detect repo state

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

### 2. `check` mode — produce a punchlist

Group the punchlist by Play Console section so the user can map directly to forms.

#### Build prerequisites
- [ ] App module at `app/` with `applicationId` set
- [ ] `targetSdk ≥ 35` (current Play floor as of 2026-05; verify against [Google's docs](https://support.google.com/googleplay/android-developer/answer/11926878))
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

Report the punchlist verbatim, grouped by section. Do not change files in `check` mode.

### 3. `init`, `aab`, `listing` modes

#### Signing (skip in `aab`-only and `listing`-only modes)

If `keystore.properties` isn't wired, invoke the `android-release-signing` skill. Do not duplicate its content.

#### Build the AAB (`init`, `aab` modes)

```bash
./gradlew :app:bundleRelease
```

Verify after build:

```bash
AAB=app/build/outputs/bundle/release/app-release.aab
test -f "$AAB" || { echo "FAIL: AAB not produced"; exit 1; }
ls -lh "$AAB"
file "$AAB"   # should report "Java archive data (JAR)" or zip
```

If the build fails because `signingConfig` falls back to debug, stop and rewire signing per `android-release-signing`.

For deeper verification (extract base APK and verify cert):

```bash
# requires bundletool — install via: brew install bundletool / sdkmanager
bundletool build-apks --bundle="$AAB" --output=/tmp/app.apks --mode=universal
unzip -p /tmp/app.apks universal.apk > /tmp/app.apk
$ANDROID_HOME/build-tools/*/apksigner verify --print-certs /tmp/app.apk
```

The cert subject must NOT be `CN=Android Debug, O=Android, C=US`. The SHA-256 fingerprint must match `keytool -list -v -keystore upload.keystore -alias upload`.

#### Listing scaffold (`init`, `listing` modes)

The `fastlane/metadata/android/en-US/` tree is shared with F-Droid. If `/android-prepare-fdroid` already ran, the text files exist. Add Play-specific assets:

```bash
mkdir -p fastlane/metadata/android/en-US/images/{phoneScreenshots,sevenInchScreenshots,tenInchScreenshots}
```

For each missing file:

| File | Action |
|---|---|
| `title.txt` / `short_description.txt` / `full_description.txt` | If absent, write placeholders sourced from README. If present, validate length and warn on overflow. |
| `images/icon.png` | Verify 512×512 PNG with `identify`. If absent, instruct user to export. Don't generate. |
| `images/featureGraphic.png` | Verify 1024×500 if present. If absent, instruct: "Required by Play. Create a 1024×500 banner with the app name + tagline." |
| `images/phoneScreenshots/*.png` | Count files. If `play-screenshots/phone6in_*.png` exists, suggest `cp` into `phoneScreenshots/` with renumbering (`01_`, `02_`). |
| `changelogs/<currentVersionCode>.txt` | Write `<TODO: release notes for v<versionName>>` if absent. |

Validate image dimensions:

```bash
for f in fastlane/metadata/android/en-US/images/icon.png \
         fastlane/metadata/android/en-US/images/featureGraphic.png; do
  test -f "$f" && identify -format '%wx%h %i\n' "$f"
done
```

Flag any mismatch (icon must be exactly 512×512, feature graphic exactly 1024×500).

#### App content draft

Write `docs/play-app-content.md` (or update if it exists) with a draft of the answers the user will paste into Play Console:

```markdown
# Play Console — App content

## Privacy policy
URL: https://github.com/<owner>/<repo>/blob/main/docs/privacy.md

## Data safety
- Does your app collect or share any user data? **<Yes/No>**
- (If Yes) Per-data-type table: see android-play-publish/references/data-safety-decision-table.md

## App access
- All functionality available without restrictions? **<Yes/No>**
- (If No) Demo credentials:
  - Server URL: <URL reachable globally>
  - Username: <reusable login>
  - Password: <reusable password>
  - Steps: 1. ... 2. ...

## Ads
- Contains ads? **<Yes/No>**

## Content rating
- Expected rating: <Everyone / Teen / Mature 17+ / Adults only 18+>
- Notable answers: <none / violence: no / nudity: no / etc.>

## Target audience
- Age groups: <18+ / 13-17 / Children — pick one>

## News, government, COVID, financial
- News app: No
- Government app: No
- COVID-19 contact tracing: No
- Financial features: <Yes/No — flag if app has crypto/loans/insurance UI>
```

Do not invent answers. Use `<...>` placeholders so the user has to fill them in deliberately. Reference the `android-play-publish/references/data-safety-decision-table.md` for the Data safety section.

### 4. Report

Show the user:

- AAB path + size if built.
- Apksigner verification result (if bundletool available).
- Punchlist of what's complete vs what still needs the user (assets, copy, App content forms).
- Next steps (in order):
  1. Create / verify Play Console developer account.
  2. Create the app in Play Console with the matching `applicationId`.
  3. First upload triggers Play App Signing dialog — accept Google's recommended option.
  4. Fill in store listing using the scaffolded `fastlane/metadata/android/en-US/` files.
  5. Complete App content forms using the draft in `docs/play-app-content.md`.
  6. Push AAB to Internal track for smoke test, then Closed (≥ 12 testers, 14 days for new accounts), then Production.
- Link to `android-play-publish` skill for the deeper reference, and `references/store-listing-checklist.md` for the per-release preflight.

Do **not** upload to Play Console, create service accounts, or interact with Google APIs — those are user actions.
