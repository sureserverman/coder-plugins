---
name: project-maturity
description: >
  Use to scaffold, audit, and read a per-project `docs/MATURITY.md` checklist tracking ship-readiness across six axes (Documentation, Security, Packaging, UI/UX, i18n, Testing). Triggers on "scaffold maturity", "audit project maturity", "is this ready to publish", "ready for publishing", "check ship-readiness", "init MATURITY.md", "what's missing before I can ship X", "publishing readiness for this repo". Three subcommands: `init` writes the template, `audit` re-runs the auto-detectors via a deterministic `scripts/audit-detectors.py` lane (no LLM in detection) and refreshes the file, `get` returns parsed state for the portfolio orchestrator.
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

<!-- audit will ADD a line per detected packaging target. To mark a target as PLANNED, add the line manually with `[ ] claim:planned-<date>`. To opt out of a detected target, replace with `[N/A] <reason>`. Android maintainers: Google Play is OPTIONAL — F-Droid, GitHub Releases (signed APK), IzzyOnDroid, Obtainium, and Accrescent are peer channels. Any one satisfies the axis. Use `[N/A] fdroid-only` / `[N/A] sideload-only` / `[N/A] not-distributing-to-play` / `[N/A] private-distribution` if you want to make the Play choice explicit. -->

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
2. Run the deterministic detector lane and consume its JSON — do **not** re-run
   the detectors by hand:

   ```
   python3 "${CLAUDE_PLUGIN_ROOT}/skills/project-maturity/scripts/audit-detectors.py" <project-path>
   ```

   The script implements every auto-detect rule defined in
   `../portfolio/references/maturity-axes.md` (file-existence, glob, JSON-field,
   and regex checks only — no LLM, no remote calls). It prints one JSON object:

   - **`is_ai_tool`** — the AI-agent-tooling fingerprint (any of
     `.claude-plugin/plugin.json` · `.claude-plugin/marketplace.json`,
     `.mcp.json` at any depth, `.cursorrules` / `.cursor/rules/*.mdc`,
     `AGENTS.md` at any depth / `.codex/config.toml` / `.codex/agents/*.md`,
     `opencode.json` / `.opencode/`, or an `agents/*.md` · `skills/**/SKILL.md` ·
     `commands/*.md` frontmatter bundle with `name:` + `description:`). When
     true, the UI/UX and i18n axes are waived — apply step 3's auto-`[N/A]
     ai-tool` rule.
   - **`detectors`** — per axis (`documentation`, `security`, `packaging`,
     `ui_ux`, `i18n`, `testing`), the list of fired items, each with an evidence
     path. Each fired item becomes an `[x] auto:repo:<evidence>` line in step 3.
   - **`notes`** — informational lines for a detector whose input exists but does
     not satisfy the tick (e.g. a `sec-audit-report-*.md` with open
     CRITICAL/HIGH). Surface these in the step-5 terminal summary; do not tick.
   - **`errors`** — malformed inputs (unparseable `chrome/manifest.json`, a
     sec-audit header that doesn't match the `**Findings:**` regex). Each maps to
     a `[?] stale-detector` annotation in step 3 on the affected item.

   Manual-claim-only items (Google Play, IzzyOnDroid, Obtainium, Accrescent;
   theming / accessibility; CI-green / coverage) are intentionally NOT emitted by
   the script — they have no local file signal. See
   `../portfolio/references/maturity-axes.md` for the full per-item rationale and
   the sanctioned Android `[N/A]` reasons (`fdroid-only`, `sideload-only`,
   `not-distributing-to-play`, `private-distribution`).

3. Compute the diff between existing state and detector results. The audit can:
   - **Tick an existing `[ ]` line** → flip to `[x] auto:<evidence>`.
   - **ADD a new line** for a detector that fired but has no matching line in the file yet (this is the primary behavior for the Packaging and i18n axes — those start empty and grow). Add the new line at the bottom of its axis section, preserving the section's existing lines.
   - **Update an existing `[x] auto:<old>`** to a different evidence path → apply (file moved/renamed).
   - **Mark `[?] stale-detector`** if a previously-`[x] auto:` line's evidence has disappeared. Never silently un-tick.
   - **Append `[?] stale-detector: <error>`** inline if the detector errored (malformed JSON, unreadable file). Never silently fail.
   - **NEVER overwrite `[x] claim:<date>` lines.** If a manual claim is >90 days old, prepend an inline `[STALE-90D]` marker so the global dashboard renders it yellow.
   - **NEVER add a line for a detector that didn't fire.** Items that don't apply stay out of the file (no `[N/A]` line written by audit). The user adds `[N/A]` manually only if they want to be explicit about an opt-out (e.g. `[N/A] english-only-tool` for the i18n axis).
   - **AI-agent tooling waiver — the one exception to the rule above.** When the step-2 `is_ai_tool` flag is true, the audit DOES write `[N/A] ai-tool` for the **UI/UX** and **i18n** axes, but only when the axis is not already satisfied by a real signal: i.e. the icon detector did not fire / no locale fired AND the maintainer has not set their own `[x]` or `[N/A]` on that axis. Concretely: convert a bare `[ ] App icon present` to `[N/A] ai-tool`; if the UI/UX or i18n axis is empty, add an `[N/A] ai-tool` line. NEVER overwrite a real `[x] auto:`/`[x] claim:` icon tick or a user's existing `[N/A] <reason>` — a maintainer who ships a GUI keeps their icon tick and the waiver does not apply. (Packaging is NOT waived: AI-agent projects tick it via the Claude-plugin / marketplace / MCP / Cursor / Codex / OpenCode detectors above.)

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
- Detectors are pure file-system / regex checks executed by `scripts/audit-detectors.py` — no LLM in the detection loop, no remote calls, no package-registry queries. The skill's own judgement is confined to the diff/merge, the AI-tool waiver, stale-detector marking, and ship-ready aggregation.
- The file is human-edited. Preserve formatting (blank lines, comments, the `## Notes` free-form section) byte-for-byte when writing.

## Integration

- **portfolio** orchestrator calls `get` for every registered project during the maturity-aggregation step (see `../portfolio/SKILL.md`).
- **portfolio** orchestrator calls `init` when the user opts a project into maturity tracking for the first time.
- **Ad-hoc** — invoke directly on a single project to scaffold or refresh.
- Detector rules and per-axis definitions live in `../portfolio/references/maturity-axes.md` — that is the source of truth; `scripts/audit-detectors.py` implements them and this skill consumes its JSON.

## Remember

- `init` scaffolds, `audit` refreshes, `get` reports.
- Three tick states: `auto`, `claim`, `na`. `audit` writes `auto` — and, only for AI-agent tooling projects (`is_ai_tool`), `[N/A] ai-tool` on the waived UI/UX + i18n axes.
- Detectors fail loudly (`[?] stale-detector`), never silently.
- Manual claims expire visually after 90 days; the global dashboard yellows them.
