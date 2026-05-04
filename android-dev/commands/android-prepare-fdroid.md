---
description: Prepare an Android app for F-Droid submission — signing, fastlane metadata, fdroiddata YAML
argument-hint: [check|init|metadata|yaml] [applicationId]
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
  "Bash(mkdir:*)"
]
---

# Android Prepare F-Droid

Walk through everything needed to submit the current Android app to F-Droid: release signing, `fastlane/metadata/android/en-US/` tree, and the `docs/f-droid/<applicationId>.yml` build recipe. The user submits the YAML to `gitlab.com/fdroid/fdroiddata` themselves — this command produces the artefacts they need to do that.

## Arguments

The user invoked this command with: $ARGUMENTS

## Modes

- **check** (default if no args) — audit current state and report a punchlist of what's missing.
- **init** — full flow: signing → fastlane scaffold → YAML draft.
- **metadata** — only scaffold/repair `fastlane/metadata/android/en-US/`.
- **yaml** — only draft `docs/f-droid/<applicationId>.yml`.

If the user passed an `applicationId` (e.g. `com.example.app`) as the second arg, use it. Otherwise, read it from `app/build.gradle.kts` (`applicationId = "..."` line) or `app/build.gradle` and confirm with the user.

## Instructions

### 1. Detect repo state

Read these signals before doing anything:

```bash
test -f app/build.gradle.kts || test -f app/build.gradle  # is this an Android app?
test -f keystore.properties.example                        # signing scaffolded?
test -f keystore.properties                                # signing wired locally?
test -d fastlane/metadata/android/en-US                    # fastlane tree exists?
ls fastlane/metadata/android/en-US/changelogs/ 2>/dev/null # changelogs present?
test -f fastlane/metadata/android/en-US/images/icon.png   # icon present?
git tag --list 'v*' | tail -n 5                            # tagged releases?
grep -E 'applicationId\s*=' app/build.gradle.kts 2>/dev/null # extract applicationId
grep -E 'versionCode\s*=' app/build.gradle.kts            # current versionCode
grep -E 'versionName\s*=' app/build.gradle.kts            # current versionName
```

If `app/build.gradle.kts` and `app/build.gradle` are both missing, stop and tell the user this isn't an Android app root.

### 2. `check` mode — produce a punchlist

For each item below, mark `[x]` (done), `[ ]` (missing), or `[?]` (needs user input):

- [ ] Public Git remote on GitHub/GitLab/Codeberg (`git remote -v`)
- [ ] At least one annotated tag matching `v*`
- [ ] `keystore.properties.example` committed
- [ ] `keystore.properties` and `*.keystore` in `.gitignore`
- [ ] `app/build.gradle.kts` reads `keystore.properties` and defines `signingConfigs.release`
- [ ] `./gradlew :app:assembleRelease` succeeds and produces a release-signed APK (run only if the user opts in)
- [ ] `fastlane/metadata/android/en-US/title.txt` (≤ 50 chars)
- [ ] `fastlane/metadata/android/en-US/short_description.txt` (≤ 80 chars)
- [ ] `fastlane/metadata/android/en-US/full_description.txt` (≤ 4000 chars)
- [ ] `fastlane/metadata/android/en-US/images/icon.png` (512×512 PNG)
- [ ] `fastlane/metadata/android/en-US/changelogs/<currentVersionCode>.txt`
- [ ] `docs/f-droid/<applicationId>.yml` drafted with current commit hash and signing-cert SHA-256

Report the punchlist verbatim to the user. Do not change files in `check` mode.

### 3. `init`, `metadata`, `yaml` modes — execute

For any mode that writes files:

#### Signing (skip in `metadata` and `yaml` modes)

If signing isn't set up, invoke the `android-release-signing` skill. Do not duplicate its content — reference it and let the skill drive.

#### Fastlane scaffold

Create missing files. **Never overwrite existing content** — if a file already has user copy, leave it.

```bash
mkdir -p fastlane/metadata/android/en-US/changelogs
mkdir -p fastlane/metadata/android/en-US/images/phoneScreenshots
```

For each missing file, write a placeholder the user can edit:

| File | Placeholder |
|---|---|
| `title.txt` | `<App Name>` |
| `short_description.txt` | `<One-line description, ≤ 80 chars, doesn't start with the app name>` |
| `full_description.txt` | Stub: 1–2 paragraphs of "What it does / Who it's for / Key features". Pull from README's first section if available. |
| `changelogs/<versionCode>.txt` | `Initial F-Droid release.` (only on first release) |

For `images/icon.png`: do NOT generate one. Tell the user to export 512×512 PNG (no transparency, no rounded corners) from their design source. Suggest:

```bash
# If you have a source PNG larger than 512×512:
magick path/to/source.png -resize 512x512 -background white -alpha remove \
  fastlane/metadata/android/en-US/images/icon.png
```

For `phoneScreenshots/`: if `play-screenshots/` already exists in the repo (from `/android-screenshots`), suggest copying the phone-form-factor PNGs:

```bash
cp play-screenshots/phone6in_*.png fastlane/metadata/android/en-US/images/phoneScreenshots/
```

#### `docs/f-droid/<applicationId>.yml`

Read the template at the plugin's `skills/android-fdroid-publish/references/fdroiddata-template.yml` and write a filled-in copy to `docs/f-droid/<applicationId>.yml`.

Fill in what you can detect:

- `Categories` — ask the user to pick from F-Droid's [category list](https://gitlab.com/fdroid/fdroiddata/-/blob/master/CATEGORIES.md). Don't guess.
- `License` — read from `LICENSE` file or ask. Use SPDX identifiers (`Apache-2.0`, `GPL-3.0-or-later`, `MIT`).
- `AuthorName` / `AuthorEmail` — read from `git config user.name` / `user.email`, confirm with user.
- `SourceCode` / `Repo` / `IssueTracker` — read from `git remote get-url origin`. Convert SSH to HTTPS.
- `Builds:` block — one entry. Use `versionName` / `versionCode` from `app/build.gradle.kts`, and the commit hash of the latest matching `v<versionName>` tag (`git rev-list -n 1 v<versionName>`). Set `subdir: app` if the app module is at `app/`, otherwise omit.
- `Binaries:` — only fill in if the user has a `.github/workflows/release.yml` that uploads to GitHub Releases. Pattern: `https://github.com/<owner>/<repo>/releases/download/v%v/app-release.apk`. Otherwise comment it out.
- `AllowedAPKSigningKeys:` — compute if `upload.keystore` is present locally:
  ```bash
  keytool -list -v -keystore upload.keystore -alias upload \
    | awk '/SHA256:/ {gsub(":",""); print tolower($2)}'
  ```
  If the keystore isn't accessible, leave a `<TODO: compute from keytool>` placeholder and explain how.
- `AutoUpdateMode: Version` and `UpdateCheckMode: Tags` — always set these.
- `CurrentVersion` / `CurrentVersionCode` — match the `Builds:` entry.

### 4. Report

Show the user:

- Which files were created vs already existed (don't overwrite anything they had).
- The full punchlist with `[x]`/`[ ]`/`[?]` markers.
- Next steps: tag a release if not yet tagged, push to public remote, then **either** open an RFP at https://gitlab.com/fdroid/rfp/-/issues **or** fork `gitlab.com/fdroid/fdroiddata` and submit `metadata/<applicationId>.yml` as an MR.
- Link to the `android-fdroid-publish` skill for the deeper "what each field means" reference.

Do **not** push to git, create tags, or open external issues/MRs — those are user actions.
