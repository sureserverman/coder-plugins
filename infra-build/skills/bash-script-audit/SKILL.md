---
name: bash-script-audit
description: Use when auditing a bash/shell script before it ships inside a Debian `.deb` (`postinst`/`prerm`/maintainer scripts), inside a macOS `.pkg` (preinstall/postinstall), or inside a Docker image — for code errors, broken download URLs, outdated version pins, or `.onion` link availability. Trigger on "audit this script", "check for broken download URLs", "is this installer safe", "does this .onion still resolve", "are these version pins current".
---

# Bash Script Audit

Systematic review of a bash script for code errors and URL health, including .onion links via Tor.

## Instructions

When invoked, identify the target script. If the user specifies a file, use it. If unclear, ask.

**Preferred — run the bundled script first:**

```bash
skills/bash-script-audit/scripts/audit.sh <script-path>
```

It covers: shebang count + validity + malformed-shebang detection, `bash -n` parse check, tilde-in-double-quotes, possible-missing-sudo on `&&` pipelines, `apt install` without `-y`, URL extraction + `curl -sI -L` for clearnet URLs, Tor SOCKS (`socks5h://127.0.0.1:9050`) check for `.onion` URLs with torsocks fallback (skipped with INFO if Tor isn't running), and GitHub `releases/latest` redirect-scrape for version currency. Exit 1 if any ERROR was found.

**After the script, still read the sections below** — they remain the source of truth for what's checked and cover the pieces that need human judgment: section 1 (mkdir-vs-cp-destination mismatches, heredoc expansion intent, chmod +x after download), section 4 (rm -rf on variable paths, quote-spaces, Flatpak ID sanity), and any non-GitHub version-currency decisions. Use the numbered sections as both the script's spec and your manual-pass checklist. Offer to fix all issues at the end.

<details>
<summary>Manual pass (fallback — only if the script isn't available)</summary>

Run every check section below in order. For each finding, report severity: **ERROR** (will break execution), **WARN** (likely bug or outdated), or **INFO** (cosmetic/suggestion). At the end, provide a summary table and offer to fix all issues.

</details>

## 1. Structural & Syntax Errors

Read the script and check:

- [ ] No duplicate shebang lines (`#!/bin/bash` appearing more than once)
- [ ] No stray/malformed shebangs mid-script (e.g. `#!/binbash`, `#!/bin/bahs`)
- [ ] Shebang on line 1 is valid (`#!/bin/bash`, `#!/usr/bin/env bash`, etc.)
- [ ] No obvious syntax errors — run `bash -n <script>` via Bash tool to verify parse
- [ ] Consistent use of `sudo` — if a pipeline uses `sudo` on one side of `&&`, check the other side too (e.g. `sudo apt-get update && apt-get upgrade` is missing `sudo` on the right)
- [ ] Interactive commands in non-interactive context — `apt-get install` without `-y` in a script that uses `-y` everywhere else
- [ ] Tilde `~` inside double quotes won't expand — `"~/path"` should be `"$HOME/path"` or unquoted `~/path`
- [ ] `mkdir` targets match where files are later copied/moved (e.g. `mkdir ./dir` but `cp file ~/dir/` will fail)
- [ ] Files that are copied/moved to a destination should have the destination directory created first
- [ ] Downloaded executables (AppImages, binaries) should be `chmod +x`'d before use
- [ ] Heredoc variable expansion — check if `$VARIABLES` inside heredocs are intended to expand (unquoted `EOF`) or be literal (quoted `'EOF'`)

## 2. URL Extraction & Health Check

Extract every URL from the script (http://, https://, ftp://).

### Clearnet URLs

For each non-.onion URL, run via Bash tool:
```bash
curl -sI -o /dev/null -w "%{http_code}" -L "<URL>"
```
Timeout: 15 seconds. Report:
- **200**: PASS
- **301/302** (without `-L`): WARN — redirect, may need URL update
- **403/404/410**: ERROR — broken link
- **000/timeout**: WARN — unreachable (may be transient)

### .onion URLs

For each `.onion` URL, check via Tor SOCKS proxy using Bash tool:
```bash
curl -sI -o /dev/null -w "%{http_code}" -x socks5h://127.0.0.1:9050 --connect-timeout 30 "<URL>"
```
If that fails, try `torsocks`:
```bash
torsocks curl -sI -o /dev/null -w "%{http_code}" --connect-timeout 30 "<URL>"
```
.onion links are inherently less reliable; use longer timeouts (30s). Report:
- **200**: PASS
- **Non-200**: WARN — may be down or slow
- **000/timeout**: WARN — Tor circuit may have failed; note that .onion availability can be intermittent

**Important:** Verify Tor is running before testing .onion URLs:
```bash
systemctl is-active tor 2>/dev/null || pgrep -x tor >/dev/null
```
If Tor is not running, report INFO that .onion URLs could not be tested and suggest starting Tor.

## 3. Version Currency Check

For URLs that contain version numbers (e.g. `/download/4.5.8/app-4.5.8.AppImage`):

1. Identify the project (GitHub releases, official download pages)
2. For **GitHub releases**, fetch the latest tag:
   ```bash
   curl -sI -o /dev/null -w "%{url_effective}" -L "https://github.com/<owner>/<repo>/releases/latest"
   ```
   Extract version from the redirect URL.
3. For **non-GitHub downloads**, use WebFetch on the project's download page to find the latest version
4. Compare script version vs latest version
5. Report WARN for outdated versions with both old and new version numbers

When a version is outdated, note **all locations** in the script where that version string appears (URLs, filenames, directory names) so they can all be updated together.

## 4. Logic & Portability Issues

- [ ] Commands that depend on prior commands use `&&` or proper error handling, not just newlines
- [ ] `rm -rf` is not used on variable paths without safeguards (e.g. `rm -rf $DIR/` where `$DIR` could be empty → `rm -rf /`)
- [ ] Variables used in paths are quoted to handle spaces (`"$HOME/my dir"` not `$HOME/my dir`)
- [ ] `wget`/`curl` downloads check or assume current working directory — files may land in unexpected places
- [ ] Flatpak IDs match real package names (spot-check against known IDs if obvious typos exist)

## Summary Format

After all checks, output:

```
| #  | Severity | Line(s) | Issue |
|----|----------|---------|-------|
| 1  | ERROR    | 8       | Missing `sudo` before `apt-get dist-upgrade` |
| 2  | WARN     | 84      | Electrum BTC 4.5.8 is outdated (latest: 4.7.0) |
| 3  | INFO     | 1-2     | Duplicate shebang line |
| ...| ...      | ...     | ... |
```

Then list **actionable fixes** grouped by severity (ERROR first), and offer to apply all fixes.

## Delegation (Claude Code only)

> **Skip this section unless you are Claude Code.** The Agent tool with
> `subagent_type:` parameters is a Claude Code feature. Codex, Cursor, Gemini,
> OpenCode, and other hosts do not have it — run the full workflow yourself
> instead.

The `shellcheck` pass, URL liveness probes, version-pin lookups, and `.onion`
resolution are read-only scan work and dominate runtime when auditing more than
a handful of scripts. If you are on Opus, delegate them to the `readonly-scanner`
subagent (model: haiku) via the Agent tool with `subagent_type: readonly-scanner`.
Hand it:

- The list of script paths.
- The severity table so it can label findings.
- A short timeout budget per URL (5–10s) and a cap on total URLs probed.

Ask it to return a per-finding table (`severity`, `file:line`, `issue`, `evidence`).
Keep the fix offering and any actual edits in this session — the scanner cannot
write.
