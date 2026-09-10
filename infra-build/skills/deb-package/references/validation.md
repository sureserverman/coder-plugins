# Deb Package Validation Reference

Consult this file during an audit, before building, or when troubleshooting a `dpkg-deb` failure.

## Validation Checklist

- [ ] Structure is `deb/package/DEBIAN/` (not `package/DEBIAN/`)
- [ ] `control` has Package, Version, Maintainer, Architecture, Description, Source
- [ ] No trailing whitespace in `control`
- [ ] `postinst` starts with `#!/bin/bash`
- [ ] `postinst` is executable (`chmod 755`)
- [ ] Binaries in `usr/bin/` have correct permissions (755)
- [ ] systemd units in `etc/systemd/user/` (not `system/`) for user-level daemons
- [ ] `postinst` uses `systemctl --global enable` (not `systemctl enable`) for user units
- [ ] Console user detection uses `"${SUDO_USER:-$USER}"` not bare `$USER`
- [ ] `dpkg-deb --build` targets `deb/package` not `package`
- [ ] Makefile is at `rust/Makefile` (not project root)
- [ ] Makefile uses `CARGO_TARGET_DIR=target/<arch>` for separate build dirs
- [ ] Makefile moves binary to `deb/amd64/` or `deb/arm64/` (not `deb/package/usr/bin/`)
- [ ] `mac/` directory is untouched (belongs to macOS .pkg pipeline)

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| `dpkg-deb --build package` | Should be `dpkg-deb --build deb/package` |
| `systemctl enable` for user unit | Use `systemctl --global enable` |
| `$USER` in postinst | Use `"${SUDO_USER:-$USER}"` |
| System unit path for user service | Put in `etc/systemd/user/` not `etc/systemd/system/` |
| Missing executable bit on postinst | `chmod 755 DEBIAN/postinst` |
| `Architecture: all` for compiled binary | Use `amd64` or `arm64` |
| Makefile at project root | Should be at `rust/Makefile` |
| Modifying `mac/` directory during deb work | `mac/` is macOS .pkg — leave it alone |
| `dpkg-sig --sign builder` in the pack workflow | Delete the step: not in Ubuntu since 23.04, and the signature apt checks is the repo's Release, signed by `infra/utils/publish` |

## GitHub Actions Pack Workflow Pattern

```yaml
- name: package
  run: dpkg-deb --build deb/package <name>.deb
- name: version
  run: echo "VERSION=$(grep Version deb/package/DEBIAN/control | cut -d ' ' -f 2)" >> $GITHUB_ENV
```

**No per-package signing step, deliberately.** This pattern used to end with
`dpkg-sig --sign builder <name>.deb`. That line is why the adminitools and
ssh-menu pack jobs sat red from April to September 2026: Ubuntu last published
`dpkg-sig` in lunar (23.04), so on `ubuntu-latest` (noble) the install ahead of
it ends at `E: Unable to locate package dpkg-sig`, exit 100.

Do not swap in `debsigs` either, even though it is still packaged. What apt
verifies is the repository's Release signature, which `infra/utils/publish`
produces: `reprepro includedeb` into every distribution in `distr.list`, signed
with the repo key (`SignWith` in `/var/www/repository/conf/distributions`). A
signature embedded in the `.deb` itself — `_gpgbuilder` from dpkg-sig,
`_gpgorigin` from debsigs — is read by nothing here: no project in the portfolio
runs `dpkg-sig --verify` or `debsig-verify`, and the newest pack workflow
(usb-lock) attaches unsigned artefacts to a GitHub release.

If a release artefact has to be verifiable outside apt, attach a detached
`gpg --armor --detach-sign` signature beside it. An embedded one will not be
checked by anything.
