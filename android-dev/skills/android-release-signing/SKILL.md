---
name: android-release-signing
description: Use when setting up Android release signing — creating an upload keystore, wiring `keystore.properties`, configuring `signingConfigs.release` in Gradle, generating signed APK/AAB outputs, or wiring a GitHub Actions release workflow that decodes a base64 keystore from secrets. Trigger on "sign my APK", "create upload keystore", "set up release signing", "build a signed AAB", "release workflow won't sign", "keystore.properties missing", "Gradle uses debug key for release", or when the user asks to prepare an Android app for any store distribution (F-Droid or Google Play).
---

# Android Release Signing

Shared signing foundation for any Android distribution channel. F-Droid and Google Play both require a release-signed build; the keystore + Gradle config + CI flow are the same. Set this up **once per app**, then layer the channel-specific publish skill on top.

## When to use

- App has no `signingConfigs.release` and Gradle silently falls back to the debug key.
- User wants to publish to F-Droid (needs `app-release.apk` reproducible from tags) or Google Play (needs `app-release.aab` signed with an upload key).
- A release CI workflow exists but fails because secrets/keystore aren't wired.
- User asks "how do I sign this for release."

## Decision tree

```
Does upload.keystore exist locally and is it backed up off-machine?
├── NO → Step 1: create it. Back it up before going further.
└── YES ↓
Does keystore.properties.example exist in the repo, and keystore.properties in .gitignore?
├── NO → Step 2: scaffold both. Never commit the real properties file.
└── YES ↓
Does app/build.gradle.kts read keystore.properties and define signingConfigs.release?
├── NO → Step 3: wire it. Use signingConfig only when properties file is present.
└── YES ↓
Does ./gradlew :app:assembleRelease (APK) or :app:bundleRelease (AAB) emit a release-signed artifact?
├── NO → Step 4: verify with apksigner / bundletool.
└── YES ↓
Is there a release workflow that builds on tag push without exposing the keystore?
├── NO → Step 5: add .github/workflows/release.yml using base64-encoded secret.
└── YES → Signing setup complete. Hand off to android-fdroid-publish or android-play-publish.
```

## Step 1: Create the upload keystore

Run **once**, anywhere. The `.keystore` file is the long-term identity of the app on every store; **losing it means losing the ability to ship updates** under the same package name.

```bash
keytool -genkey -v \
  -keystore upload.keystore \
  -alias upload \
  -keyalg RSA -keysize 2048 \
  -validity 10000
```

- `validity 10000` ≈ 27 years. Google Play requires the key to be valid until at least 2033; pick a value comfortably beyond that.
- Pick a strong store password and a strong key password. They can be the same; many tools assume they are.
- **Back up `upload.keystore` and both passwords off-machine immediately** (password manager, encrypted USB, separate cloud account). Treat them like a root SSH key.

Move the file to the project root (next to `build.gradle.kts`) so the relative path in `keystore.properties` is just `upload.keystore`.

## Step 2: Scaffold `keystore.properties`

Add `keystore.properties.example` (committed) and `keystore.properties` (gitignored).

`keystore.properties.example`:

```properties
# Copy to keystore.properties and fill in real values.
# keystore.properties is gitignored; never commit it.
#
# Create an upload keystore (one-time):
#   keytool -genkey -v -keystore upload.keystore -alias upload -keyalg RSA -keysize 2048 -validity 10000
#
storeFile=upload.keystore
storePassword=your_store_password
keyAlias=upload
keyPassword=your_key_password
```

In `.gitignore`:

```
keystore.properties
upload.keystore
*.keystore
*.jks
```

**Hard gate:** if `keystore.properties` or `*.keystore` is tracked by git, stop and remove from history (`git rm --cached`, then rotate keys if it was ever pushed).

## Step 3: Wire `signingConfigs.release` in Gradle

In `app/build.gradle.kts` (Kotlin DSL):

```kotlin
import java.util.Properties
import java.io.FileInputStream

val keystorePropsFile = rootProject.file("keystore.properties")
val keystoreProps = Properties().apply {
    if (keystorePropsFile.exists()) load(FileInputStream(keystorePropsFile))
}

android {
    signingConfigs {
        if (keystorePropsFile.exists()) {
            create("release") {
                storeFile = rootProject.file(keystoreProps["storeFile"] as String)
                storePassword = keystoreProps["storePassword"] as String
                keyAlias = keystoreProps["keyAlias"] as String
                keyPassword = keystoreProps["keyPassword"] as String
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
            if (keystorePropsFile.exists()) {
                signingConfig = signingConfigs.getByName("release")
            }
        }
    }
}
```

**Why the `if (keystorePropsFile.exists())` guard:** lets contributors clone and build debug variants without owning the keystore. Release variants without the file fall back to debug signing, which is what the build error catches in Step 4.

