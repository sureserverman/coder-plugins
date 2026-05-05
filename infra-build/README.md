# infra-build

Make a project buildable by the three publishing pipelines under `~/dev/infra`. Audit readiness, scaffold what's missing, and keep registration in lockstep across the data file and the workflow YAML.

## The three pipelines

| Pipeline | Lives at | Produces | Trigger |
|---|---|---|---|
| `utils` | `~/dev/infra/utils/` | Debian `.deb` per arch, published to a `reprepro` apt repo | `./pkgskel <project>` then `./publish <project>` |
| `build-for-mac` | `~/dev/infra/build-for-mac/` | macOS `arm64` `.pkg` from a Rust source repo | GitHub Actions checkbox dispatch |
| `publish-images` | `~/dev/infra/publish-images/` | Multi-arch OCI image fanned out to DockerHub / GHCR / Quay / GitLab / ECR | GitHub Actions checkbox dispatch or `repository_dispatch` from source repo |

Each pipeline expects a specific layout in the source repo **and** an entry in two coordinated places (a list file + a workflow YAML) for the build-for-mac and publish-images pipelines. Forgetting either half silently skips the project from the build matrix — that's the gotcha this plugin exists to prevent.

## What it covers

| Skill | When it fires | What it does |
|---|---|---|
| `build-readiness-check` | "is this project ready to publish", "check build readiness" | Read-only audit. Reports which of the three pipelines the project is / isn't ready for, with the exact missing files or registration entries. |
| `deb-package` | "fix my control file", "scaffold deb/", "dpkg-deb error" | Reference for the canonical `deb/package/DEBIAN/control` + `deb/{amd64,arm64}/` layout that `infra/utils/pkgskel` expects. |
| `mac-package` | "fix my mac/ Makefile", "pkgbuild error", "launchctl bootout" | Reference for the canonical `mac/{Makefile,payload,scripts}` layout that `infra/build-for-mac` expects. |
| `bash-script-audit` | "audit my postinst", "check this installer" | Static + URL-health audit for `postinst`, `prerm`, launchd helpers, and other bash that ships inside packages. |
| `utils-register` | "register this project for utils", "add to pkg.list" | Adds the project to `infra/utils/pkg.list` and scaffolds `deb/` via the bundled `pkgskel`. |
| `build-for-mac-register` | "register this for build-for-mac", "add to programs.txt" | Adds to `programs.txt` **and** patches `.github/workflows/build_and_package.yml` (boolean input + matrix entry) in lockstep. |
| `publish-images-register` | "register this image for publish-images", "add to images.yml" | Adds to `images.yml`, patches `build-and-publish.yml` (input + `repository_dispatch` type + job), optionally scaffolds `Dockerfile` + `doc/DOCKERHUB.md`, and wires the source repo's release workflow to fire `repository_dispatch`. |

## Install

```
/plugin marketplace add sureserverman/coder-plugins
/plugin install infra-build@coder-plugins
```

## Design rules

- **Read before write.** `build-readiness-check` is the only entrypoint that runs unprompted as an audit. The register skills always show the diff before editing.
- **Dual-edit or nothing.** `build-for-mac-register` and `publish-images-register` refuse to land a half-update — either both the list file and the workflow YAML get updated or neither does.
- **Never edit other people's `mac/` or `deb/` while fixing the other.** Many projects ship both pipelines side-by-side; the skills stay strictly in their lane.
- **Never push, tag, or trigger a build.** Registration ends at "the file is on disk and YAML still parses". Triggering the build is your job.

## License

MIT.
