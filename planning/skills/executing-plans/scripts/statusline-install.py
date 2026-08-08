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
import shlex
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
# render time instead of freezing today's. Versions are ordered by a numeric
# field sort (0.9.0 before 0.37.0, which a lexical sort gets backwards). The
# `[ -n "$p" ]` guard
# means a cache with no match prints nothing rather than a "command not found"
# line, preserving the never-noisy contract the chain script itself keeps.
VERSION_PINNED_RE = re.compile(
    r"^(?P<prefix>.*/plugins/cache/[^/]+/[^/]+)/(?P<version>[^/]+)/(?P<suffix>.*)$"
)


BASH_INVOCATION_RE = re.compile(r'^bash\s+"?([^"]+)"?\s*$')

# The `PLAN_STATUSLINE_BASE=<path> ` prefix chain_through() writes, so a later
# repair can recognise and carry it rather than silently dropping it. Parsed
# with shlex so a quoted path containing spaces round-trips.
BASE_PREFIX_RE = re.compile(r"^PLAN_STATUSLINE_BASE=(?P<base>('[^']*'|\"[^\"]*\"|\S+))\s+")

# The chain script's own name, matched as a PATH COMPONENT rather than as a
# substring anywhere in the command (see is_ours).
CHAIN_NAME = "statusline-chain.sh"
CHAIN_PATH_RE = re.compile(r"[^\s\"';|&]*" + re.escape(CHAIN_NAME))


def split_base_prefix(command):
    """(base_path_or_None, remainder) for a command chain_through() may have written.

    A repair install must carry a preserved base forward instead of rebuilding
    the command from scratch: cmd_install() used to `merged.update(desired)`,
    which overwrote `command` with the unprefixed form, so a --force install
    that carefully preserved the user's statusline was undone by the very next
    plain --install. And --status compared against the unprefixed command, so a
    preserved entry always reported "differs — run `--install` to repair",
    steering the user into exactly the call that destroyed it.
    """
    m = BASE_PREFIX_RE.match(str(command or ""))
    if not m:
        return None, str(command or "")
    base = m.group("base")
    if base[:1] in ("'", '"') and base[-1:] == base[:1]:
        base = base[1:-1]
    return base, str(command)[m.end():]


def base_emits_own_bar(base_path):
    """Whether a candidate base statusline already renders a plan-progress bar.

    The hand-written ~/.claude/statusline-with-plan.sh this plan retires IS a
    `bash <script>` invocation that itself runs plan-progress.py. Chaining it in
    as the base therefore produces the bar TWICE — once from the old wrapper,
    once from the chain script — and nothing at install or render time says so.
    That is the exact shape of the wiring this repo ships against today, so the
    upgrade path hits it rather than some hypothetical user.
    """
    try:
        return "plan-progress.py" in Path(base_path).read_text(
            encoding="utf-8", errors="ignore"
        )
    except OSError:
        return False


def chain_through(displaced):
    """A `PLAN_STATUSLINE_BASE=<path> ` prefix that preserves a displaced statusline.

    --force used to discard whatever it replaced. The chain script only ever
    runs $HOME/.claude/statusline.sh as its base, and settings.json has no way
    to supply PLAN_STATUSLINE_BASE — so a user whose statusline was a script at
    any other path lost it in every project, and got a blank line whenever no
    plan was executing. Where the displaced entry is a plain `bash <script>`, we
    can keep it as the base instead of destroying it.

    Returns (prefix, reason). `prefix` is "" when the displaced command is not a
    shape we can safely chain — better to hand the user their old command back
    in a message than to guess wrong — and `reason` says which case applied so
    the caller can explain it:

        "ok"          chained
        "not-a-dict"  the entry is a bare string, not a {type, command} object
        "unchainable" node/deno/bun, a pipeline, anything with its own arguments
        "missing"     the script named no longer exists on disk
        "doubles-bar" the script already prints a plan-progress bar of its own
    """
    if not isinstance(displaced, dict):
        return "", "not-a-dict"
    m = BASH_INVOCATION_RE.match(str(displaced.get("command", "")).strip())
    if not m:
        return "", "unchainable"
    base = m.group(1)
    if not os.path.isfile(base):
        return "", "missing"
    if base_emits_own_bar(base):
        return "", "doubles-bar"
    return f"PLAN_STATUSLINE_BASE={shlex.quote(base)} ", "ok"


