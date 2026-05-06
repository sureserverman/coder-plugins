---
name: build-readiness-check
description: >
  Use to audit whether the current project is ready to be built and published
  by the three pipelines under `~/dev/infra/`: `utils` (Debian `.deb` via
  `pkgskel` + `reprepro`), `build-for-mac` (Rust → macOS `.pkg` via GitHub
  Actions), and `publish-images` (multi-arch Docker → DockerHub/GHCR/Quay/
  GitLab/ECR). Read-only. Reports per pipeline whether the project is
  READY / PARTIAL / NOT-READY with the exact missing files or registration
  entries. Trigger on "is this project ready to publish", "check build
  readiness", "what's missing for the deb build", "audit my mac/ layout",
  "is this image registered with publish-images".
---

# Build Readiness Check

Read-only audit. Never edits, scaffolds, or registers anything — that's what `utils-register`, `build-for-mac-register`, and `publish-images-register` are for. This skill answers one question for each of the three pipelines: **what specifically is missing before this project can be built and published?**

## Inputs

- **Required:** the project being audited. Default to the current working directory's project name (last path segment of the repo root, or `metapacks/<sub>` if the repo lives under `~/dev/metapacks/`).
- **Optional:** which pipelines to check. Default: all three.

## Pipeline 1 — `utils` (Debian `.deb`)

The publishing entrypoint is `~/dev/infra/utils/publish <project>`. It expects:

| Check | What it confirms |
|---|---|
| `~/dev/<project>/deb/package/DEBIAN/control` exists and has `Package:`, `Version:`, `Architecture:`, `Maintainer:`, `Description:` | `dpkg-deb` will accept it |
| `~/dev/<project>/deb/package/usr/bin/` exists | scaffold present |
| `~/dev/<project>/deb/amd64/` and `~/dev/<project>/deb/arm64/` exist | per-arch staging dirs ready |
| Project name appears in `~/dev/infra/utils/pkg.list` | `pkgskel --all` and `publish --all` will pick it up |

Report per check: **OK** / **MISSING** with the exact path. If the control file exists but is malformed (missing required fields), call out which fields.

For deeper layout questions defer to the `deb-package` skill in this plugin — don't duplicate its reference content here.

## Pipeline 2 — `build-for-mac` (Rust → macOS `.pkg`)

The publishing entrypoint is the GitHub Actions checkbox dispatch in `~/dev/infra/build-for-mac/`. It expects:

| Check | What it confirms |
|---|---|
| Source repo is a Rust project (`Cargo.toml` at root) | the workflow's `cargo build --release --target aarch64-apple-darwin` will work |
| `~/dev/<project>/mac/Makefile` exists with at minimum `build`, `package`, `clean` targets | the workflow's `make package` step will succeed |
| `~/dev/<project>/mac/payload/` exists | `pkgbuild --root` has something to package |
| `~/dev/<project>/mac/scripts/` exists if a `postinstall` is referenced from the Makefile | `pkgbuild --scripts` won't fail |
| Project name appears as a line in `~/dev/infra/build-for-mac/programs.txt` | declarative list |
| Project name appears as a `boolean` input under `on.workflow_dispatch.inputs.<name>` in `~/dev/infra/build-for-mac/.github/workflows/build_and_package.yml` | checkbox is exposed in the Actions UI |
| Project name appears in the `strategy.matrix.program` list in the same workflow | the matrix actually iterates over it |

**The two YAML edits and the `programs.txt` line MUST agree.** If `programs.txt` has the project but the workflow doesn't (or vice versa), the project silently disappears from the matrix or never becomes a checkbox. Report mismatch loudly.

For deeper `mac/` layout questions defer to the `mac-package` skill in this plugin.

## Pipeline 3 — `publish-images` (multi-arch Docker)

The publishing entrypoint is the GitHub Actions dispatch in `~/dev/infra/publish-images/`. It expects:

**In the source repo:**

| Check | What it confirms |
|---|---|
| `Dockerfile` exists at repo root | `docker buildx build` has something to build |
| `doc/DOCKERHUB.md` exists (optional, only if pushing to Docker Hub) | the `peter-evans/dockerhub-description` step will sync the long description |
| Source repo's release workflow fires `repository_dispatch` against `sureserverman/publish-images` with `event_type=build-<image>` (optional but recommended) | tag → republish is automatic |

**In `~/dev/infra/publish-images/`:**

| Check | What it confirms |
|---|---|
| Image entry under `images:` in `images.yml` with all five `targets:` filled in | declarative list and target URLs are documented |
| `on.workflow_dispatch.inputs.<image>` boolean in `.github/workflows/build-and-publish.yml` (note: `_` instead of `-` in input keys, e.g. `tor_socat`) | Actions UI checkbox |
| `on.repository_dispatch.types` includes `build-<image>` | external trigger works |
| `jobs.<image>` block with `if:` clause referencing both `inputs.<image>` and `action == 'build-<image>'`, and `uses: ./.github/workflows/reusable-build-image.yml` with `image:`, `source_repo:`, `ref:` inputs | the job actually wires up |

**The four registrations (images.yml + workflow_dispatch input + repository_dispatch type + job) MUST agree.** A missing job means the checkbox does nothing; a missing dispatch type means external triggers silently no-op.

## Output format

Print one block per pipeline:

```
═══ utils (Debian .deb) ═══
status: READY | PARTIAL | NOT-READY
missing:
  - <exact path or registration entry>
  - ...
next step: <one-liner pointing at utils-register or deb-package>
```

End with a one-line summary across all three:

```
overall: ready for [utils, build-for-mac]; missing pieces for [publish-images]
```

## Conventions

- **Read-only.** Never write, edit, or scaffold. If the user wants to fix something, hand off to the named register skill.
- **Never invent a project name.** If you can't infer it from the cwd, ask the user.
- **Don't run `pkgskel` or `dpkg-deb` to "see if it builds."** Those are side-effectful. Just check the file layout statically.
- **Don't follow the source repo's own `dispatches` to verify the source-side wiring.** That requires GitHub auth. Just report whether it's *probably* wired by grepping the source repo's `.github/workflows/*.yml` for `repository_dispatch` and `event_type=build-<image>`.

## Common false positives

- A project listed in `pkg.list` as `metapacks/sure-desktop` lives at `~/dev/metapacks/sure-desktop`, not `~/dev/sure-desktop`. Always honor the slash-separated path.
- The two workflows differ in how they spell input keys: `publish-images` uses `_` (e.g. `tor_socat`, `hardened_unbound`); `build-for-mac` uses `-` verbatim (e.g. `pick-a-boo`). Don't flag a workflow input as "missing" just because its punctuation differs from the project name in the list file — verify against the actual convention of *that* workflow.
- Some projects intentionally ship deb-only or mac-only. The user may not want all three pipelines green. Always report per-pipeline status; don't downgrade overall to "NOT-READY" just because one pipeline isn't applicable.
