# Maturity Axes Reference

This document is the authoritative definition for the six maturity axes used by
the `project-maturity` skill. It specifies exactly how each axis is
auto-detected, when a manual claim is appropriate, when N/A is valid, and what
the minimum state is for a project to count that axis as green in the
`ship_ready` column of `~/.claude/global-maturity.md`. The `project-maturity
audit` subcommand runs every rule in this file deterministically — no LLM
judgement in the loop.

## Tick-state syntax

Every sub-item in a `docs/MATURITY.md` checklist uses exactly one of three
syntaxes. No other forms are valid.

**Auto-detected (deterministic):**

```
[x] auto:<evidence-path>
```

The tool found the required file or pattern. `<evidence-path>` is the
relative path from the project root (or a comma-separated list of paths) that
satisfied the rule. Written by `project-maturity audit`; never written by
hand. Because the evidence is embedded, reviewers can verify the tick without
re-running the tool.

**Manual claim:**

```
[x] claim:<YYYY-MM-DD>
```

The user has verified a condition that cannot be auto-detected. The date is
when the claim was made. Claims older than 90 days are rendered in yellow in
`~/.claude/global-maturity.md` to signal staleness and prompt a re-check.
The user is responsible for updating the date when they re-verify.

**Not applicable:**

```
[N/A] <reason>
```

This axis or sub-item does not apply to this project. A reason string is
mandatory — a bare `[N/A]` is treated as a parse error by `project-maturity
audit`. The reason should be terse but unambiguous, e.g.
`no-attack-surface`, `english-only-tool`, `not-distributed`.

## ship_ready aggregation

A project is ship-ready (`ship_ready: true` in the registry and a green row in
the global dashboard) if and only if every one of the six axes meets its own
ship-ready threshold as defined in the `### Ship-ready threshold` subsection
below.

No axis may be absent from `docs/MATURITY.md` and no axis may be in the
`[?] stale-detector` state (see "Auto-detector failure handling" at the bottom
of this document). A missing or errored axis blocks ship-ready regardless of
the other five.

An axis whose threshold says "or N/A" counts as green when it is marked
`[N/A] <reason>` with a non-empty reason.

---

## Documentation

### Definition

Tracks the presence of the standard root-level documentation files that
downstream users and contributors expect to find. These files are
project-agnostic and apply to virtually every codebase, including libraries,
CLI tools, desktop apps, and browser extensions.

### Auto-detect rules

All path checks are relative to the project root. Glob expansions are
case-sensitive on Linux.

- `README.md` exists at project root → auto-tick "README" with
  `auto:README.md`
- `CHANGELOG.md` exists at project root → auto-tick "CHANGELOG" with
  `auto:CHANGELOG.md`
- Any of `LICENSE`, `LICENSE.md`, or `LICENSE.txt` exists at project root →
  auto-tick "LICENSE" with `auto:<whichever file matched>`
- `CONTRIBUTING.md` exists at project root → auto-tick "CONTRIBUTING" with
  `auto:CONTRIBUTING.md`

### Manual claim conditions

None of the documentation sub-items require a manual claim under normal
circumstances — they are fully auto-detectable. A manual claim is only
appropriate if the file lives at a non-standard path (e.g. inside `docs/`) and
the project maintainer intentionally keeps it there. In that case, use
`[x] claim:<date>` and add a comment noting the actual path.

### N/A guidance

- **CONTRIBUTING**: reasonable to mark `[N/A] solo-project` or
  `[N/A] not-accepting-prs` for personal tools, archived projects, or
  projects where external contribution is explicitly out of scope.
- **CHANGELOG**: may be marked `[N/A] pre-release` for projects that have
  never shipped a tagged release, but remove the N/A once the first release
  lands.
- **README** and **LICENSE**: N/A is almost never appropriate. Every
  distributed project needs both. Flag it rather than marking N/A.

### Ship-ready threshold

README and LICENSE must both be auto-ticked (or, in the manual-path edge case,
manually claimed). CHANGELOG and CONTRIBUTING may be auto-ticked, manually
claimed, or marked N/A. If either is simply absent (no tick of any kind), the
axis is not green.

---

## Security

### Definition

Tracks whether the project has undergone a security audit and whether any
findings that represent active risk (CRITICAL or HIGH severity) remain open.
The audit report is a structured markdown file produced by the `sec-review`
skill. The auto-detector reads the report header to extract finding counts.

### Auto-detect rules

1. Glob for `sec-audit-report-*.md` at the project root. If no files match,
   there is no auto-tick.
