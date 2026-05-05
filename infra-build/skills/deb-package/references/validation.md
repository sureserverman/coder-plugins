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

## GitHub Actions Pack Workflow Pattern

```yaml
- name: package
  run: dpkg-deb --build deb/package <name>.deb
- name: version
  run: echo "VERSION=$(grep Version deb/package/DEBIAN/control | cut -d ' ' -f 2)" >> $GITHUB_ENV
- name: sign
  run: dpkg-sig --sign builder <name>.deb
```
