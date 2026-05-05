---
name: utils-register
description: Use to register a project with the `~/dev/infra/utils/` Debian-packaging pipeline — adding it to `pkg.list` and scaffolding the canonical `deb/package/DEBIAN/control`, `deb/package/usr/bin/`, `deb/amd64/`, `deb/arm64/` tree. Wraps the existing `~/dev/infra/utils/pkgskel` script (which idempotently creates the layout and adds the project to `pkg.list` in one go). Trigger on "register this project for utils", "add to pkg.list", "scaffold the deb tree", "set up debian packaging for the publish pipeline".
---

# utils-register

Register a project with the `~/dev/infra/utils/` Debian-packaging pipeline. The bundled `pkgskel` script already does the actual work — this skill's job is to (a) gather the right project path argument, (b) confirm with the user before invoking it, (c) verify the result, and (d) point at the next step.

## When this fires vs. when `deb-package` fires

- **`utils-register`** — first-time setup of the directory tree and `pkg.list` registration.
- **`deb-package`** — reference content for *fixing* an existing tree (control field syntax, postinst conventions, dpkg-deb errors). Don't duplicate that here.

## Steps

1. **Determine the project argument.** `pkgskel` accepts either a flat name (`usb-lock`) or a slashed sub-path (`metapacks/sure-desktop`). The argument is interpreted as a path under `~/dev/`. Default to the cwd's repo name; if the repo lives under `~/dev/metapacks/`, use `metapacks/<sub>`. If unsure, ask the user.

2. **Check whether the project is already registered.**
   - `grep -Fxq "<project>" ~/dev/infra/utils/pkg.list` — if it's already there, report and skip the `pkg.list` edit; `pkgskel` will still happily idempotently re-scaffold the layout.
   - Check whether `~/dev/<project>/deb/package/DEBIAN/control` already exists — if it does, `pkgskel` will only **amend** missing fields (it never overwrites existing values).

3. **Show the user the dry-run plan.** Print:
   - Which `pkg.list` line will be added (or "already present").
   - Which directories will be created.
   - Whether `control` will be created (with default scaffold values: `Package`, `Version: 0.1`, `Maintainer: Server Man`, `Architecture: all`, `Source`) or just amended.

4. **Wait for explicit confirmation** before running `pkgskel`. Auto mode does not waive this — `pkgskel` writes inside the project tree and can be surprising.

5. **Run `pkgskel <project>`.** Capture stdout. Report exactly what it created or amended.

6. **Post-run verification:**
   - `~/dev/<project>/deb/package/DEBIAN/control` exists and `dpkg-deb --field` parses it cleanly:
     ```bash
     dpkg-deb --field ~/dev/<project>/deb/package/DEBIAN/control 2>&1
     ```
     If `dpkg-deb` is unavailable, fall back to a `grep` for required fields.
   - `~/dev/<project>/deb/{amd64,arm64}/` are present.
   - `<project>` is now a line in `~/dev/infra/utils/pkg.list`.

7. **Hand off.**
   - Tell the user: the layout is ready, but binaries still need to be placed in `deb/amd64/` and `deb/arm64/` before `~/dev/infra/utils/publish <project>` will produce a non-empty `.deb`.
   - For deeper edits to `control`, `postinst`, or systemd integration, point at the `deb-package` skill in this same plugin.
   - Do **not** run `publish` here. That builds and uploads to a remote `reprepro` repo — out of scope for a registration skill.

## Conventions

- **Never edit `pkg.list` by hand if `pkgskel` is available.** It already syncs the list file on explicit-argument invocations (lines 85–89 of `pkgskel`). Hand editing risks dropping the trailing newline.
- **Never run `pkgskel --all` from this skill.** It scaffolds every project listed in `pkg.list`, which is far too broad for a "register this one project" intent.
- **Stay out of `mac/`.** Many projects ship both `deb/` and `mac/`. This skill only touches `deb/`.
- **Stay out of `Cargo.toml` and source files.** Registering for the deb pipeline does not require any source-tree changes.

## Common false positives

- A project whose name has a slash (e.g. `metapacks/sure-desktop`) is **not** misregistered if `pkg.list` shows it with the slash — that's the canonical form. The package name `dpkg` ends up using is the basename (`sure-desktop`).
- `control` with `Architecture: all` is the `pkgskel` default and is correct for noarch (shell/python) packages. Don't flag it as wrong unless the project actually ships per-arch binaries — in which case the user wants `Architecture: amd64` (or `arm64`) and one control file per arch.