2. Sort matches lexically (filenames follow the pattern
   `sec-audit-report-YYYYMMDD-HHMM.md`, so lexical order equals
   chronological order). Take the last entry — that is the newest report.
3. Parse the header line of that file using the regex:

   ```
   ^\*\*Findings:\*\* (\d+) CRITICAL, (\d+) HIGH, (\d+) MEDIUM, (\d+) LOW
   ```

4. If both captured groups 1 (CRITICAL) and 2 (HIGH) are `0` → auto-tick
   "sec-audit clean" with `auto:<relative-path-to-report>`.
5. If the file exists but CRITICAL > 0 or HIGH > 0 → no auto-tick. The
   finding counts are recorded as an annotation so the user sees the block
   reason without opening the file.

### Manual claim conditions

A manual claim (`[x] claim:<date>`) is appropriate when:

- The sec-audit report exists but has open HIGH/CRITICAL findings that the
  user has reviewed and accepted as out-of-scope with documented rationale.
- The audit was performed by an external tool that does not produce a
  `sec-audit-report-*.md` file; the user has reviewed the external output.

In either case the user must be able to point to a specific artifact. A manual
claim with no linked evidence is considered aspirational and will be challenged
at the next review.

### N/A guidance

Mark `[N/A] no-attack-surface` only for projects that genuinely have no
externally reachable I/O: pure data-transformation CLI utilities that read
from stdin and write to stdout, with no network access, no file-system writes
outside a controlled temp dir, and no privilege escalation. This is rare. When
in doubt, run the audit.

### Ship-ready threshold

The "sec-audit clean" sub-item must be auto-ticked, OR the axis must be marked
`[N/A] no-attack-surface`. A manual claim on the overall axis is accepted only
when backed by an artifact reference as described above. An absent audit file
with no N/A blocks ship-ready.

---

## Packaging

### Definition

Tracks whether the project is packaged for each distribution channel that
applies to its type. This axis has a per-target sub-checklist; only the
targets relevant to the project are checked — the rest are marked N/A. The
goal is to confirm that users on each supported platform have a working install
path, not to force packaging for every possible channel.

### Auto-detect rules

Each target below is independent. Check only those that apply; mark the rest
`[N/A] <reason>`.

| Target | Detection rule | Auto-tick evidence |
|---|---|---|
| Debian (.deb) | `deb/package/DEBIAN/control` exists | `auto:deb/package/DEBIAN/control` |
| macOS pkg/dmg | `pkg/` directory exists OR a `*.pkg` artifact is present in `releases/` | `auto:pkg/` or `auto:releases/<file>.pkg` |
| Homebrew tap | Any `Formula/*.rb` file anywhere under the project tree | `auto:Formula/<file>.rb` |
| Flathub | `*.flatpak.yaml` at root OR a `flatpak/` directory exists | `auto:<file>.flatpak.yaml` or `auto:flatpak/` |
| AUR | `PKGBUILD` exists at project root | `auto:PKGBUILD` |
| Snap | `snapcraft.yaml` exists at project root | `auto:snapcraft.yaml` |
| Chrome extension | `chrome/manifest.json` exists AND contains `"manifest_version": 3` | `auto:chrome/manifest.json` |
| Firefox/AMO extension | `mozilla/manifest.json` OR `moz-mobile/manifest.json` exists | `auto:mozilla/manifest.json` or `auto:moz-mobile/manifest.json` |
| F-Droid | `metadata/<applicationId>.yml` in an fdroiddata fork directory OR a `fastlane/metadata/android/` directory exists | `auto:metadata/<id>.yml` or `auto:fastlane/metadata/android/` |
| Google Play (Android) | Cannot be auto-detected. Play submission cannot be verified from local files alone. | Manual claim required — see below. |