## Step 4: Verify the signed output

For F-Droid (APK channel) **or** local sideloading:

```bash
./gradlew :app:assembleRelease
ls app/build/outputs/apk/release/app-release.apk
$ANDROID_HOME/build-tools/<version>/apksigner verify --print-certs \
  app/build/outputs/apk/release/app-release.apk
```

For Google Play (AAB channel):

```bash
./gradlew :app:bundleRelease
ls app/build/outputs/bundle/release/app-release.aab
```

**Verification gates** (block release if any fail):

| Check | Pass criterion |
|---|---|
| `apksigner verify` exit code | `0` |
| Signing cert SHA-256 | matches the fingerprint of your `upload.keystore` (compare with `keytool -list -v -keystore upload.keystore`) |
| Not signed by Android Debug | Subject must NOT be `CN=Android Debug, O=Android, C=US` |
| `versionCode` | strictly greater than the previous release |

Record the **certificate SHA-256 fingerprint** somewhere durable (commit message of first release, internal docs, password manager). F-Droid pins it with `AllowedAPKSigningKeys` and Google Play pins it via Play App Signing — once committed, it cannot be rotated without losing the listing.

## Step 5: GitHub Actions release workflow

Goal: tag push → build release → upload artifact. Keystore lives **only** as base64 in repo secrets.

One-time prep:

```bash
base64 -w0 upload.keystore > upload.keystore.b64
# Paste the contents into GitHub repo Settings → Secrets → Actions:
#   KEYSTORE_BASE64       = <contents of upload.keystore.b64>
#   KEYSTORE_PASSWORD     = <store password>
#   KEY_ALIAS             = upload
#   KEY_PASSWORD          = <key password>
# Then delete upload.keystore.b64 from disk.
```

`.github/workflows/release.yml`:

```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  release:
    name: Build and publish signed release
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'
          cache: gradle

      - name: Set up Android SDK
        uses: android-actions/setup-android@v3

      - name: Decode keystore
        run: echo "${{ secrets.KEYSTORE_BASE64 }}" | base64 -d > upload.keystore

      - name: Create keystore.properties
        run: |
          cat > keystore.properties <<EOL
          storeFile=upload.keystore
          storePassword=${{ secrets.KEYSTORE_PASSWORD }}
          keyAlias=${{ secrets.KEY_ALIAS }}
          keyPassword=${{ secrets.KEY_PASSWORD }}
          EOL

      - name: Build release APK
        run: ./gradlew :app:assembleRelease

      - name: Build release AAB
        run: ./gradlew :app:bundleRelease

      - name: Upload to GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: |
            app/build/outputs/apk/release/app-release.apk
            app/build/outputs/bundle/release/app-release.aab
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

      - name: Clean up secrets from runner
        if: always()
        run: rm -f upload.keystore keystore.properties
```

**Why both APK and AAB:** F-Droid's `Binaries:` field can pin to the GitHub-released APK (so users get the same bytes you signed), while the AAB is what you upload to Play Console. One workflow run produces both.

## Hard gates (block all release work)

| Gate | Violation | Fix |
|---|---|---|
| Keystore is the **upload key**, not the debug key | `apksigner verify --print-certs` shows `CN=Android Debug` | Rebuild after Step 3 wiring; verify `keystore.properties` exists at build time |
| Keystore not in git | `git ls-files \| grep -E '\.(keystore\|jks)$'` returns rows | `git rm --cached`; rotate key if the commit was ever pushed |
| `keystore.properties` not in git | `git ls-files \| grep keystore.properties$` returns the real file | Add to `.gitignore`; only `keystore.properties.example` is tracked |
| Secrets not in source | grep for `storePassword=`/`keyPassword=` in committed files returns hits | Move to `keystore.properties` or CI secrets |
| Backup exists | No off-machine copy of `upload.keystore` + passwords | **Stop. Make the backup before tagging.** Lost key = lost app identity on every store. |

## Common mistakes

| Mistake | Correct |
|---|---|
| Hardcoding `storePassword = "hunter2"` in `build.gradle.kts` | Read from `keystore.properties` (gitignored) or env vars in CI |
| Committing `upload.keystore` "for the team" | Each release is signed by CI from base64 secret; nobody else needs the file |
| Reusing the debug keystore for release | Debug key is per-machine and not durable; Play and F-Droid pin the cert fingerprint |
| Bumping `versionName` but forgetting `versionCode` | Both stores reject uploads where `versionCode` ≤ the current released code |
| `validity 365` on `keytool` | Pick ≥ 27 years; you cannot rotate without losing the listing |
| Letting CI print `keystore.properties` to logs | Keep the heredoc; never `cat` it back; clean up in `if: always()` step |

## Hand-off

After this skill completes:
- F-Droid → switch to `android-fdroid-publish`.
- Google Play → switch to `android-play-publish`.
