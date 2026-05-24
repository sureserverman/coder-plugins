---
name: project-maturity
description: Use to scaffold, audit, and read a per-project `docs/MATURITY.md` checklist tracking ship-readiness across six axes (Documentation, Security, Packaging, UI/UX, i18n, Testing). Triggers on "scaffold maturity", "audit project maturity", "is this ready to publish", "ready for publishing", "check ship-readiness", "init MATURITY.md", "what's missing before I can ship X", "publishing readiness for this repo". Three subcommands: `init` writes the template, `audit` re-runs auto-detectors, `get` returns parsed state for the portfolio orchestrator.
---

# Project Maturity

`MATURITY.md` is a per-project checklist tracking publishing readiness across six axes. Each axis has sub-items; each sub-item carries one of three tick states:

- `[x] auto:<evidence-path>` — auto-detected by a deterministic rule (file exists, regex matches, count above threshold)
- `[x] claim:<YYYY-MM-DD>` — manually claimed by the user on this date (yellow in the global dashboard if >90 days old)
- `[N/A] <reason>` — not applicable to this project

## Where the file lives + what gets scanned (resolver)

The checklist does **not** live in the repo. It lives in the vault at `<portfolio_home>/MATURITY.md`, where `portfolio_home = <vault_dir>/Portfolio/<area>/<name>/` (resolve per `../portfolio/references/registry-format.md`). **If `vault_dir` is unset, refuse and fail loudly — never write `<repo>/docs/MATURITY.md`.**

But the **detectors scan the repo**, not the vault — README, packaging recipes, locale dirs, CI workflows all live in `<project-path>` (the repo). So:

- The checklist is read from / written to `<portfolio_home>/MATURITY.md`.
- Detector inputs are globbed from `<project-path>` (the repo working tree).
- Every auto-tick's evidence path is recorded with a `repo:` prefix (e.g. `[x] auto:repo:deb/package/DEBIAN/control`) so a reader of the vault checklist knows the evidence lives in the repo, not beside the checklist.

Every `docs/MATURITY.md` reference below means `<portfolio_home>/MATURITY.md`; every detector path is `repo:`-relative to `<project-path>`.

**Announce at start:** "Using the project-maturity skill — `<init|audit|get>` on `<portfolio_home>/MATURITY.md` (detectors scan `<project-path>`)."

The six axes, the per-axis auto-detect rules, and the ship-ready thresholds are defined in `../portfolio/references/maturity-axes.md`. Read that file before invoking `audit`.

---

## Subcommands

### `init` — scaffold `docs/MATURITY.md` from the template

Inputs: `<project-path>` (absolute, defaults to current working directory).

Refuses to overwrite an existing `docs/MATURITY.md` — caller must delete it or use a different mode.

Writes the following template, with the project name interpolated from the path's final segment:

```markdown
# Project Maturity: <project-name>

This file tracks publishing-readiness across six axes. Each sub-item
carries one of three tick states:

- `[x] auto:<evidence>`     — auto-detected by `project-maturity audit`
- `[x] claim:<YYYY-MM-DD>`  — manually asserted by the maintainer
- `[N/A] <reason>`          — does not apply to this project (rare — preferred is to omit the line entirely)

Per-project MATURITY.md is **sparse**: it only lists items that are auto-detected, manually claimed, or universally applicable basics. Packaging targets you don't ship to (and i18n if you're english-only) are omitted entirely — not listed as `[ ]` or `[N/A]`. Re-run `project-maturity audit` after any change; the audit will ADD newly-detected items as lines and re-evaluate existing ones.

The full catalog of detectable items lives in `../portfolio/references/maturity-axes.md`. The portfolio orchestrator's global-maturity.md rolls these up across all registered projects.

---

## Documentation

- [ ] README at project root
- [ ] LICENSE file

## Security

- [ ] sec-audit clean (latest `sec-audit-report-*.md` has 0 CRITICAL + 0 HIGH)

## Packaging

<!-- audit will ADD a line per detected packaging target. To mark a target as PLANNED, add the line manually with `[ ] claim:planned-<date>`. To opt out of a detected target, replace with `[N/A] <reason>`. -->

## UI/UX

- [ ] App icon present

## i18n

<!-- audit will add a line if a non-default locale is detected (Android values-*, browser ext _locales, gettext po/, Flutter .arb). Omit this whole axis with `[N/A] english-only-tool` if you don't intend to translate. -->

## Testing & CI

- [ ] Test suite present
- [ ] CI configured (`.github/workflows/`)

---

## Notes

Free-form context that doesn't fit a checkbox (waivers, planned packaging targets, links to publishing-target tracking issues, why an axis is N/A, etc.).
```

After write, report: `Scaffolded docs/MATURITY.md for <project-name>. Run 'project-maturity audit' to populate auto-ticks and add detected packaging/i18n items.`

### `audit` — re-run auto-detectors and refresh the file

