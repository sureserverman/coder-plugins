---
name: license-audit
description: Use when the user asks to audit licenses, check license compliance, find license conflicts, pick a project license, or generate a LICENSE/LICENSE.md file. Trigger on "audit licenses", "what license should this project use", "are my dependencies GPL-compatible", or "generate a LICENSE file".
---

# License Audit

Systematic license compliance audit for software projects. Discovers all dependencies, determines their licenses, analyzes compatibility based on usage type, and proposes valid license options.

## Instructions

When invoked, identify the project root. If the user specifies a directory, use it. If unclear, use the current working directory.

Run every phase below in order. For each finding, report severity: **ERROR** (license conflict or unknown license that blocks distribution), **WARN** (potential issue or ambiguity that needs attention), or **INFO** (suggestion or note). At the end, provide a summary table, propose compatible licenses, and offer to generate LICENSE.md.

## Phase 1 — Discover All Dependencies

Search the project for all dependency sources using Glob and Read tools:

- [ ] **Dockerfiles** — Glob for `**/Dockerfile*` and read each one. Extract:
  - Base images (`FROM` directives, including multi-stage builds)
  - System packages installed via `apk add`, `apt-get install`, `dnf install`, `yum install`, `pacman -S`
  - Language packages installed via `pip install`, `npm install`, `gem install`, `cargo install`, `go install`
  - Binaries downloaded via `curl`/`wget` (identify what software is being fetched)
  - `COPY --from=` references to external images
- [ ] **Package manifests** — Glob for `**/package.json`, `**/requirements.txt`, `**/Pipfile`, `**/pyproject.toml`, `**/Cargo.toml`, `**/go.mod`, `**/Gemfile`, `**/composer.json`, `**/pom.xml`, `**/build.gradle*`, `**/mix.exs`. Read and extract all dependencies
- [ ] **Build scripts** — Glob for `**/Makefile`, `**/CMakeLists.txt`, `**/configure*`, `**/build.sh`. Look for external library references or downloads
- [ ] **Vendored code** — Check for `vendor/`, `third_party/`, `lib/`, `extern/` directories that contain copied source code. Read any LICENSE or COPYING files within
- [ ] **Existing license files** — Glob for `**/LICENSE*`, `**/LICENCE*`, `**/COPYING*`, `**/NOTICE*`, `**/THIRD-PARTY*` in the project root and subdirectories

For each discovered dependency, classify its **usage type**:

| Usage Type | Description | Copyleft Impact |
|---|---|---|
| `bundled-distributed` | Included in the distributed artifact (Docker image, binary) | Full copyleft propagation |
| `statically-linked` | Compiled into the final binary | Full copyleft propagation |
| `dynamically-linked` | Shared library loaded at runtime | Weak copyleft propagation (LGPL satisfied) |
| `used-as-service` | Runs as a separate process or service in the container | No copyleft propagation (mere aggregation) |
| `build-tool-only` | Used only during build, not present in final artifact | No copyleft propagation |
| `dev-dependency` | Used only for development/testing | No copyleft propagation |

Output a dependency table:

```
| # | Dependency | Version | Source | Usage Type |
|---|------------|---------|--------|------------|
| 1 | alpine | 3.19 | Dockerfile FROM | bundled-distributed |
| 2 | tor | latest | apk add | used-as-service |
| 3 | socat | latest | apk add | used-as-service |
```

## Phase 2 — Determine License of Each Dependency

For each dependency, determine its license using these methods in order:

### 2a. Well-Known License Reference

Check [references/well-known-licenses.md](references/well-known-licenses.md) for common packages (alpine, tor, socat, nginx, openssl, bash, python, node, go, rust, redis, postgresql, the Tor pluggable transports, etc.). If the dependency is listed there, use that license and skip registry lookup.

### 2b. Registry and Package Database Lookups

If not in the reference table:

- **Alpine packages**: WebSearch for `"alpine package <name> license"` or WebFetch `https://pkgs.alpinelinux.org/package/edge/main/x86_64/<name>` and extract the License field
- **Debian/Ubuntu packages**: WebSearch for `"debian package <name> license"` or check `https://packages.debian.org/<suite>/<name>`
- **npm packages**: WebFetch `https://registry.npmjs.org/<name>/latest` and extract `license` field
- **PyPI packages**: WebFetch `https://pypi.org/pypi/<name>/json` and extract `info.license` field
- **Crates.io**: WebFetch `https://crates.io/api/v1/crates/<name>` and extract `crate.license` field
- **Go modules**: WebSearch for `"pkg.go.dev <module> license"`
- **Docker Hub images**: WebSearch for `"<image> docker license"` or check the image's source repository