def resolve_command(target=TARGET):
    """The shell command to write into settings.json, plus how it was derived.

    Returns (command, mode) where mode is "versioned" or "literal". A literal
    path is correct for a dev checkout — it is stable there — and is the honest
    fallback anywhere the version-pinned layout is not recognised.

    Every literal path component is shell-quoted and only the version `*` is
    left to expand. Interpolating the glob bare meant a HOME containing a space
    word-split it, `ls` matched nothing, and the guard below then exec'd
    nothing — losing the user's BASE statusline too, since the chain script is
    what invokes it, with empty stdout and empty stderr to explain it. That is
    the loudest possible failure rendered completely invisible.

    Version selection sorts the version component numerically field by field
    rather than with `sort -V`, which is a GNU extension absent from the BSD
    sort on macOS — a platform this repo explicitly supports. A missing `-V`
    would have failed the same silent way.
    """
    m = VERSION_PINNED_RE.match(target)
    if not m:
        # Double quotes already handle a space here — the literal form was never
        # the defect; only the glob below was. Escape properly in the one case
        # double-quoting cannot survive, a `"` in the path itself.
        if '"' in target:
            return f"bash {shlex.quote(target)}", "literal"
        return f'bash "{target}"', "literal"
    script = (
        "d=%s; s=%s; "
        'p=$(for f in "$d"/*/"$s"; do '
        '[ -f "$f" ] || continue; '
        'v=${f#"$d"/}; v=${v%%%%/*}; '
        'printf "%%s\t%%s\n" "$v" "$f"; '
        "done | sort -t. -k1,1n -k2,2n -k3,3n | tail -1 | cut -f2-); "
        '[ -n "$p" ] && exec bash "$p"'
    ) % (shlex.quote(m.group("prefix")), shlex.quote(m.group("suffix")))
    return f"sh -c {shlex.quote(script)}", "versioned"


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

    Matched as a whole PATH COMPONENT, not as a substring of the command. A raw
    `"statusline-chain.sh" in command` test also claimed ownership of a
    third-party entry that merely mentioned the name — `bash
    ~/bin/my-statusline-chain.sh`, a comment, an argument, a path to an old
    backup — and a bare --install would then "repair" it, bypassing the very
    --force gate README.md promises for a statusLine this tool did not write.
    """
    if not isinstance(entry, dict):
        return False
    command = str(entry.get("command", ""))
    return any(
        os.path.basename(hit) == CHAIN_NAME for hit in CHAIN_PATH_RE.findall(command)
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
        # Explicit encoding: read_text() defaults to the locale encoding, so
        # under LC_ALL=C a settings.json holding any non-ASCII byte died with an
        # unactionable "'ascii' codec can't decode". write_settings() already
        # got this right; both read paths did not.
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        die(f"cannot read {path}: {e}")
    except UnicodeDecodeError as e:
        die(f"refusing to modify {path}: it is not valid UTF-8 ({e}).")
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
        # Inherit the source's mode rather than the umask. write_bytes() creates
        # at 0666 & ~umask — typically 0644 — so a settings.json deliberately
        # chmod'd 0600 because it carries `env` API keys or an apiKeyHelper left
        # a world-readable copy of those secrets sitting in ~/.claude forever.
        os.chmod(backup_path, path.stat().st_mode & 0o7777)
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
        raw = path.read_text(encoding="utf-8")
    except OSError as e:
        print(f"statusline-install: cannot read {path}: {e}", file=sys.stderr)
        return 1
    except UnicodeDecodeError as e:
        print(f"statusline-install: {path} is not valid UTF-8: {e}", file=sys.stderr)
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
        # Compare only the part AFTER any preserved-base prefix. Comparing the
        # whole string meant a chained entry never equalled a fresh install's
        # command, so --status permanently advised `--install` to "repair" it —
        # and that install then dropped the base. The tool recommended the one
        # action that destroyed the config it had just preserved.
        base, rest = split_base_prefix(current)
        if base:
            print(f"  (chained after your own statusline: {base})")
        if rest != desired_entry()["command"]:
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
    if ours and isinstance(current, dict):
        # Carry a previously preserved base forward. Without this, repairing our
        # own entry rebuilt `command` from desired_entry() alone and silently
        # dropped the PLAN_STATUSLINE_BASE prefix a --force install had added —
        # so the user's own statusline survived the install that displaced it
        # and was destroyed by the next routine repair.
        base, _rest = split_base_prefix(current.get("command", ""))
        if base:
            merged["command"] = (
                f"PLAN_STATUSLINE_BASE={shlex.quote(base)} " + merged["command"]
            )
    if current is not None and not ours:
        prefix, reason = chain_through(current)
        # `current` may be a bare string rather than a {type, command} object;
        # .get() on it raised AttributeError and turned --force, the documented
        # escape hatch, into an unactionable crash.
        shown = current.get("command") if isinstance(current, dict) else current
        if prefix:
            merged["command"] = prefix + merged["command"]
            print(f"Preserved your previous statusline as the base: {shown}")
        elif reason == "doubles-bar":
            print(f"NOTE: your previous statusline was NOT chained in:\n"
                  f"  {shown}\n"
                  f"  It runs plan-progress.py itself, so chaining it would print the\n"
                  f"  plan progress bar twice. It is preserved in the backup beside\n"
                  f"  settings.json; delete it once this install renders correctly.",
                  file=sys.stderr)
        else:
            print(f"NOTE: replaced a statusline this tool cannot chain through:\n"
                  f"  {shown}\n"
                  f"  It is preserved in the backup beside settings.json. To keep it "
                  f"as the base, set PLAN_STATUSLINE_BASE to a bash script path.",
                  file=sys.stderr)
    data["statusLine"] = merged
    write_settings(path, data, existed)
    action = "Repaired" if current is not None else "Installed"
    print(f"{action} statusLine -> {merged['command']} in {path}")
    return 0


def cmd_remove(force):
    path = get_settings_path()
    if not path.exists():
        print(f"Nothing to remove: {path} does not exist.")
        return 0
    data, existed = load_settings_for_write(path)
    if "statusLine" not in data:
        print(f"statusLine not present in {path}; nothing to do.")
        return 0
    # --remove is a destructive action on a key this tool may not own, so it
    # takes the SAME ownership gate as --install. Without it, a user with a
    # hand-configured statusLine who ran `/planning:statusline remove` to tidy
    # up lost their own configuration silently — while planning/README.md
    # promises this installer "refuses to clobber a third-party statusLine
    # without --force", a promise a reader reasonably reads as covering remove.
    if not is_ours(data["statusLine"]) and not force:
        print(
            "statusline-install: statusLine was not installed by this tool: "
            f"{data['statusLine']!r}\n"
            "statusline-install: refusing to remove it without --force.",
            file=sys.stderr,
        )
        return 1
    # If our entry chained a base the user already had, --remove restores THAT
    # rather than deleting the key. Deleting outright made remove the inverse of
    # a fresh install but not of a --force install: a user whose own statusline
    # had been preserved as the base lost it entirely on remove, recoverable
    # only from a .bak they had no reason to know about — while README.md says
    # remove merely "takes it back out".
    base, _rest = split_base_prefix(
        data["statusLine"].get("command", "")
        if isinstance(data["statusLine"], dict)
        else ""
    )
    if base:
        restored = {"type": "command", "command": f'bash "{base}"'}
        for k, v in data["statusLine"].items():
            if k not in ("type", "command"):
                restored[k] = v
        data["statusLine"] = restored
        write_settings(path, data, existed)
        print(f"Removed the plan bar and restored your previous statusline in {path}.\n"
              f"  {restored['command']}")
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
        return cmd_remove(args.force)
    return cmd_install(args.force)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception as e:  # a CLI tool must never hand the user a traceback
        print(f"statusline-install: unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
