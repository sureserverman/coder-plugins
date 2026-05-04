---
name: android-fdroid-publish
description: Use when preparing an Android app for publication on F-Droid — scaffolding fastlane metadata under `fastlane/metadata/android/en-US/`, drafting the `fdroiddata` build recipe YAML, choosing between the RFP issue flow and a direct merge request, computing the `AllowedAPKSigningKeys` fingerprint, or wiring `Binaries:` to GitHub releases. Trigger on "publish to F-Droid", "submit to fdroid", "create fdroid metadata", "fastlane folder for android", "RFP issue for fdroid", "fdroiddata YAML", "AllowedAPKSigningKeys", "F-Droid build recipe".
---

# Android F-Droid Publish

Get an Android app onto **F-Droid**. F-Droid does not accept your APK — it clones your **public source repo** and builds the app on its own infrastructure, then signs with its own key (or, with `AllowedAPKSigningKeys` pinned, distributes the binary you built yourself). This skill covers everything in your repo; the actual submission happens in `gitlab.com/fdroid/fdroiddata`.

## Prerequisites

- `android-release-signing` already ran (you have an upload keystore and a working `:app:assembleRelease`).
- App lives in a **public** Git repo (GitHub, GitLab, Codeberg, etc.).
- You have **at least one tagged release** with `versionCode` ≥ 1. F-Droid needs a tag (e.g. `v1.0.0`) that the metadata's `Builds:` block can point at by commit hash.

If any prerequisite is missing, hand off back to `android-release-signing` or stop and ask.

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

F-Droid pulls the store-listing copy from the **app repo itself**, from a path matching the [fastlane structure](https://f-droid.org/en/docs/All_About_Descriptions_Graphics_and_Screenshots/). Create:

```
fastlane/metadata/android/en-US/
├── title.txt                              # ≤ 50 chars
├── short_description.txt                  # ≤ 80 chars, single line, no markdown
├── full_description.txt                   # ≤ 4000 chars; plain text or simple HTML
├── changelogs/
│   └── <versionCode>.txt                  # ≤ 500 chars per version
└── images/
    ├── icon.png                           # 512×512 PNG, no transparency
    ├── featureGraphic.png                 # optional, 1024×500
    └── phoneScreenshots/                  # optional but strongly recommended
        ├── 01_main.png
        ├── 02_detail.png
        └── ...
```

Hard rules from the F-Droid docs:

- `title.txt` is **plain text only**, no markdown, no quotes around it.
- `short_description.txt` must NOT start with the app name and must NOT exceed 80 chars (F-Droid will truncate silently).
- `full_description.txt` cannot reference Google Play, in-app purchases, or "leave a 5-star review" language (F-Droid policy).
- One `<versionCode>.txt` per release — F-Droid associates a changelog by `versionCode`, not `versionName`. If you forget the changelog for a version, the app page renders blank for that release.
- Screenshots: 320–3840 px on each side, aspect ratio between 1:2 and 2:1. PNG or JPEG.

**F-Droid only re-reads metadata at the next tagged release.** If you add screenshots after `v1.0.0` is tagged, you must tag `v1.0.1` (even if the only change is metadata) for the new images to land in the catalog.

## Step 2: `fdroiddata` build recipe

The recipe lives in `gitlab.com/fdroid/fdroiddata` at `metadata/<applicationId>.yml`. Keep a copy in your own repo at `docs/f-droid/<applicationId>.yml` so the recipe is reviewed alongside the source it builds.

Use `references/fdroiddata-template.yml` as a starting point. Key fields:

| Field | What it does | Common mistakes |
|---|---|---|
| `Categories` | One or more from F-Droid's [fixed list](https://gitlab.com/fdroid/fdroiddata/-/blob/master/CATEGORIES.md) | Inventing a category — must be from the list |
| `License` | SPDX identifier (e.g. `Apache-2.0`, `GPL-3.0-or-later`) | Using `Apache 2.0` (space) — must be SPDX form |
| `SourceCode` / `IssueTracker` | URLs of the public repo and its issue tracker | Pointing to a private fork |
| `RepoType: git` + `Repo:` | Where F-Droid clones from | Pointing at a tag, not the repo root |
| `Builds:` | One block per version, each with `versionName` / `versionCode` / `commit` (hash or tag) / `subdir` / `gradle: [yes]` | Using `commit: v1.0.0` then re-tagging — F-Droid pins by hash and detects mutation |
| `Binaries:` | URL pattern with `%v` for `versionName` — F-Droid downloads from your GitHub release and verifies signature | Forgetting that `%v` is `versionName`, not `versionCode` |
| `AllowedAPKSigningKeys` | SHA-256 of your signing cert, lowercase hex no colons. Pins which key is allowed to sign uploaded binaries | Including the colons that `keytool -list -v` prints — strip them |
| `AutoUpdateMode: Version` | New entries auto-generated when you push a new tag | Forgetting `UpdateCheckMode: Tags` to actually scan tags |
| `CurrentVersion` / `CurrentVersionCode` | Latest release the catalog should point at | Letting these drift behind reality after a manual build |

Compute `AllowedAPKSigningKeys` from your upload keystore:

```bash
keytool -list -v -keystore upload.keystore -alias upload \
  | awk '/SHA256:/ {gsub(":",""); print tolower($2)}'
```

That hex string is what goes into the YAML. Once F-Droid merges it, **the cert is permanently pinned** for this `applicationId` — losing the keystore now means losing the F-Droid listing.

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

If F-Droid's reproducible-build CI fails (artifact bytes don't match yours), the cause is almost always:

- `keystore.properties` ordering changed.
- AGP / Gradle / Kotlin version drifted between local and F-Droid's `srvlib`.
- A non-deterministic build step (timestamps, random IDs in resources).

In that case F-Droid falls back to building+signing with their own key — your users still get the app, but they no longer match the binary on your GitHub release. Look for `Disable: ...` comments on your Builds entry.

## Hard gates

| Gate | Why |
|---|---|
| `License:` is a valid SPDX identifier | Wrong form silently fails the lint check |
| `Builds:` `commit:` is a hash or annotated tag, not a branch | F-Droid pins by commit; branches mutate |
| `AllowedAPKSigningKeys` matches the actual cert | Mismatch → F-Droid rejects your binary and rebuilds with their key |
| `versionCode` strictly increases per release | F-Droid (and Android itself) reject downgrades |
| Repo is public and clone works without auth | F-Droid's builders are unauthenticated |
| No proprietary deps / Google Maps / Firebase / GMS | F-Droid's `AntiFeatures:` flag or rejection |

## Common mistakes

| Mistake | Correct |
|---|---|
| Putting `Summary:` and `Description:` in fdroiddata YAML | Use `fastlane/metadata/.../short_description.txt` and `full_description.txt` |
| Tagging `1.0.0` (no `v` prefix) and writing `commit: v1.0.0` in YAML | Match the actual tag — either both `1.0.0` or both `v1.0.0` |
| Forgetting `subdir: app` when the Gradle module isn't at repo root | Build fails with "no build.gradle found" |
| `Builds:` with `gradle: yes` (string) | Must be a list: `gradle:\n  - yes` |
| Adding screenshots after the last tag and expecting them to show up | F-Droid only re-reads at the next tag — bump and re-tag |
| Including F-Droid build keys' fingerprint in `AllowedAPKSigningKeys` | Use **your** upload cert fingerprint, not theirs |

## Reference files

- `references/fdroiddata-template.yml` — drop-in YAML template with all common fields.
- `references/fastlane-layout.md` — full directory layout + per-file constraints.
