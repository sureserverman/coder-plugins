---
name: project-maturity
description: Use to scaffold, audit, and read a per-project `docs/MATURITY.md` checklist tracking ship-readiness across six axes (Documentation, Security, Packaging, UI/UX, i18n, Testing). Triggers on "scaffold maturity", "audit project maturity", "is this ready to publish", "ready for publishing", "check ship-readiness", "init MATURITY.md", "what's missing before I can ship X", "publishing readiness for this repo". Three subcommands: `init` writes the template, `audit` re-runs auto-detectors, `get` returns parsed state for the portfolio orchestrator.
---

# Project Maturity

`docs/MATURITY.md` is a per-project checklist tracking publishing readiness across six axes. Each axis has sub-items; each sub-item carries one of three tick states:

- `[x] auto:<evidence-path>` — auto-detected by a deterministic rule (file exists, regex matches, count above threshold)
- `[x] claim:<YYYY-MM-DD>` — manually claimed by the user on this date (yellow in the global dashboard if >90 days old)
- `[N/A] <reason>` — not applicable to this project

**Announce at start:** "Using the project-maturity skill — `<init|audit|get>` on `<project-path>`."

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
- `[N/A] <reason>`          — does not apply to this project

Re-run `project-maturity audit` after any change to refresh auto-ticks.
The portfolio orchestrator's global-maturity.md rolls these up across
all registered projects.

---

## Documentation

- [ ] README at project root
- [ ] LICENSE file
- [ ] CHANGELOG
- [ ] CONTRIBUTING

## Security

- [ ] sec-audit clean (latest `sec-audit-report-*.md` has 0 CRITICAL + 0 HIGH)

## Packaging

Tick only the targets that apply; mark the rest `[N/A]`.

- [ ] Debian `.deb`
- [ ] macOS `.pkg` / `.dmg`
- [ ] Homebrew tap
- [ ] Flathub
- [ ] AUR
- [ ] Snap
- [ ] Chrome Web Store
- [ ] Firefox AMO
- [ ] Google Play
- [ ] F-Droid

## UI/UX

- [ ] App icon present
- [ ] Theming consistent (manual claim)
- [ ] Accessibility audit passed (manual claim, reference the audit report)

## i18n

- [ ] At least one non-default locale present

## Testing & CI

- [ ] Test suite present
- [ ] CI configured (`.github/workflows/`)
- [ ] CI green on main (manual claim)
- [ ] Coverage threshold met (manual claim, state the threshold)

---

## Notes

Free-form context that doesn't fit a checkbox (waivers, why an axis is N/A, links to publishing-target tracking issues, etc.).
```

After write, report: `Scaffolded docs/MATURITY.md for <project-name>. Run 'project-maturity audit' to populate auto-ticks.`

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
   - Icon: glob `icon.{png,svg,ico,icns}` OR `app-icon.*` at root OR `res/mipmap-*/ic_launcher*` (Android) → `[x] auto:<path>` (first match wins for evidence)
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

3. Compute the diff between existing state and detector results. For each detector:
   - If it would set a fresh `[x] auto:` tick where the line was previously `[ ]` → apply.
   - If it would change an existing `[x] auto:<old>` to a different evidence path → apply (file moved/renamed).
   - If it would clear an `[x] auto:` because the evidence disappeared → mark as `[?] stale-detector previously had: <old evidence>`. Never silently un-tick.
   - If the detector errored (malformed JSON, unreadable file) → keep existing line, append `[?] stale-detector: <error reason>` as an inline marker. Never silently fail.
   - Manually-claimed lines (`[x] claim:<date>`) are NEVER overwritten by audit. If a manual claim is >90 days old, prepend an inline `[STALE-90D]` marker so the global dashboard renders it yellow.

4. If `--write`, persist the new file (preserving every comment, blank line, and the `## Notes` section byte-for-byte). Otherwise, print a unified-diff-style preview.

5. Report a one-line summary per axis: `Documentation: 3/4 ✓ | Security: 1/1 ✓ | Packaging: 2/10 ✓ (6 N/A) | UI/UX: 1/3 | i18n: 0/1 | Testing: 2/4`.

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
   - `ticked: int` — count of `auto` + `claim` + `na` items
   - `total: int` — total sub-items in the axis
   - `axis_ship_ready: bool` — per the per-axis threshold in `../portfolio/references/maturity-axes.md` (e.g. Documentation requires README + LICENSE; Packaging requires ≥1 applicable target ticked or all `[N/A]`)
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