### 2c. WebSearch Fallback

For any dependency whose license is still unknown, run a targeted WebSearch:
```
"<dependency-name> <version> license SPDX"
```

### 2d. Flag Unknowns

If a dependency's license cannot be determined after all lookups, flag it as:
- **ERROR** if usage type is `bundled-distributed`, `statically-linked`, or `dynamically-linked`
- **WARN** if usage type is `used-as-service`, `build-tool-only`, or `dev-dependency`

Update the dependency table with license information:

```
| # | Dependency | Version | License (SPDX) | Usage Type | Method |
|---|------------|---------|----------------|------------|--------|
| 1 | alpine | 3.19 | MIT | bundled-distributed | well-known |
| 2 | tor | latest | BSD-3-Clause | used-as-service | well-known |
| 3 | socat | latest | GPL-2.0-only | used-as-service | well-known |
```

## Phase 3 — Analyze License Compatibility

### 3a. License Classification

Classify each discovered license into one of: **public-domain**, **permissive**, **weak-copyleft**, **strong-copyleft**, **network-copyleft** (AGPL/SSPL — copyleft extends to network use), or **non-free** (BUSL, Elastic, proprietary — may prohibit redistribution). Use the SPDX identifier; if a license's category is genuinely ambiguous, flag it **WARN** and ask the user before proceeding.

### 3b. Copyleft Propagation Analysis

For each dependency with a copyleft license, determine if copyleft propagates to the project:

1. **bundled-distributed + strong copyleft** → **ERROR** if project license is less restrictive. The project must adopt a compatible copyleft license
2. **statically-linked + strong copyleft** → same as bundled-distributed
3. **dynamically-linked + strong copyleft** → **WARN** — GPL considers dynamic linking as creating a combined work; LGPL explicitly allows it
4. **used-as-service + strong copyleft** → **INFO** — separate process, mere aggregation under GPL interpretation. Docker containers running separate processes are generally considered mere aggregation, not a combined work
5. **build-tool-only + any license** → **INFO** — no propagation, but note the license for completeness
6. **dev-dependency + any license** → **INFO** — no propagation to distributed artifact

### 3c. Docker-Specific Analysis

Docker images have specific licensing considerations:

- [ ] **Mere aggregation**: Multiple independent programs in a Docker image, each running as its own process, is generally considered "mere aggregation" under GPL Section 2, not a combined work. Each program retains its own license
- [ ] **Combined work**: If a program links against GPL libraries, or if scripts tightly integrate GPL components (e.g., piping output, shared memory), it may constitute a combined work
- [ ] **Base image**: The base image license applies to the OS components. Alpine (MIT) is permissive. Debian/Ubuntu include GPL components in the base
- [ ] **Distribution**: Publishing a Docker image to Docker Hub or a registry counts as distribution under GPL/LGPL

### 3d. GPL Version Compatibility

Flag any GPL-2.0-only × GPL-3.0-only combination in a combined work as **ERROR**. `-or-later` variants resolve upward (GPL-2.0-or-later combines cleanly with GPL-3.0). Apache-2.0 is compatible with GPL-3.0+ but not GPL-2.0-only.

Report all conflicts with severity:
- **ERROR** for conflicts in bundled/linked dependencies
- **WARN** for conflicts in service-level dependencies (may not legally apply but worth noting)
- **INFO** for conflicts in build-only or dev dependencies

## Phase 4 — Propose Compatible Licenses

### 4a. Determine License Floor

Based on dependencies with copyleft propagation (only `bundled-distributed` and `statically-linked` usage types):

1. If any bundled dependency is **GPL-3.0-or-later**: floor is GPL-3.0-or-later
2. If any bundled dependency is **GPL-3.0-only**: floor is GPL-3.0-only
3. If any bundled dependency is **GPL-2.0-or-later** (and no GPL-3.0): floor is GPL-2.0-or-later
4. If any bundled dependency is **GPL-2.0-only** (and no GPL-3.0): floor is GPL-2.0-only
5. If any bundled dependency is **LGPL** (and no GPL): floor is LGPL (same version)
6. If any bundled dependency is **MPL-2.0**: floor is MPL-2.0
7. If all bundled dependencies are permissive/public domain: no floor — project can use any license
8. If any bundled dependency is **AGPL**: floor is AGPL (same version)

