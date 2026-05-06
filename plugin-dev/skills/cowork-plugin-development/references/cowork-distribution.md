# Cowork distribution reference

How to ship a plugin to Cowork users today, given that `/plugin marketplace add` does not exist in Cowork and the marketplace sync flow has bugs (anthropics/claude-code#39400). The reliable answer is **zip-upload from GitHub releases**.

## Three install paths, ranked

| Path | Audience | Reliability |
|---|---|---|
| **Zip upload via Customize UI** | Any Cowork user, any plan | ✅ Reliable today |
| **Custom GitHub-synced marketplace** | Org admins on Team / Enterprise plans only | ⚠ Marketplace skill-loading bug; recommend fallback to zip |
| **Anthropic-curated marketplace** | Any Cowork user, any plan | ✅ Reliable but you don't control the catalog |

For a plugin author who isn't Anthropic and isn't shipping through an enterprise admin, the zip-upload path is the default. Build for it.

## The zip-upload UX, what users actually do

1. User downloads a release artifact from your GitHub releases page.
2. User unzips locally (if you ship one all-in-one zip; skip this step if you ship per-plugin zips directly).
3. User opens Cowork → **Customize** in sidebar → **Browse plugins** → **upload custom plugin file**.
4. User selects the zip(s).
5. User restarts Cowork (`Cmd+Q` on macOS, close window on Windows) so skills register.
6. User invokes a skill via natural language or a slash command.

Each step is a friction point. Document the path in the README clearly enough that the user only reads it once.

## All-in-one zip vs per-plugin zips

You'll choose between two release-artifact shapes:

**Per-plugin zips** — one zip per plugin attached as a separate release asset. Five plugins = five assets per release.

- Pro: user downloads only the plugins they want.
- Con: user has to read filenames and pick. More cognitive friction.
- Con: GitHub release assets list is longer; harder to scan.

**Single all-in-one zip wrapping per-plugin zips** — one outer zip per release, containing N inner zips at the root.

- Pro: one download, simpler release page.
- Pro: users who want everything get everything in one click.
- Con: user has to unzip locally before uploading.
- Con: doesn't work for users who only want one plugin from a multi-plugin bundle (they download the whole thing anyway).

**Recommendation:** for a multi-plugin marketplace shipping ≤6 plugins per release, ship the single all-in-one zip. For larger bundles or cases where users typically install one plugin in isolation, ship per-plugin zips.

Either way, name zips with the version: `<plugin-name>-<version>.zip` for per-plugin, `<bundle-name>-<version>.zip` for all-in-one. Including the version in the filename makes it unambiguous which release the user has installed.

## GitHub Actions release workflow shape

The mechanical pattern: tag → build zip(s) → create release → attach assets. Use [`softprops/action-gh-release@v2`](https://github.com/softprops/action-gh-release) (canonical for releases as of 2026).

Trigger: tag push matching `v*` (so `v0.3.0`, `v1.0.0`, but not random branch pushes).

Permissions needed: `contents: write` on the workflow's GITHUB_TOKEN. If your org has stricter Actions permissions defaults, the user enables "Read and write permissions" under Settings → Actions → General → Workflow permissions.

Concurrency: lock per ref (`group: release-${{ github.ref }}`) to prevent double-runs if a tag is force-pushed.

Verification step: count built zips before creating the release. Fail the workflow if zero, so a misconfigured `plugins/*/` directory layout doesn't silently produce an empty release.

Release body: include the install steps **in the release body**, not just in the README. Users reaching the release page from a notification or RSS feed shouldn't have to navigate to find install instructions.

A complete copy-paste workflow lives at `examples/release-workflow.yml`.

## marketplace.json — when it matters

A `marketplace.json` at the repo root describes the marketplace structure (plugins, sources, descriptions). It's read by:

- Claude **Code's** `/plugin marketplace add owner/repo` command (so Code users can install via slash command).
- Cowork's **org-admin** custom-marketplace setup (so an admin can sync from your repo).

For personal Cowork users uploading zips, `marketplace.json` is irrelevant. They never see it.

You can ship one anyway — it costs nothing — but treat it as a Code-side / admin-side convenience, not a load-bearing piece of Cowork distribution.

If you do ship it, keep it accurate: every `source` path must resolve to an actual plugin directory; every plugin must be in the array; the version metadata should match the latest release.

## README install section

The Cowork install section in your README should look roughly like:

```markdown
## Install

1. Open the [latest release](https://github.com/<org>/<repo>/releases/latest).
2. Download `<bundle>-vX.Y.Z.zip` (or the per-plugin zip you want).
3. (If all-in-one) Unzip locally to get inner zips.
4. In Cowork: **Customize** in sidebar → **Browse plugins** → **upload custom plugin file** → select a zip.
5. Repeat for each plugin you want.
6. Restart Cowork (`Cmd+Q` and reopen) so skills register.
7. Type "show me what you do" (or `/<plugin>:tour` if you ship a tour command) to start.
```

Things to avoid in the README:

- `/plugin marketplace add ...` — doesn't work in Cowork.
- `/plugin install ...@<marketplace>` — doesn't work in Cowork.
- "git clone and copy to ~/.claude/plugins/" — this works in Code but not Cowork; Cowork's plugin storage is managed by the app.
- Links to Anthropic's curated marketplace if your plugin isn't actually there.

If you maintain a plugin that targets both Code and Cowork, make the surfaces explicit:

```markdown
## Install

**In Cowork:** [latest release](.../releases/latest) → Customize → upload zip.

**In Code:** `/plugin marketplace add <org>/<repo>` then `/plugin install <plugin>@<marketplace>`.
```

## Versioning

Standard semver. Every plugin in a multi-plugin bundle bumps version when its contents change; the bundle metadata version (in `marketplace.json`) bumps when the catalog or any plugin changes.

Tag the repo with `v<bundle-version>`. The release workflow uses the tag name verbatim as the release title and as the version suffix in zip filenames.

Breaking changes (install path changes, hard-removed skills, schema migrations in saved-state files) deserve a major bump. Cowork-only refactors that purge Code paths are breaking changes — bump major.

## CHANGELOG

Optional. The release workflow auto-generates release notes from commits since the previous tag, which is usually enough.

If you want a hand-curated changelog, ship `CHANGELOG.md` and reference the latest section in the release body. Don't ship a stale CHANGELOG — that's worse than not shipping one.
