---
name: build-for-mac-register
description: Use to register a Rust project with the `~/dev/infra/build-for-mac/` GitHub Actions pipeline so it appears as a checkbox in the macOS-pkg build dispatch. Adds the project to `programs.txt` AND patches `.github/workflows/build_and_package.yml` (boolean input + matrix entry + `aggregate-artifacts` if-condition) in lockstep — refusing to land a half-update. Trigger on "register this for build-for-mac", "add to programs.txt", "expose this as a build-for-mac checkbox", "set up macOS pkg publishing for this project".
---

# build-for-mac-register

Register a Rust project with `~/dev/infra/build-for-mac/`. The pipeline is **declarative-but-also-imperative**: `programs.txt` is human-readable documentation, but the workflow YAML hardcodes the same names in three separate places. Forgetting any of them causes the project to silently never build.

## What "registered" means

A project is registered if and only if **all four** of the following are true in `~/dev/infra/build-for-mac/`:

| Location | Edit | Why it matters |
|---|---|---|
| `programs.txt` | Add `<project>` on its own line | Declarative list; the README points readers here |
| `.github/workflows/build_and_package.yml`, under `on.workflow_dispatch.inputs.` | Add a `<project>:` block with `description`, `required: false`, `type: boolean`, `default: false` | The Actions "Run workflow" UI exposes a checkbox |
| Same file, under `jobs.build-package.strategy.matrix.program:` | Add `- <project>` | The matrix actually iterates over it |
| Same file, under `jobs.aggregate-artifacts.if:` | OR-append `github.event.inputs['<project>'] == 'true'` (square-bracket form for names containing hyphens) | The combine-pkg step runs when *only* the new project is selected |

Three of those four edits live in the same workflow file. **All four must land or none.**

## Steps

1. **Inputs.**
   - Project name (the GitHub repo name; e.g. `pick-a-boo`, `multitor`). Default: cwd's repo name.
   - Confirm it is a Rust project (`Cargo.toml` exists in the source repo). Refuse if not — this pipeline is Rust-only.

2. **Pre-flight reads.** Read all four locations. Determine which (if any) of the four edits is already in place.

   Also confirm in the source repo that a `mac/Makefile` exists with a `pkg` target — the workflow runs `make -C "<project>/mac" pkg PKG_ID=...`, so that target must already be defined. Specifically grep for `^pkg:` in `~/dev/<project>/mac/Makefile`. If `mac/Makefile` does not exist, or `pkg:` is not a top-level target, **stop**: tell the user to scaffold the `mac/` tree first via the `mac-package` skill, then re-run this registration. Registering without `mac/` makes the matrix entry build-fail on every dispatch.

3. **Show a unified dry-run plan.** Print a single block listing every line that will be added, with the exact YAML indentation the surrounding file uses. Example:

   ```
   programs.txt: append line "<project>"

   build_and_package.yml @ on.workflow_dispatch.inputs:
     <project>:
       description: 'Build & package `<project>`?'
       required: false
       type: boolean
       default: false

   build_and_package.yml @ jobs.build-package.strategy.matrix.program:
     - <project>

   build_and_package.yml @ jobs.aggregate-artifacts.if:
     ... || github.event.inputs['<project>'] == 'true'
   ```

4. **Wait for explicit confirmation.** Auto mode does not waive this — these edits change CI behavior on a shared workflow.

5. **Apply all four edits in one go.** If any edit fails, **revert the others** before reporting. The all-or-none rule is enforced by you, not by the underlying tools.

6. **Validate.** Run `python3 -c "import yaml; yaml.safe_load(open('.github/workflows/build_and_package.yml'))"` (or `yamllint` if available) to confirm the workflow still parses. If parse fails, revert.

7. **Hand off.**
   - Tell the user: the four edits are landed and the workflow parses. The next dispatch will pick the project up.
   - The source repo's `mac/` tree was already validated in step 2; no further `mac/` work should be required for the build to succeed. If the user still wants to *change* the `mac/` layout, point at the `mac-package` skill.
   - Do **not** trigger the workflow. That's the user's call.

## Naming gotchas

- **Hyphens are allowed** in `programs.txt`, in workflow input keys, in matrix entries — `pick-a-boo` and `bin-buster` ship verbatim. Don't translate to underscores; the publish-images workflow has its own (different) convention.
- **Square-bracket form** is required when referencing hyphenated names from a workflow expression: `github.event.inputs['pick-a-boo']`, **not** `github.event.inputs.pick-a-boo` (which YAML would mis-parse as subtraction). The existing `aggregate-artifacts` `if:` shows both styles — match the surrounding pattern.
- **`metapacks/` projects don't belong here.** This pipeline is for single Rust binaries with their own GitHub repo. Slashed names will fail at the `git clone` step.

## Conventions

- **Never reorder the existing entries.** Append to the end of every list.
- **Never edit `programs.txt` without also touching the workflow.** Half-registration is the bug this skill exists to prevent.
- **Don't rewrite the workflow.** Targeted edits only. If the workflow has drifted from the convention this skill assumes, surface the drift rather than reformatting.
- **One project per invocation.** Batch registrations are fine in principle but produce harder-to-review diffs; prefer separate invocations.

## Common false positives

- `programs.txt` allows comment lines starting with `#`. Don't count a comment that *mentions* the project as a registration.
- The `aggregate-artifacts` `if:` is one long expression broken across one or more lines. A finding that the project is "missing" from this `if:` because the `grep` only checks line 1 is wrong — re-read the whole expression.
