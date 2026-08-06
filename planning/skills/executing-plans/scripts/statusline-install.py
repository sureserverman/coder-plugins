#!/usr/bin/env python3
"""statusline-install — manage the ONE `statusLine` key in the user's global
~/.claude/settings.json, pointing it at the sibling statusline-chain.sh.

Why this script exists: a Claude Code plugin's settings.json only supports
`agent` and `subagentStatusLine` as contribution points — `statusLine` is not
one of them. So exactly one line in the user's *global* settings.json is
irreducible, and this script is what writes/repairs/removes that line so the
user never has to hand-edit JSON.

CLI:
    statusline-install.py               install/repair the pointer (default)
    statusline-install.py --install     same, explicit
    statusline-install.py --status      report what is currently wired
    statusline-install.py --remove      remove the statusLine key
    statusline-install.py --force       (with --install) overwrite a
                                         statusLine this script did not install

Settings path is ~/.claude/settings.json, resolved via Path.home() (which
honors the HOME environment variable) so tests can point it at a temp dir.
"""
import argparse
import json
import re
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Self-locating target: never hard-code a checkout path. The chain script is
# always the sibling of this file, wherever the plugin happens to be installed.
TARGET_PATH = Path(__file__).resolve().parent / "statusline-chain.sh"
TARGET = str(TARGET_PATH)

# A plugin installs to a VERSION-PINNED directory
# (~/.claude/plugins/cache/<marketplace>/<plugin>/<version>/...), and that path
# changes on every version bump. `statusLine` is not a plugin contribution point,
# so `/reload-plugins` — which re-points hooks, MCP and LSP servers — cannot
# re-point it, and the old directory is cleaned up after roughly two weeks. A
# literal absolute path baked in at install time therefore expires silently,
# taking the user's *base* statusline down with it (the chain script is what
# invokes the base, so a missing chain script loses both lines, not just the bar).
#
# So when this script is running from inside a version-pinned install, the
# command written to settings.json resolves the newest installed version at
# render time instead of freezing today's. `sort -V` orders versions naturally
# (0.9.0 before 0.37.0, which a lexical sort gets wrong). The `[ -n "$p" ]` guard
# means a cache with no match prints nothing rather than a "command not found"
# line, preserving the never-noisy contract the chain script itself keeps.
VERSION_PINNED_RE = re.compile(
    r"^(?P<prefix>.*/plugins/cache/[^/]+/[^/]+)/(?P<version>[^/]+)/(?P<suffix>.*)$"
)


def resolve_command(target=TARGET):
    """The shell command to write into settings.json, plus how it was derived.

    Returns (command, mode) where mode is "versioned" or "literal". A literal
    path is correct for a dev checkout — it is stable there — and is the honest
    fallback anywhere the version-pinned layout is not recognised.
    """
    m = VERSION_PINNED_RE.match(target)
    if not m:
        return f'bash "{target}"', "literal"
    glob = f"{m.group('prefix')}/*/{m.group('suffix')}"
    return (
        f'sh -c \'p=$(ls -d {glob} 2>/dev/null | sort -V | tail -1); '
        f'[ -n "$p" ] && exec bash "$p"\'',
        "versioned",
    )


def get_settings_path():
    path = Path.home() / ".claude" / "settings.json"
    # Resolve through a symlinked settings.json. os.replace() unlinks the
    # destination symlink and swaps a regular file into its place, which would
    # silently orphan a dotfile-manager's real file (chezmoi/stow keep the
    # managed copy elsewhere and symlink it here) — the user's edits would land
    # somewhere nothing syncs. Following the link writes where they expect.
    if path.is_symlink():
        try:
            return path.resolve()
        except OSError:
            return path
    return path


def desired_entry():
    return {"type": "command", "command": resolve_command()[0]}


def is_ours(entry):
    """Whether a statusLine entry is one this installer wrote.

    Structural, never string equality against today's absolute path: the path
    changes when the plugin moves (dev checkout to marketplace, one version to
    the next), and that relocation is exactly what this tooling exists to
    survive. Shared by --status and --install so the two cannot disagree about
    the same file.
    """
    return isinstance(entry, dict) and "statusline-chain.sh" in str(
        entry.get("command", "")
    )


def detect_indent(text):
    """The original file's indent string, so a rewrite preserves its formatting.

    Re-serialising every write at a fixed `indent=2` is what made `--remove`
    fail to restore a 4-space or tab-indented settings.json byte-for-byte: the
    content round-tripped, the bytes did not. Returns None for a compact
    (single-line) file, which json.dump treats as no pretty-printing.
    """
    m = re.search(r"^([ \t]+)\"", text, re.M)
    if not m:
        return None
    indent = m.group(1)
    return indent if "\t" in indent else len(indent)


def die(msg):
    print(f"statusline-install: {msg}", file=sys.stderr)
    sys.exit(1)


def load_settings_for_write(path):
    """Load settings.json for a write operation. Never overwrites malformed
    or non-object JSON — dies with a clear message instead.

    Returns (data, existed).
    """
    if not path.exists():
        return {}, False
    try:
        raw = path.read_text()
    except OSError as e:
        die(f"cannot read {path}: {e}")
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        die(
            f"refusing to modify {path}: it contains malformed JSON ({e}). "
            "Fix or remove it by hand before retrying."
        )
    if not isinstance(data, dict):
        die(f"refusing to modify {path}: top-level JSON value is not an object.")
    return data, True