For the Chrome extension check, the detector reads `chrome/manifest.json` and
asserts the JSON field `manifest_version` equals `3`. If the file is malformed
JSON, this triggers a stale-detector error (see "Auto-detector failure
handling").

### Manual claim conditions

- **Google Play**: claim `[x] claim:<date>` once the app has been accepted
  and is live on the Play Store. The user should note the Play Store URL or
  package name in a comment. Detection would require a Play Developer API
  call, which is out of scope for v1.
- **Any other target**: use a manual claim if the packaging artifact lives at
  a non-standard path not covered by the rule above. Note the actual path.

### N/A guidance

- Mark individual targets `[N/A] not-applicable` for any channel the project
  does not target (e.g. `[N/A] not-applicable` on AUR for a project that only
  targets Android).
- Mark the entire axis `[N/A] not-distributed` only if the project is an
  internal library or tool that is never published to any external channel.
  This is unusual — even CLI utilities typically have at least one packaging
  target.

### Ship-ready threshold

At least one applicable packaging target must be auto-ticked. If every target
is marked N/A except Google Play, then the Google Play manual claim must be
present. If the entire axis is marked `[N/A] not-distributed`, that counts as
green. An axis with no ticks and no N/A blocks ship-ready.

---

## UI/UX

### Definition

Tracks the baseline visual and accessibility quality of projects that have a
user-facing interface. For headless CLI tools and pure libraries this axis is
largely N/A, but the icon sub-item still applies to anything that appears in
an application launcher, app store, or browser extension store.

### Auto-detect rules

- **Icon present**: any of the following exists →
  auto-tick "icon" with evidence = the matched path:
  - `icon.png` at project root
  - `icon.svg` at project root
  - `app-icon.*` (any extension) at project root
  - For Android projects: any `res/mipmap-*/ic_launcher*` file under the
    project tree (glob; use the first match as evidence, note count if > 1)

All other UI/UX sub-items (theming, accessibility audit) cannot be reliably
auto-detected across platforms and require manual claims.

### Manual claim conditions

- **Theming**: claim when a consistent color palette, typography, and spacing
  system has been applied across all screens or surfaces. The user should
  reference a design token file, a Figma link, or a style guide document.
- **Accessibility audit**: claim when an audit has been completed using a
  platform-appropriate tool or methodology:
  - Web / browser extension: WCAG 2.1 AA audit (tool + manual check)
  - Android: TalkBack navigation pass on a physical or emulated device
  - Linux desktop: Orca screen reader pass
  - macOS/iOS: VoiceOver pass
  The claim should reference the audit date and tool used in a comment.

### N/A guidance

- Mark theming and accessibility `[N/A] headless-cli` or
  `[N/A] library-no-ui` for projects with no visual interface.
- Mark the icon sub-item `[N/A] no-launcher-presence` only if the project
  genuinely never appears in any app launcher, extension store listing, or
  home screen (e.g. a pure server-side daemon with no desktop presence). This
  is uncommon — extension stores and app stores all require icons.
- N/A on the full axis is appropriate only for projects that have zero user
  interface of any kind.

### Ship-ready threshold

The icon sub-item must be auto-ticked (or `[N/A] no-launcher-presence` with
documented rationale). Theming and accessibility must each be manually claimed
or marked N/A — they may not be left with no tick of any kind. A bare unchecked
`[ ]` on any sub-item blocks ship-ready.

---

## i18n

### Definition

Tracks whether the project externalizes its user-visible strings and ships at
least one locale beyond the default (typically English). A project that
targets only English-speaking users is a legitimate N/A; everything else
should demonstrate active i18n support before shipping.

### Auto-detect rules

The detector checks all applicable patterns below. If more than one applies,
each is ticked independently with its own evidence.

- **Android**: `res/values-*/` directories exist in the project tree (other
  than the bare `res/values/` default) → auto-tick with evidence =
  comma-separated list of the matched directory paths, e.g.
  `auto:app/src/main/res/values-de,app/src/main/res/values-fr`
- **Browser extensions**: `_locales/<lang>/` directories exist (other than
  `_locales/en/` or the extension's declared `default_locale`) → auto-tick
  with evidence = comma-separated list of matched locale directories
- **Gettext**: `po/*.po` files exist, at least one of which is not
  `messages.pot` → auto-tick with evidence = `auto:po/` and the count of
  `.po` files
- **Flutter**: `*.arb` files exist with a `_<lang>` suffix that is not `_en`
  (e.g. `app_de.arb`, `app_ja.arb`) → auto-tick with evidence =
  comma-separated list of matched `.arb` file paths

In all cases, the detection confirms structure only — it does not validate
translation completeness or string coverage.

### Manual claim conditions

A manual claim is appropriate when:

- The i18n mechanism uses a framework not covered above (e.g. Rails i18n
  YAML, iOS `.strings` / `.xcstrings`, GNU gettext in a non-standard
  directory layout). The user should note the framework and evidence path.
- Translation exists but is loaded dynamically from a remote source (e.g. a
  translation management platform) and no locale files live in the repo.

### N/A guidance

- Mark `[N/A] english-only-tool` for CLI tools, system daemons, or developer
  utilities whose output is log lines and structured data — places where
  i18n has no meaningful effect on usability.
- Mark `[N/A] english-only-by-design` for projects where the maintainer has
  made a deliberate, documented decision not to support additional locales.
- Do not mark N/A simply because no translations have been done yet — that is
  an open task, not an N/A.

### Ship-ready threshold

At least one non-default locale must be auto-ticked using any of the patterns
above, OR the axis must be marked `[N/A] english-only-tool` or
`[N/A] english-only-by-design`. A project with internationalized UI that has
not yet shipped any locale files does not meet the threshold.

---

## Testing

### Definition

Tracks the presence and health of automated tests and continuous integration.
A project without a test suite and CI is not ship-ready — even a small suite
that runs on every push is sufficient. CI green on main and coverage thresholds
are monitored via manual claims because auto-detecting those states would
require live API calls, which are out of scope for v1.

### Auto-detect rules

- **Test suite present**: any of the following exists →
  auto-tick "tests present" with evidence = the matched path(s):
  - `tests/` directory at project root
  - `test/` directory at project root
  - `spec/` directory at project root
  - Any `*_test.go` file anywhere in the project tree
  - Any `*Test.kt` or `*Test.java` file anywhere under `src/`
  - `src/test/` directory (Maven/Gradle conventional test source root)
  - Rust: `Cargo.toml` exists AND (`tests/` directory exists OR `Cargo.toml`
    contains a `[[test]]` section)

  If multiple patterns match, list all matched paths in the evidence string,
  comma-separated. The presence of any one is sufficient for the sub-item to
  tick.

- **CI configured**: `.github/workflows/*.yml` — at least one `.yml` file
  exists under `.github/workflows/` → auto-tick "CI configured" with
  evidence = comma-separated list of matched workflow file paths.

### Manual claim conditions

- **CI green on main**: claim `[x] claim:<date>` when CI is currently passing
  on the default branch. Auto-detection would require a GitHub Actions API
  call; this is explicitly deferred to a future version of the skill. The user
  should note the last verified date and, optionally, the badge URL in a
  comment.
- **Coverage threshold**: claim when the project's coverage report meets the
  agreed threshold (e.g. 70% line coverage). Note the measured percentage and
  the tool used (e.g. `pytest-cov 84%`, `JaCoCo 76%`) in a comment alongside
  the claim date.

### N/A guidance

- Mark "CI configured" `[N/A] no-remote-repo` only if the project has no
  remote repository where CI can run (e.g. a purely local experiment that has
  never been pushed anywhere). Once the project is pushed, CI should be
  configured.
- Mark "CI green on main" `[N/A] no-ci` only when CI configured is also N/A.
  If CI is configured, its status must be claimed — it cannot be skipped.
- Mark "coverage threshold" `[N/A] no-threshold-set` if the project
  deliberately does not enforce a coverage floor (acceptable for scripts and
  glue code; document the rationale).
- The "tests present" sub-item has no valid N/A for ship-ready projects. Every
  project that ships to users should have at least a minimal smoke test.

### Ship-ready threshold

"Tests present" and "CI configured" must both be auto-ticked. "CI green on
main" and "coverage threshold" must each be manually claimed or marked N/A —
they may not be left as bare unchecked items. A project without a test suite
or without CI configured does not meet the threshold, regardless of the state
of the other four axes.

---

## Auto-detector failure handling

If any auto-detector encounters an error during `project-maturity audit` — for
example, a `sec-audit-report-*.md` file that matches the glob but whose header
line does not match the expected regex, a `chrome/manifest.json` that is not
valid JSON, or a filesystem permission error reading a matched file — the
following behavior applies:

1. The axis sub-item retains whatever value it held before the audit run. No
   tick is added or removed.
2. The sub-item is annotated with `[?] stale-detector` and an inline note
   describing the error, e.g.:

   ```
   [?] stale-detector — sec-audit-report-20260501-1430.md: header line not found
   ```

3. The error is surfaced in the terminal output of `project-maturity audit` so
   the user is aware. There are no silent failures.
4. A `[?] stale-detector` state blocks `ship_ready: true` for the whole
   project, because the axis state is unknown.
5. The user must resolve the underlying issue (fix the malformed file, or
   update the detection rule if the format has legitimately changed) and
   re-run `project-maturity audit` to clear the flag.

The `[?] stale-detector` marker is never written by hand — it is exclusively
an output of the audit tool. If a user sees it in a `MATURITY.md` and the
audit has not been run recently, that is itself a signal to re-run the audit.