### 4b. List Valid License Options

Present options from most permissive to most restrictive, only including licenses at or above the floor:

```
| Option | License | Rating | Notes |
|--------|---------|--------|-------|
| A | MIT | RECOMMENDED | All deps are permissive or service-only |
| B | Apache-2.0 | ACCEPTABLE | Adds patent protection |
| C | GPL-2.0-or-later | POSSIBLE | More restrictive than needed |
| D | GPL-3.0-or-later | POSSIBLE | Most restrictive option |
```

Rating criteria:
- **RECOMMENDED**: Minimum viable license that satisfies all constraints. Prefer permissive when possible
- **ACCEPTABLE**: Valid choice with good rationale (e.g., added patent protection, project philosophy)
- **POSSIBLE**: Legally valid but more restrictive than necessary

### 4c. Current License Check

If the project already has a LICENSE file:
- [ ] Read and identify the current license
- [ ] Check if the current license is compatible with all dependencies
- [ ] Report **ERROR** if current license conflicts with a dependency
- [ ] Report **INFO** if current license is valid but a different choice might be better

## Phase 5 — Summary, User Selection & LICENSE.md Generation

### 5a. Present Full Summary

Output the complete dependency table with licenses, the compatibility analysis, and the license proposals. Format as a single summary table:

```
| # | Severity | Dependency | License | Usage Type | Finding |
|---|----------|------------|---------|------------|---------|
| 1 | INFO | alpine | MIT | bundled | Permissive — no constraints |
| 2 | INFO | tor | BSD-3-Clause | service | Separate process — mere aggregation |
| 3 | WARN | socat | GPL-2.0-only | service | Copyleft but separate process |
```

### 5b. User License Selection

Use AskUserQuestion to ask the user:

1. **Which license to apply** — present the options from Phase 4 as choices
2. **Copyright holder name** — e.g., "John Doe", "My Organization"
3. **Copyright year(s)** — default to the current year, or a range if the project has history (check git log for first commit year)

### 5c. Generate LICENSE.md

After user selection:

1. Write `LICENSE.md` (or `LICENSE` if the user prefers) at the project root containing:
   - The copyright line: `Copyright (c) <year(s)> <holder>`
   - The full canonical text of the chosen license (use the exact SPDX-standard text)
2. If the project has dependencies with attribution requirements (MIT, BSD, Apache-2.0), offer to create a `THIRD-PARTY-LICENSES` or `NOTICE` file listing each dependency, its license, and its copyright holder
3. If the project previously had a different LICENSE file, note the change and confirm before overwriting

### 5d. Offer Additional Actions

After generating the license file, offer to:
- [ ] Add an SPDX license identifier header to source files (e.g., `# SPDX-License-Identifier: MIT`)
- [ ] Create or update `THIRD-PARTY-LICENSES` / `NOTICE` file
- [ ] Add license badge to README.md
- [ ] Verify the license choice against any CI license-checking tools in the project

## Delegation (Claude Code only)

> **Skip this section unless you are Claude Code.** The Agent tool with
> `subagent_type:` parameters is a Claude Code feature. Codex, Cursor, Gemini,
> OpenCode, and other hosts do not have it — run the full workflow yourself
> instead.

The dependency enumeration (Phase 1), the registry/package-database license
lookups (Phase 2), and the SPDX-text matching across `package.json` /
`Cargo.toml` / `requirements.txt` / `go.mod` / vendored headers is bulk read
work. If you are on Opus or the dependency graph is large, delegate it to the
`readonly-scanner` subagent (model: haiku) via the Agent tool with
`subagent_type: readonly-scanner`. Ask it to return:

- One row per dependency: `name`, `version`, `source_file`, `declared_license`,
  `resolved_license` (if it found a `LICENSE` file in the installed package),
  and the lookup method it used.
- A separate list of dependencies with missing or ambiguous license info.

Keep the policy decisions (compatibility matrix in Phase 3, license-floor in
Phase 4, generating the LICENSE file in Phase 5) in this session. The scanner
reports; you judge.