def backup(path):
    """Timestamped backup next to settings.json, taken before any write."""
    ts = datetime.now().strftime("%Y%m%dT%H%M%S%f")
    backup_path = path.with_name(path.name + f".bak.{ts}")
    try:
        backup_path.write_bytes(path.read_bytes())
    except OSError as e:
        die(f"could not create backup at {backup_path}: {e}")
    return backup_path


def write_settings(path, data, existed):
    """Atomic write: temp file in the SAME directory, then os.replace().

    An interrupted run must never leave a truncated settings.json — the
    replace is atomic on POSIX, and the temp file lives next to the target so
    the replace can't cross a filesystem boundary.
    """
    indent = 2
    prev_mode = None
    if existed:
        backup(path)
        try:
            prev_mode = path.stat().st_mode & 0o7777
            indent = detect_indent(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError):
            indent = 2
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        die(f"cannot create {path.parent}: {e}")
    # ensure_ascii=False keeps non-ASCII values (display names, non-English
    # paths) as the bytes the user wrote, instead of re-escaping "café" to
    # "café" — semantically equal, but not the verbatim survival this
    # promises. indent comes from the original file so its formatting survives.
    text = json.dumps(data, indent=indent, ensure_ascii=False) + "\n"
    tmp_path = None
    try:
        fd, tmp_name = tempfile.mkstemp(
            dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
        )
        tmp_path = Path(tmp_name)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            # Durability: the rename is atomic, but without this the data may
            # not have reached disk when the rename does, so a crash can leave
            # an empty file where valid settings used to be.
            f.flush()
            os.fsync(f.fileno())
        # mkstemp always creates at 0600, and os.replace() swaps the whole
        # inode — mode included. Without this, every write silently narrows a
        # deliberately group-readable settings.json to owner-only.
        if prev_mode is not None:
            os.chmod(tmp_path, prev_mode)
        os.replace(tmp_path, path)
    except OSError as e:
        if tmp_path is not None:
            try:
                tmp_path.unlink()
            except OSError:
                pass
        die(f"failed writing {path}: {e}")


def cmd_status():
    path = get_settings_path()
    if not path.exists():
        print(f"statusLine: not wired ({path} does not exist)")
        return 0
    try:
        raw = path.read_text()
    except OSError as e:
        print(f"statusline-install: cannot read {path}: {e}", file=sys.stderr)
        return 1
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"statusline-install: {path} is not valid JSON: {e}", file=sys.stderr)
        return 1
    if not isinstance(data, dict):
        print(f"statusline-install: {path} top-level JSON is not an object", file=sys.stderr)
        return 1
    entry = data.get("statusLine")
    if entry is None:
        print(f"statusLine: not wired in {path}")
        return 0
    if is_ours(entry):
        current = entry.get("command", "")
        print(f"statusLine: wired to this installer's chain script\n  {current}")
        if current != desired_entry()["command"]:
            print("  (differs from what a fresh install would write — "
                  "run `--install` to repair)")
        return 0
    print(f"statusLine: wired to something else: {entry!r}")
    return 0


def cmd_install(force):
    path = get_settings_path()
    data, existed = load_settings_for_write(path)
    desired = desired_entry()
    current = data.get("statusLine")

    if current == desired:
        print(f"statusLine already wired; nothing to do.\n  {desired['command']}")
        return 0

    # "Is this entry ours?" must be a STRUCTURAL question, not string equality
    # against today's absolute path. Exact-match said "third-party" whenever the
    # plugin moved — dev checkout to marketplace install, or one version to the
    # next — which is the relocation this whole change exists to survive, and it
    # turned a routine repair into a refusal demanding --force. It also
    # misclassified an entry the user had merely added a supported `padding` key
    # to. Anything invoking a script named statusline-chain.sh is ours to repair.
    ours = is_ours(current)

    if current is not None and not ours and not force:
        print(
            f"statusline-install: statusLine is already set to something else: {current!r}\n"
            "statusline-install: refusing to overwrite without --force.",
            file=sys.stderr,
        )
        return 1

    # Preserve any extra keys the user added to their entry (e.g. `padding`);
    # --force replacing a third-party entry wholesale is correct, repairing our
    # own by discarding their tuning is not.
    merged = dict(current) if ours and isinstance(current, dict) else {}
    merged.update(desired)
    data["statusLine"] = merged
    write_settings(path, data, existed)
    action = "Repaired" if current is not None else "Installed"
    print(f"{action} statusLine -> {merged['command']} in {path}")
    return 0


def cmd_remove():
    path = get_settings_path()
    if not path.exists():
        print(f"Nothing to remove: {path} does not exist.")
        return 0
    data, existed = load_settings_for_write(path)
    if "statusLine" not in data:
        print(f"statusLine not present in {path}; nothing to do.")
        return 0
    del data["statusLine"]
    write_settings(path, data, existed)
    print(f"Removed statusLine from {path}.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="Manage the statusLine key in ~/.claude/settings.json."
    )
    parser.add_argument("--install", action="store_true", help="write/repair the pointer (default)")
    parser.add_argument("--status", action="store_true", help="report what is currently wired")
    parser.add_argument("--remove", action="store_true", help="remove the statusLine key")
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite a statusLine this script did not install",
    )
    args = parser.parse_args()

    if args.status:
        return cmd_status()
    if args.remove:
        return cmd_remove()
    return cmd_install(args.force)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # a CLI tool must never hand the user a traceback
        print(f"statusline-install: unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
