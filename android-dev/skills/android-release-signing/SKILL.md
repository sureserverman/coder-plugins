---
name: android-release-signing
description: Use when an Android app needs a release signing setup — a build falling back to the debug key, a release CI workflow failing because keystore secrets aren't wired, or prep before publishing. Trigger on "sign my APK", "create upload keystore", "set up release signing", "build a signed AAB".
---

# Android Release Signing

Set up once per app, then hand off to `android-fdroid-publish` or `android-play-publish`. Both publish skills assume the file names and secret names below.

## File conventions

| File | Tracked? | Content |
|---|---|---|
| `upload.keystore` | never (gitignore `*.keystore`, `*.jks`) | upload key, alias `upload`, `-validity 10000`; backed up off-machine with both passwords before the first tag |
| `keystore.properties.example` | yes | `storeFile=upload.keystore`, `storePassword=`, `keyAlias=upload`, `keyPassword=` placeholders |
| `keystore.properties` | never | the real values |

`app/build.gradle.kts` reads `rootProject.file("keystore.properties")` and creates `signingConfigs.release` only when that file exists, so contributors without the key can still build debug variants. A release build without the file falls back to the debug key; the gate below catches that.

## Gate (block release if any fail)

| Check | Pass criterion |
|---|---|
| `apksigner verify --print-certs app-release.apk` | exit `0`, subject is NOT `CN=Android Debug, O=Android, C=US` |
| Cert SHA-256 | matches `keytool -list -v -keystore upload.keystore`; record it — F-Droid pins it in `AllowedAPKSigningKeys`, Play pins it via Play App Signing |
| `git ls-files \| grep -E '\.(keystore\|jks)$\|keystore.properties$'` | no rows (if any: `git rm --cached`, rotate the key if it was ever pushed) |
| `versionCode` | strictly greater than the previous release |

## Secret-name contract (CI)

`.github/workflows/release.yml` runs on `v*` tag push and builds both `:app:assembleRelease` (APK, for F-Droid `Binaries:`) and `:app:bundleRelease` (AAB, for Play), then attaches both to the GitHub Release. The keystore exists only as repo secrets with exactly these names:

| Secret | Value |
|---|---|
| `KEYSTORE_BASE64` | `base64 -w0 upload.keystore` (delete the `.b64` file after pasting) |
| `KEYSTORE_PASSWORD` | store password |
| `KEY_ALIAS` | `upload` |
| `KEY_PASSWORD` | key password |

Workflow steps that consume them:

```yaml
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

      # ... ./gradlew :app:assembleRelease, ./gradlew :app:bundleRelease,
      # upload app-release.apk + app-release.aab to the GitHub Release ...

      - name: Clean up secrets from runner
        if: always()
        run: rm -f upload.keystore keystore.properties
```

Never `cat` `keystore.properties` back into the log.
