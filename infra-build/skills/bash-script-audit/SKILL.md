---
name: bash-script-audit
description: Use when auditing a bash/shell script before it ships inside a Debian .deb, macOS .pkg, or Docker image, checking for code errors, broken URLs, and stale version pins. Trigger on "audit this script", "check for broken download URLs", "is this installer safe", "does this .onion still resolve".
---

# Bash Script Audit

Run the bundled script first:

```bash
${CLAUDE_PLUGIN_ROOT}/skills/bash-script-audit/scripts/audit.sh <script-path>
```

It checks shebangs, `bash -n` parse, tilde in double quotes, missing `sudo` across `&&`,
`apt install` without `-y`, clearnet URL health, `.onion` URLs over Tor SOCKS
(`socks5h://127.0.0.1:9050`, torsocks fallback; INFO if Tor is down), and GitHub
`releases/latest` version currency. Exit 1 means an ERROR was found.

## Judgment the script cannot decide

Check these by hand after the script:

- `mkdir` targets match where files are later copied or moved (`mkdir ./dir` then
  `cp file ~/dir/` fails); the destination exists before the copy.
- Heredoc expansion intent: `$VARS` in an unquoted `EOF` heredoc expand, in `'EOF'`
  they stay literal. Decide which the author meant.
- Downloaded executables (AppImages, binaries) are `chmod +x`'d before use.
- `rm -rf` on a variable path (`rm -rf $1/*`, `rm -rf $DIR/`): the script reports
  nothing here, so check each one for an empty or unquoted variable.
- Version currency for non-GitHub downloads: find the latest on the project's download
  page, and list every place the old version string appears.

Report each finding as ERROR / WARN / INFO with line numbers, then offer to fix them.
