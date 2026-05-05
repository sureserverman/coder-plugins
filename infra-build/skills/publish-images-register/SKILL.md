---
name: publish-images-register
description: Use to register a Docker image with the `~/dev/infra/publish-images/` multi-arch multi-registry pipeline. Adds the image to `images.yml` AND patches `.github/workflows/build-and-publish.yml` (boolean input + `repository_dispatch` type + job block) in lockstep — refusing to land a half-update. Optionally scaffolds `Dockerfile` + `doc/DOCKERHUB.md` in the source repo, and wires the source repo's release workflow to fire `repository_dispatch` so tag → republish is automatic. Trigger on "register this image for publish-images", "add to images.yml", "publish this image to all registries", "wire up multi-arch docker publishing".
---

# publish-images-register

Register a Docker image with `~/dev/infra/publish-images/`. The pipeline fans one source repo's `Dockerfile` out to four architectures and up to five registries (DockerHub, GHCR, Quay, GitLab, ECR) — but only if the image is registered in **four coordinated places**, three of which sit inside the same workflow YAML.

## What "registered" means

A new image `<image>` (e.g. `tor-socat`) is registered if and only if **all four** of the following are true in `~/dev/infra/publish-images/`:

| Location | Edit | Why it matters |
|---|---|---|
| `images.yml`, under `images:` | Append a block with `name: <image>`, `source_repo: sureserverman/<image>`, and `targets:` filled in for `dockerhub`, `ghcr`, `quay`, `gitlab`, `ecr` | Declarative documentation of where this image ships to |
| `.github/workflows/build-and-publish.yml`, under `on.workflow_dispatch.inputs.` | Add `<image_with_underscores>:` block (`description`, `required: false`, `type: boolean`, `default: false`) | Actions UI checkbox |
| Same file, under `on.repository_dispatch.types:` | Append `- build-<image>` (with hyphens) | External `repository_dispatch` triggers from the source repo work |
| Same file, under `jobs:` | Append a `<image>:` job block whose `if:` references **both** the workflow_dispatch input **and** the `build-<image>` action; `uses: ./.github/workflows/reusable-build-image.yml`; passes `image:`, `source_repo:`, `ref:` | The job actually runs |

All four edits are mandatory. The source repo must also have a `Dockerfile` at its root — without it `docker buildx build` has nothing to build, so the workflow will fail on every dispatch. The `<image>:` job block is a copy-paste of the existing patterns; copy from `tor-socat` / `tor-haproxy` / `hardened-unbound` verbatim and substitute the name forms below.

Optionally (do not block registration on these):

- Source repo's `doc/DOCKERHUB.md` (long description synced to Docker Hub).
- Source repo's release workflow fires `repository_dispatch event_type=build-<image>` against `sureserverman/publish-images` on tag push, so that tag → republish is automatic.

## Naming convention (gotcha)

Three different name forms appear, and you must use the right one in each location:

| Form | Example | Used in |
|---|---|---|
| Hyphen, the canonical image name | `tor-socat`, `hardened-unbound` | `images.yml` `name:`, registry image names, source repo name, `repository_dispatch` types as `build-<image>`, the `<image>:` job key, `jobs.<image>.with.image:` |
| Underscore | `tor_socat`, `hardened_unbound` | `on.workflow_dispatch.inputs.<key>:` (and the `if:` reference `github.event.inputs.<key>`) |
| `build-` prefix | `build-tor-socat`, `build-hardened-unbound` | `on.repository_dispatch.types:`, the `if:` check `github.event.action == 'build-<image>'`, the source repo's release workflow `event_type:` |

Get any of these wrong and the project silently no-ops (checkbox does nothing, dispatch fires into the void, or YAML parse fails).

## Steps

1. **Inputs.**
   - Image name in canonical hyphen form.
   - Source repo (default `sureserverman/<image>`).
   - Whether to also scaffold `Dockerfile` / `doc/DOCKERHUB.md` in the source repo (default: only if missing, and only after asking).
   - Whether to wire `repository_dispatch` from the source repo's release workflow (default: ask).

2. **Pre-flight reads.** Read all four locations in `publish-images/`. For each, determine: already-present / missing.

3. **Pre-flight source-repo reads.** Confirm `Dockerfile` exists at the source repo root. If it does not, **stop** and tell the user the source repo needs a `Dockerfile` before registration is meaningful. Do not scaffold a Dockerfile from this skill — Dockerfile design is project-specific (base image choice, multi-stage builds, USER directive, healthcheck) and should not be auto-generated. The user should author it, or invoke a Docker-specific skill, then re-run this registration.

4. **Show a unified dry-run plan.** One block listing every line that will be added — to `images.yml`, to each section of the workflow, and (if applicable) to the source repo. Use the exact indentation of the surrounding file.

5. **Wait for explicit confirmation.** Mandatory. Do not skip in auto mode — these edits change CI behavior on a shared workflow that pushes to public registries.

6. **Apply all edits atomically.**
   - Update `images.yml`.
   - Update workflow YAML (three sections in one Edit pass).
   - Optionally update the source repo's `Dockerfile`, `doc/DOCKERHUB.md`, and release workflow.
   - If any edit fails, revert the others.

7. **Validate.**
   - `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build-and-publish.yml'))"` — workflow still parses.
   - `python3 -c "import yaml; yaml.safe_load(open('images.yml'))"` — `images.yml` still parses.
   - Cross-check that the new entries' three name forms are mutually consistent (no `tor_socat` input paired with `build-tor_socat` dispatch, etc.).

8. **Hand off.**
   - Print: required secrets per registry that's enabled. Cite `~/dev/infra/publish-images/README.md` ("Repository secrets" table) for the canonical list. The user is responsible for setting them in GitHub repo settings.
   - Print: required one-time registry-side setup — Quay repo creation, `aws ecr-public create-repository --repository-name <image> --region us-east-1`, Docker Hub repo creation at `sureserver/<image>`. Same README, "Registry-side one-time setup" section.
   - Tell the user: tagging a release in the source repo will only auto-republish if the *optional* `repository_dispatch` wiring landed in step 6. Workflow_dispatch (manual checkbox) always works.
   - Do **not** trigger the workflow.

## Conventions

- **Never edit `images.yml` without also touching the workflow YAML.** Half-registration is the bug this skill exists to prevent. The header comment in `images.yml` itself enumerates the three workflow edits — match it exactly.
- **Don't enable a registry the user hasn't configured.** Variables like `ENABLE_QUAY` and per-registry secrets are the user's call. This skill registers the image; it does not flip enable variables.
- **Don't push to a registry by hand to "test" it.** The pipeline does that. This skill stops at "the file is on disk and YAML parses".
- **Never modify `reusable-build-image.yml`.** That's the per-image build template; new images plug into it via `uses:`, not by editing it.

## Common false positives

- `images.yml` is documentation only (its own header comment says so). A diff that touches only `images.yml` and not the workflow looks "wrong" to a reviewer but is also not actually broken from the pipeline's perspective — the workflow is the source of truth. This skill still requires both because the documentation drifts otherwise.
- The `if:` clause spans multiple lines and uses YAML block scalar (`|`). A single-line `grep` for `inputs.<image>` may miss the dispatch half. Read the full block.
- A source repo with `Dockerfile.alpine`, `Dockerfile.debian`, etc. is common. The workflow uses `docker buildx build` with the default `Dockerfile` only — flag multiple Dockerfiles as a question for the user, not a block.
