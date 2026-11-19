---
name: android-fdroid-publish
description: Use when preparing an already-signed Android app for publication on F-Droid, scaffolding or repairing its fastlane metadata, or maintaining an existing listing after a new release. Trigger on "publish to F-Droid", "submit to fdroid", "fastlane metadata", "fdroiddata YAML".
---

# Android F-Droid Publish

Get an Android app onto **F-Droid**. F-Droid does not accept your APK — it clones your **public source repo** and builds the app on its own infrastructure, then signs with its own key (or, with `AllowedAPKSigningKeys` pinned, distributes the binary you built yourself). This skill covers everything in your repo; the actual submission happens in `gitlab.com/fdroid/fdroiddata`.

## Prerequisites

- Release signing is set up per the `android-build` stack page (`~/.claude/vault-stacks/vault-stack-android-build.md`) (you have an upload keystore and a working `:app:assembleRelease`).
- App lives in a **public** Git repo (GitHub, GitLab, Codeberg, etc.).
- You have **at least one tagged release** with `versionCode` ≥ 1. F-Droid needs a tag (e.g. `v1.0.0`) that the metadata's `Builds:` block can point at by commit hash.

If any prerequisite is missing, set up signing per that page or stop and ask.

## Quick audit (punchlist)

Before walking the full decision tree, you can audit current state without writing anything.

Detect repo state first:

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

If `applicationId` isn't otherwise known, read it from `app/build.gradle.kts` (`applicationId = "..."`).

Then mark each item `[x]` (done), `[ ]` (missing), or `[?]` (needs user input):

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

Report the punchlist verbatim to the user. Do not change files during an audit-only pass.

This audit maps to four modes of engagement:

- **check** — audit only (the punchlist above), no writes.
- **init** — full flow: signing → fastlane scaffold → YAML draft (Steps 1–3 below).
- **metadata** — only scaffold/repair `fastlane/metadata/android/en-US/` (Step 1).
- **yaml** — only draft `docs/f-droid/<applicationId>.yml` (Step 2).

## Decision tree

```
Public repo + tagged release exists?
├── NO → fix prerequisites first
└── YES ↓
fastlane/metadata/android/en-US/ scaffolded with title, descriptions, icon?
├── NO → Step 1
└── YES ↓
docs/f-droid/<applicationId>.yml drafted with Builds: pinned to commit hash?
├── NO → Step 2
└── YES ↓
Choose path: RFP issue (Option A) or direct MR (Option B)?
├── A → Step 3a: open RFP at gitlab.com/fdroid/rfp
└── B → Step 3b: fork fdroiddata, add metadata file, open MR
```

## Step 1: Fastlane metadata in the app repo

F-Droid pulls the store-listing copy from the **app repo itself**. Scaffold `fastlane/metadata/android/en-US/` to the directory shape, per-file limits, hard rules and locale conventions in the `android-store-metadata` stack page (`~/.claude/vault-stacks/vault-stack-android-store-metadata.md`).

## Step 2: `fdroiddata` build recipe

Draft `docs/f-droid/<applicationId>.yml` from `references/fdroiddata-template.yml`. The recipe's home in fdroiddata, the field table with its common mistakes, and the command that computes `AllowedAPKSigningKeys` are in the `android-store-metadata` stack page (`~/.claude/vault-stacks/vault-stack-android-store-metadata.md`).

## Step 3a: Option A — RFP issue (easiest, slowest)

Open an issue at **https://gitlab.com/fdroid/rfp/-/issues** using the "Request for Packaging" template. Fill in:

- **App name:** the value from `title.txt`
- **Package name:** the `applicationId` (e.g. `com.example.app`)
- **Source code URL**, **License (SPDX)**, **Short description**
- Link to the YAML draft you committed at `docs/f-droid/<applicationId>.yml` so the packager can copy it verbatim

A volunteer packager picks it up in days–weeks and opens the MR for you. You don't need a GitLab account beyond signup. Use this when you're not in a hurry and want F-Droid to validate your YAML before it lands.

## Step 3b: Option B — Direct merge request (fastest, more work)

1. Sign in at **https://gitlab.com**, fork **https://gitlab.com/fdroid/fdroiddata**.
2. In your fork, create a branch named after the package (e.g. `add-com.example.app`).
3. Add `metadata/<applicationId>.yml` with the contents from Step 2.
4. Optional but recommended: run `fdroid lint metadata/<applicationId>.yml` locally (requires `fdroidserver` installed; `pipx install fdroidserver`).
5. Commit, push, open MR targeting `fdroid/fdroiddata:master`.
6. Pipeline on your fork may fail with "you must verify your account to use shared runners" — that's expected; F-Droid maintainers run the build on their side regardless.

The maintainers reply on the MR with required changes (usually `Categories`, license format, or build subdirectory). Iterate until merge; first build appears in the catalog within a day of merge.

## Updating after the app is in F-Droid

`AutoUpdateMode: Version` + `UpdateCheckMode: Tags` means **a new tag in your repo automatically becomes a new F-Droid version**. The flow is:

1. Bump `versionCode` and `versionName` in `app/build.gradle.kts`.
2. Add `fastlane/metadata/android/en-US/changelogs/<new-versionCode>.txt`.
3. Tag and push (`git tag v1.1.0 && git push --tags`).
4. CI builds the signed APK and uploads to the GitHub Release (matches `Binaries:` URL pattern).
5. F-Droid's bot opens an MR against `fdroiddata` adding the new `Builds:` block. Maintainer merges, build runs, version appears.

If F-Droid's reproducible build doesn't match your APK, the cause is almost always:

- `keystore.properties` ordering changed.
- AGP / Gradle / Kotlin version drifted between local and F-Droid's `srvlib`.
- A non-deterministic build step (timestamps, random IDs in resources).

With `Binaries:` + `AllowedAPKSigningKeys`, a mismatch means F-Droid skips that version, never signing it with its own key (checked 2026-11-10, https://f-droid.org/docs/Reproducible_Builds/). Look for `Disable: ...` comments on your Builds entry.

## Hard gates

| Gate | Why |
|---|---|
| `License:` is a valid SPDX identifier | Wrong form silently fails the lint check |
| `Builds:` `commit:` is a hash or annotated tag, not a branch | F-Droid pins by commit; branches mutate |
| `AllowedAPKSigningKeys` matches the actual cert | Mismatch → F-Droid skips that version |
| `versionCode` strictly increases per release | F-Droid (and Android itself) reject downgrades |
| Repo is public and clone works without auth | F-Droid's builders are unauthenticated |
| No proprietary deps / Google Maps / Firebase / GMS | F-Droid's `AntiFeatures:` flag or rejection |
| Adaptive launcher icon present in the APK (`mipmap-anydpi-v26/ic_launcher.xml` with `<background>`+`<foreground>`+`<monochrome>` and legacy PNG fallbacks) | Without it the F-Droid client renders a generic gray square and themed icons fail on Android 13+. See the `android-icons` stack page (`~/.claude/vault-stacks/vault-stack-android-icons.md`) |

## Reference files

- `references/fdroiddata-template.yml` — drop-in YAML template with all common fields.