Inputs: `<project-path>` (absolute), optional `--write` (off by default — dry-run shows the diff but doesn't persist).

Operation:

1. Read `docs/MATURITY.md`. If missing, abort with `No MATURITY.md found. Run 'project-maturity init' first.` (Never auto-scaffold during audit — that's the orchestrator's separate concern.)
2. For each axis, run the auto-detectors documented in `../portfolio/references/maturity-axes.md`:

   **Documentation**
   - `README` exists at project root (case-insensitive glob `README*`) → `[x] auto:README.md` (or whatever the actual filename is)
   - `LICENSE` / `LICENSE.md` / `LICENSE.txt` at root → `[x] auto:<filename>`
   - `CHANGELOG` / `CHANGELOG.md` at root → `[x] auto:<filename>` (otherwise leave unticked; manual claim or N/A acceptable)
   - `CONTRIBUTING` / `CONTRIBUTING.md` at root → `[x] auto:<filename>` (N/A allowed for solo projects)

   **Security**
   - Glob `sec-audit-report-*.md` at project root; sort lexically; take newest by filename (the YYYYMMDD-HHMM stamp makes lexical sort equivalent to chronological).
   - Parse the header line with regex `^\*\*Findings:\*\*\s*(\d+)\s+CRITICAL,\s*(\d+)\s+HIGH`. If both groups are `0`, tick `[x] auto:<filename>`. Otherwise leave unticked; the maintainer can manual-claim with a waiver if intentional.

   **Packaging** — for each sub-item:
   - Debian: `deb/package/DEBIAN/control` exists → `[x] auto:deb/package/DEBIAN/control`
   - macOS: `pkg/` directory exists OR `*.pkg` anywhere under `releases/` → `[x] auto:<path>`
   - Homebrew: any `Formula/*.rb` anywhere in the tree → `[x] auto:<path>`
   - Flathub: `*.flatpak.yaml` OR `flatpak/` directory → `[x] auto:<path>`
   - AUR: `PKGBUILD` at root → `[x] auto:PKGBUILD`
   - Snap: `snapcraft.yaml` at root → `[x] auto:snapcraft.yaml`
   - Chrome Web Store: `chrome/manifest.json` with `"manifest_version": 3` (parse JSON, check field) → `[x] auto:chrome/manifest.json`
   - Firefox AMO: `mozilla/manifest.json` OR `moz-mobile/manifest.json` → `[x] auto:<path>`
   - Google Play: requires manual claim (no reliable auto-detect of Play submission status)
   - F-Droid: `metadata/<applicationId>.yml` OR `fastlane/metadata/android/` directory → `[x] auto:<path>`

   **UI/UX**
   - Icon: glob `icon.{png,svg,ico,icns}` OR `app-icon.*` at root OR `res/mipmap-*/ic_launcher*` (Android) OR `<dir>/icons/icon*.{png,svg}` beside a `manifest.json` (browser extension; e.g. `mozilla/icons/`, `chrome/icons/`) → `[x] auto:<path>` (first match wins for evidence)
   - Theming / Accessibility: manual claim only

   **i18n**
   - Android: count entries matching `res/values-*/` (excluding the default `values/`) → if ≥1, `[x] auto:res/values-<comma-sep-list>`
   - Browser extension: count `_locales/<lang>/` (excluding `en` / `en_US`) → if ≥1, `[x] auto:_locales/<list>`
   - Gettext: count `po/*.po` files that aren't `messages.pot` → if ≥1, `[x] auto:po/<list>`
   - Flutter: count `*.arb` files with `_<lang>` suffix where `<lang>` ≠ `en` → if ≥1, `[x] auto:<paths>`
   - Otherwise: leave unticked; N/A acceptable for english-only-tool

   **Testing & CI**
   - Test suite: any of `tests/`, `test/`, `spec/`, `src/test/`, or files matching `*_test.go` / `*Test.kt` / `*_test.py` / `*.test.{js,ts,jsx,tsx}` → `[x] auto:<earliest match>`
   - CI configured: at least one `.github/workflows/*.yml` OR `.gitlab-ci.yml` OR `.circleci/config.yml` → `[x] auto:<path>`
   - CI green / Coverage: manual claim only (auto-verification would require remote API calls; out of scope for v1)

3. Compute the diff between existing state and detector results. The audit can:
   - **Tick an existing `[ ]` line** → flip to `[x] auto:<evidence>`.
   - **ADD a new line** for a detector that fired but has no matching line in the file yet (this is the primary behavior for the Packaging and i18n axes — those start empty and grow). Add the new line at the bottom of its axis section, preserving the section's existing lines.
   - **Update an existing `[x] auto:<old>`** to a different evidence path → apply (file moved/renamed).
   - **Mark `[?] stale-detector`** if a previously-`[x] auto:` line's evidence has disappeared. Never silently un-tick.
   - **Append `[?] stale-detector: <error>`** inline if the detector errored (malformed JSON, unreadable file). Never silently fail.
   - **NEVER overwrite `[x] claim:<date>` lines.** If a manual claim is >90 days old, prepend an inline `[STALE-90D]` marker so the global dashboard renders it yellow.
   - **NEVER add a line for a detector that didn't fire.** Items that don't apply stay out of the file (no `[N/A]` line written by audit). The user adds `[N/A]` manually only if they want to be explicit about an opt-out (e.g. `[N/A] english-only-tool` for the i18n axis).

4. If `--write`, persist the new file (preserving every comment, blank line, and the `## Notes` section byte-for-byte). Otherwise, print a unified-diff-style preview including the new lines that would be added.

5. Report a one-line summary per axis showing `<ticked>/<total-in-file>` (the denominator is the number of lines actually present in that axis section, not a hypothetical max): `Documentation: 2/2 ✓ | Security: 1/1 ✓ | Packaging: 1/1 ✓ | UI/UX: 1/1 ✓ | i18n: 1/1 ✓ | Testing: 2/2 ✓`.

### `get` — emit machine-readable state for the orchestrator

Inputs: `<project-path>` (absolute), optional `--format json|yaml` (default `json`).

Operation:

1. Read `docs/MATURITY.md`. If missing, return `{"error": "no-maturity-md", "path": "<project>/docs/MATURITY.md"}` and exit 0 (orchestrator handles this gracefully — see portfolio SKILL).
2. Parse each axis section into a structure. For each sub-item, record:
   - `label` — the human text after the checkbox
   - `state` — one of `auto` | `claim` | `na` | `unticked` | `stale-detector`
   - `evidence` — the path/date/reason after the state prefix, or `null`
   - `stale` — boolean; `true` if `state == "claim"` and the claim date is >90 days old

3. Compute per-axis aggregates:
   - `ticked: int` — count of `auto` + `claim` lines in the axis
   - `total: int` — number of lines actually present in the axis (excluding `[N/A]` lines)
   - `axis_ship_ready: bool` — true iff every present line is `[x]` (auto or claim) OR the entire axis is empty/N/A-only (no required minimum). The sparse model means an axis with no lines is treated as "nothing-to-do-here": ship-ready by vacuity. The per-axis specifics in `../portfolio/references/maturity-axes.md` may add extra requirements (e.g. Documentation README + LICENSE are minimums even in the sparse model).
   - `stale_count: int` — count of `[STALE-90D]` markers

4. Compute overall `ship_ready: bool` — true iff every axis's `axis_ship_ready` is true AND there are no `stale-detector` markers anywhere in the file.

Output shape (JSON):

```json
{
  "project": "<final path segment>",
  "path":    "<absolute path>",
  "audited": "<YYYY-MM-DD>",
  "axes": {
    "documentation": { "ticked": 3, "total": 4, "axis_ship_ready": true,  "stale_count": 0, "items": [...] },
    "security":      { "ticked": 1, "total": 1, "axis_ship_ready": true,  "stale_count": 0, "items": [...] },
    "packaging":     { "ticked": 2, "total": 10, "axis_ship_ready": true, "stale_count": 0, "items": [...] },
    "ui_ux":         { "ticked": 1, "total": 3, "axis_ship_ready": false, "stale_count": 0, "items": [...] },
    "i18n":          { "ticked": 0, "total": 1, "axis_ship_ready": false, "stale_count": 0, "items": [...] },
    "testing":       { "ticked": 2, "total": 4, "axis_ship_ready": false, "stale_count": 0, "items": [...] }
  },
  "ship_ready": false
}
```

YAML output uses the same shape.

---

## Hard rules

- `init` never overwrites an existing MATURITY.md.
- `audit` never overwrites a `[x] claim:` line — only `[ ]`, `[x] auto:`, and `[?] stale-detector` lines are subject to detector updates.
- `audit` never silently un-ticks. Disappeared evidence becomes `[?] stale-detector previously had: <old>`.
- Detectors are pure file-system / regex checks. No LLM in this skill. No remote calls. No package-registry queries.
- The file is human-edited. Preserve formatting (blank lines, comments, the `## Notes` free-form section) byte-for-byte when writing.

## Integration

- **portfolio** orchestrator calls `get` for every registered project during the maturity-aggregation step (see `../portfolio/SKILL.md`).
- **portfolio** orchestrator calls `init` when the user opts a project into maturity tracking for the first time.
- **Ad-hoc** — invoke directly on a single project to scaffold or refresh.
- Detector rules and per-axis definitions live in `../portfolio/references/maturity-axes.md` — that is the source of truth; this skill implements them.

## Remember

- `init` scaffolds, `audit` refreshes, `get` reports.
- Three tick states: `auto`, `claim`, `na`. `audit` only touches the first.
- Detectors fail loudly (`[?] stale-detector`), never silently.
- Manual claims expire visually after 90 days; the global dashboard yellows them.
