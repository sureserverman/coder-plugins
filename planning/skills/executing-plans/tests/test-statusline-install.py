#!/usr/bin/env python3
"""Fixture suite for statusline-install.py — run directly (CI convention):
    python3 planning/skills/executing-plans/tests/test-statusline-install.py

Every case points HOME at a fresh temp directory and runs the installer as a
subprocess, so the REAL ~/.claude/settings.json is never touched. Asserts:
install into an empty/missing settings file, idempotency, verbatim survival
of unrelated keys, refusal (and --force override) of a third-party
statusLine, byte-identical round trip on install-then-remove, refusal to
touch malformed JSON, atomic-write evidence, --status reporting, byte-exact
round trip across non-canonical indent styles, non-ASCII verbatim survival,
file-mode preservation, symlinked settings.json handling, structural
"is this ours?" relocation/repair detection, extra-key preservation on
repair, and resolve_command()'s versioned/literal resolution.
"""
import atexit
import glob
import io
import contextlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "statusline-install.py"
CHAIN = SCRIPT.parent / "statusline-chain.sh"
EXPECTED_COMMAND = f'bash "{CHAIN}"'

FAILURES = []

# Every mkdtemp() here used to leak: ~20 directories per run accumulated under
# the OS temp dir on a dev machine running the suite repeatedly.
_TMPDIRS = []


def mkdtemp(**kw):
    d = tempfile.mkdtemp(**kw)
    _TMPDIRS.append(d)
    return d


@atexit.register
def _cleanup_tmpdirs():
    for d in _TMPDIRS:
        shutil.rmtree(d, ignore_errors=True)


def check(cond, label):
    print(("  ok  " if cond else "  FAIL") + f"  {label}")
    if not cond:
        FAILURES.append(label)


def run(home, args):
    env = dict(os.environ)
    env["HOME"] = str(home)
    r = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
    )
    return r


def fresh_home(tmp, name):
    home = tmp / name
    home.mkdir(parents=True)
    return home


def write_canonical(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n")


def write_raw(path, text):
    """Write EXACT text, bypassing the installer's own canonical formatting.
    Used for fixtures that must not accidentally already be in the format
    the installer itself emits (indent=2), which would let a broken
    byte-restoration path pass by coincidence.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")



def case_space_in_path():
    """The seam both Tier-2 Criticals lived in: a full --install into a cache
    tree whose path contains a space, then executing the command recovered from
    the written JSON end to end.

    Each suite was airtight for its own file and blind to the join: the install
    suite only ever built resolve_command() on clean synthetic paths, and the
    chain suite invoked statusline-chain.sh directly rather than through the
    generated `sh -c` wrapper. An unquoted glob therefore shipped, and a HOME
    with a space in it lost the ENTIRE statusline -- base included -- with empty
    stdout and empty stderr to explain it.
    """
    print("17. end-to-end through the generated command, path containing a space:")
    home = mkdtemp(prefix="sl space ")
    base = os.path.join(home, ".claude", "plugins", "cache", "mkt", "planning")
    for v in ("0.9.0", "0.37.0"):
        d = os.path.join(base, v, "skills", "executing-plans", "scripts")
        os.makedirs(d, exist_ok=True)
        chain = os.path.join(d, "statusline-chain.sh")
        with open(chain, "w") as f:
            f.write('#!/bin/bash\ncat >/dev/null\nprintf "CHAIN-%s"\n' % v)
        os.chmod(chain, 0o755)
    installer = os.path.join(base, "0.37.0", "skills", "executing-plans",
                             "scripts", "statusline-install.py")
    shutil.copy(SCRIPT, installer)
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    env = dict(os.environ, HOME=home)
    r = subprocess.run([sys.executable, installer, "--install"],
                       env=env, capture_output=True, text=True)
    check(r.returncode == 0, "install rc 0 from a cache path containing a space")
    with open(os.path.join(home, ".claude", "settings.json")) as f:
        written = json.load(f)["statusLine"]["command"]
    run = subprocess.run(written, shell=True, input="{}",
                         capture_output=True, text=True)
    check(run.returncode == 0,
          "the command written to settings.json exits 0 (was rc=1, silent, before)")
    check(run.stdout == "CHAIN-0.37.0",
          "it execs the newest chain script (got %r)" % run.stdout)
    check(run.stderr == "",
          "and stays silent on stderr")


def case_apostrophe_in_path():
    """The apostrophe half of a claim the record already made.

    Commits `fd2ca84` / `d827283` say the quoting was verified "against paths
    containing a space **and an apostrophe**". Only the space half shipped as a
    case (`case_space_in_path`); the apostrophe was checked by hand once and
    never pinned, so nothing in the suite would notice it regressing. That is a
    behavioral claim in the permanent record with no artifact behind it — the
    shape honest-gates names — and this case is the artifact (BL-050).

    An apostrophe is the harder character precisely because the two quoting
    branches disagree about it: double quotes carry a space fine but leave a
    single quote to whatever the shell does next, so only the shlex.quote path
    survives it.
    """
    print("25. end-to-end through the generated command, path containing an apostrophe:")
    home = mkdtemp(prefix="sl it's ")
    base = os.path.join(home, ".claude", "plugins", "cache", "mkt", "planning")
    for v in ("0.9.0", "0.37.0"):
        d = os.path.join(base, v, "skills", "executing-plans", "scripts")
        os.makedirs(d, exist_ok=True)
        chain = os.path.join(d, "statusline-chain.sh")
        with open(chain, "w") as f:
            f.write('#!/bin/bash\ncat >/dev/null\nprintf "CHAIN-%s"\n' % v)
        os.chmod(chain, 0o755)
    installer = os.path.join(base, "0.37.0", "skills", "executing-plans",
                             "scripts", "statusline-install.py")
    shutil.copy(SCRIPT, installer)
    os.makedirs(os.path.join(home, ".claude"), exist_ok=True)
    env = dict(os.environ, HOME=home)
    r = subprocess.run([sys.executable, installer, "--install"],
                       env=env, capture_output=True, text=True)
    check(r.returncode == 0, "install rc 0 from a cache path containing an apostrophe")
    with open(os.path.join(home, ".claude", "settings.json")) as f:
        written = json.load(f)["statusLine"]["command"]
    run = subprocess.run(written, shell=True, input="{}",
                         capture_output=True, text=True)
    check(run.returncode == 0,
          "the command written to settings.json exits 0 with an apostrophe in the path")
    check(run.stdout == "CHAIN-0.37.0",
          "it execs the newest chain script (got %r)" % run.stdout)
    check(run.stderr == "", "and stays silent on stderr")
    # Idempotence: a second install must not double-quote or re-wrap the entry.
    r2 = subprocess.run([sys.executable, installer, "--install"],
                        env=env, capture_output=True, text=True)
    check(r2.returncode == 0, "re-install rc 0")
    with open(os.path.join(home, ".claude", "settings.json")) as f:
        again = json.load(f)["statusLine"]["command"]
    check(again == written, "the written command is byte-identical on re-install")



def case_bom_settings():
    """A UTF-8 BOM is stripped on read, not reported as malformed JSON (BL-046).

    The script reads settings.json in THREE places, and a sweep found the third
    after the plan had named only two. Two of the three are real defects:

      load_settings_for_write -> json.loads raises, so --install dies with
        "refusing to modify ... malformed JSON" and sends the user to hand-edit
        a file that is not malformed;
      cmd_status              -> the same, so --status reports "not valid JSON"
        and exits 1 on a perfectly good file.

    The third, detect_indent's read inside write_settings, is NOT a defect and
    is deliberately not asserted here: `detect_indent` matches `^([ \t]+)"`
    under re.M, so it scans any line and a leading BOM never reached its answer
    (verified directly: detect_indent returns 4 with and without one). Its read
    was changed anyway so all three sites share one encoding rule, but claiming
    a fixture proves that change would be claiming coverage this suite does not
    have. Editors that write a BOM by default (Notepad, some VS Code setups) are
    how a settings.json acquires one.

    The written file must come back WITHOUT a BOM: utf-8-sig on read, plain
    utf-8 on write, so the file is normalised rather than carrying it forever.
    """
    print("26. a UTF-8 BOM in settings.json:")
    # (a) --install: the loud failure
    home = mkdtemp(prefix="sl bom ")
    cl = os.path.join(home, ".claude")
    os.makedirs(cl)
    sp = os.path.join(cl, "settings.json")
    with open(sp, "w", encoding="utf-8-sig") as f:
        json.dump({"theme": "dark"}, f, indent=4)
    r = subprocess.run([sys.executable, SCRIPT, "--install"],
                       env=dict(os.environ, HOME=home), capture_output=True, text=True)
    check(r.returncode == 0,
          "install succeeds on a BOM'd settings.json (rc=%d: %s)"
          % (r.returncode, r.stderr.strip()[:90]))
    raw = Path(sp).read_bytes()
    check(not raw.startswith(b"\xef\xbb\xbf"),
          "the written settings.json carries no BOM")
    try:
        with open(sp, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (ValueError, OSError) as e:
        data = {}
        check(False, "settings.json is readable JSON after the install (%s)" % e)
    check(data.get("theme") == "dark", "the pre-existing key survives")
    check("statusLine" in data, "the statusLine entry was written")
    # The indent assertion is only meaningful because the entry above proves the
    # file was actually rewritten; on an untouched file it would pass vacuously.
    lines = Path(sp).read_text(encoding="utf-8-sig").split("\n")
    indent = (len(lines[1]) - len(lines[1].lstrip())) if len(lines) > 1 else -1
    check(indent == 4, "the 4-space indent survives the rewrite (got %d)" % indent)

    # (b) --status: the same defect on the read the sweep found
    home2 = mkdtemp(prefix="sl bomstat ")
    cl2 = os.path.join(home2, ".claude")
    os.makedirs(cl2)
    sp2 = os.path.join(cl2, "settings.json")
    with open(sp2, "w", encoding="utf-8-sig") as f:
        json.dump({"statusLine": {"type": "command", "command": "x"}}, f, indent=2)
    r2 = subprocess.run([sys.executable, SCRIPT, "--status"],
                        env=dict(os.environ, HOME=home2), capture_output=True, text=True)
    check(r2.returncode == 0,
          "--status succeeds on a BOM'd settings.json (rc=%d: %s)"
          % (r2.returncode, r2.stderr.strip()[:90]))
    check("not valid JSON" not in r2.stderr,
          "--status does not call a BOM'd file invalid JSON")


def case_backup_atomic_and_pruned():
    """The backup is the one artifact the rollback path depends on (BL-049).

    Two defects in `backup()`. It was a plain `write_bytes()`, so an ENOSPC or
    EIO part-way through left a TRUNCATED `.bak` — the original untouched, but
    the file you would restore from silently unreliable, which is the one file
    that must not be. And nothing pruned, so backups accumulated in ~/.claude
    forever, one per install, each a copy of a file that can hold `env` API keys.

    Fault injection is on os.fsync, which is a real symptom (a full or failing
    disk surfaces there) and which also discriminates: the old write_bytes()
    path never called fsync, so injecting it left a complete .bak and the
    "nothing survives a failed backup" assertion failed. The new path writes to
    a temp name, fsyncs, then renames, so an injected failure leaves neither.

    The mode inheritance is asserted here as a REGRESSION guard, not as new
    work: it already existed deliberately, and rewriting the function around it
    is exactly when it would be lost.
    """
    print("27. backup() is atomic and pruned:")
    # `mod` is a local of main(); load our own handle rather than reaching for it.
    spec = importlib.util.spec_from_file_location("statusline_install_bak", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    home = mkdtemp(prefix="sl bak ")
    cl = os.path.join(home, ".claude")
    os.makedirs(cl)
    sp = Path(cl) / "settings.json"
    sp.write_text(json.dumps({"theme": "dark"}, indent=2) + "\n", encoding="utf-8")
    os.chmod(sp, 0o600)

    # (a) a failed backup leaves nothing behind
    real_fsync = os.fsync
    def boom(fd):
        raise OSError(28, "No space left on device")
    mod.os.fsync = boom
    try:
        try:
            mod.backup(sp)
        except (SystemExit, OSError):
            pass
    finally:
        mod.os.fsync = real_fsync
    leftovers = sorted(Path(cl).glob("settings.json.bak.*")) + sorted(Path(cl).glob("settings.json.*.tmp"))
    check(not leftovers,
          "a backup interrupted mid-write leaves no .bak and no .tmp (found %r)"
          % [f.name for f in leftovers])
    check(sp.read_text(encoding="utf-8").strip().endswith("}"),
          "the original settings.json is untouched by a failed backup")

    # (b) mode inheritance survives the rewrite. 0640, deliberately: mkstemp
    # creates at 0600, so a 0600 source cannot distinguish "inherited" from
    # "mkstemp's default" and the assertion passes with the chmod deleted — it
    # did, until the mutant survived and exposed it. 0640 differs from both the
    # umask default and mkstemp's, so only a real inherit produces it.
    os.chmod(sp, 0o640)
    b = mod.backup(sp)
    got = oct(Path(b).stat().st_mode & 0o777)
    check(got == "0o640",
          "the backup inherits the source's mode rather than mkstemp's 0600 or the "
          "umask's 0644 (got %s) — settings.json can carry env API keys and an "
          "apiKeyHelper" % got)
    check(Path(b).read_bytes() == sp.read_bytes(), "the backup is a complete copy")
    # and the security direction specifically: never WIDER than the source
    os.chmod(sp, 0o600)
    b2 = mod.backup(sp)
    m2 = Path(b2).stat().st_mode & 0o777
    check(m2 & 0o077 == 0,
          "a 0600 settings.json never yields a group/world-readable backup (got %s)"
          % oct(m2))

    # (c) pruning: backups do not accumulate forever
    created = [Path(mod.backup(sp)) for _ in range(15)]
    baks = sorted(Path(cl).glob("settings.json.bak.*"))
    keep = getattr(mod, "BACKUP_KEEP", None)
    check(keep is not None, "the script declares a BACKUP_KEEP retention bound")
    check(keep is not None and len(baks) <= keep,
          "backups are pruned to the newest %s (found %d)" % (keep, len(baks)))
    # Anchored to the paths backup() actually returned, in creation order.
    # The previous form compared a sorted list against a slice of itself, which
    # is true of ANY list and would have passed even had pruning kept the OLDEST
    # and deleted the newest — the exact regression it was written to catch.
    survivors = {f.name for f in baks}
    check(created[-1].name in survivors,
          "the most recently created backup survived pruning")
    check(created[0].name not in survivors,
          "the oldest backup was the one evicted, not an arbitrary member")

    # (d) a crash-orphaned .tmp never occupies a retention slot
    orphan = Path(cl) / "settings.json.bak.zz_orphan.tmp"
    orphan.write_bytes(b"partial")
    hand = Path(cl) / "settings.json.bak.mine"
    hand.write_bytes(b"a copy the user made")
    mod.backup(sp)
    check(not orphan.exists(),
          "a crash-orphaned .tmp is swept rather than counted as a backup")
    check(hand.exists(),
          "a user's own hand-named settings.json.bak.mine is never deleted")
    # Stated rather than implied: that assertion holds because eviction takes the
    # lexically smallest and digits sort before letters, so a non-timestamp name
    # is never the oldest — NOT because of any name-shape filter. A filter was
    # written, found unprovable by mutation (widening the glob left this check
    # green), and removed.



def case_hardlinked_settings():
    """A hardlinked settings.json keeps its links (BL-048).

    mkstemp + os.replace swaps a whole inode, so a settings.json that is one of
    several hardlinks to the same file loses the link: count drops 2 -> 1 and
    every other path keeps the OLD content forever, diverging silently.

    The fix preserves the link and pays for it in atomicity, which is a real
    trade and is disclosed rather than hidden. The precedent is this script's
    own get_settings_path(), which already resolves SYMLINKS so a dotfile
    manager's real file is the one written -- "following the link writes where
    they expect". A hardlink is the same class of user-established topology, so
    the same reasoning applies. The single-link path is untouched and stays
    fully atomic, which this case pins by inode identity: replaced when there is
    one link, preserved when there are two. Losing that distinction silently is
    the regression worth catching.
    """
    print("28. a hardlinked settings.json:")
    # (a) two links: the link survives and BOTH paths see the new content
    home = mkdtemp(prefix="sl hl ")
    cl = os.path.join(home, ".claude")
    os.makedirs(cl)
    sp = Path(cl) / "settings.json"
    sp.write_text(json.dumps({"theme": "dark"}, indent=2) + "\n", encoding="utf-8")
    other = Path(home) / "dotfiles-settings.json"
    os.link(sp, other)
    ino_before = sp.stat().st_ino
    r = subprocess.run([sys.executable, SCRIPT, "--install"],
                       env=dict(os.environ, HOME=home), capture_output=True, text=True)
    check(r.returncode == 0, "install rc 0 on a hardlinked settings.json")
    check(sp.stat().st_nlink == 2,
          "the hardlink survives the install (nlink=%d, was 2)" % sp.stat().st_nlink)
    check(sp.stat().st_ino == ino_before,
          "the inode is preserved, so every other link still points at this file")
    check("statusLine" in other.read_text(encoding="utf-8"),
          "the OTHER link sees the new content rather than keeping a stale copy")
    check("atomic" in r.stderr.lower() or "hardlink" in r.stderr.lower(),
          "the reduced-atomicity trade is disclosed on stderr (got %r)"
          % r.stderr.strip()[:90])
    # The whole design leans on a backup existing before the non-atomic write,
    # so pin the artifact rather than trusting the prose that asserts it.
    check(list(Path(cl).glob("settings.json.bak.*")),
          "a backup exists after the in-place write — the recovery path the "
          "non-atomic branch depends on is a file, not a claim")

    # (a2) if the link count cannot be READ, the write refuses rather than
    # guessing. The old default was nlink = 0, which routes to the atomic
    # replace -- the exact link-breaking behaviour this branch prevents, done
    # silently and indistinguishably from a legitimate single-link file.
    #
    # The stat is armed on the FIFTH call, which is the nlink read; the four
    # before it are backup()'s and the prev_mode/mkdir reads. An earlier
    # attempt armed on a flag set right after backup(), which also broke
    # prev_mode and detect_indent two lines later -- so BOTH the fixed and the
    # fail-open builds died for unrelated reasons and the assertion passed
    # either way. It was vacuous, and only the mutation showed it.
    #
    # This is why the assertion below checks the MESSAGE and not just the exit:
    # if the call order ever drifts so that call 5 is no longer the nlink read,
    # this fails loudly and tells you to re-count, instead of quietly passing.
    spec_h = importlib.util.spec_from_file_location("statusline_install_hl", str(SCRIPT))
    mod_h = importlib.util.module_from_spec(spec_h)
    spec_h.loader.exec_module(mod_h)

    home3 = mkdtemp(prefix="sl statfail ")
    cl3 = os.path.join(home3, ".claude")
    os.makedirs(cl3)
    sp3 = Path(cl3) / "settings.json"
    sp3.write_text(json.dumps({"theme": "dark"}, indent=2) + "\n", encoding="utf-8")
    before3 = sp3.read_bytes()

    seen = [0]

    class StatFailsOnNlinkRead(type(Path(cl3))):
        def stat(self, *a, **kw):
            seen[0] += 1
            if seen[0] == 5:
                raise OSError(5, "Input/output error")
            return super().stat(*a, **kw)

    err3 = io.StringIO()
    refused = False
    try:
        with contextlib.redirect_stderr(err3):
            mod_h.write_settings(
                StatFailsOnNlinkRead(str(sp3)),
                {"statusLine": {"type": "command", "command": "x"}}, True)
    except SystemExit:
        refused = True
    except OSError:
        refused = False
    check(refused and "hardlinked" in err3.getvalue(),
          "an unreadable link count REFUSES with a message naming the hardlink "
          "question, rather than defaulting to the path that breaks links "
          "(refused=%s, stderr=%r)" % (refused, err3.getvalue().strip()[:80]))
    check(sp3.read_bytes() == before3,
          "and settings.json is left byte-identical when it refuses")

    # (b) one link: the atomic replace path is unchanged, proven by inode change
    home2 = mkdtemp(prefix="sl nohl ")
    cl2 = os.path.join(home2, ".claude")
    os.makedirs(cl2)
    sp2 = Path(cl2) / "settings.json"
    sp2.write_text(json.dumps({"theme": "dark"}, indent=2) + "\n", encoding="utf-8")
    ino2_before = sp2.stat().st_ino
    r2 = subprocess.run([sys.executable, SCRIPT, "--install"],
                        env=dict(os.environ, HOME=home2), capture_output=True, text=True)
    check(r2.returncode == 0, "install rc 0 on an ordinary settings.json")
    check(sp2.stat().st_ino != ino2_before,
          "a single-link file still goes through mkstemp + os.replace (inode changed)")
    check("atomic" not in r2.stderr.lower(),
          "and says nothing about atomicity, because nothing was traded")


def case_remove_ownership_gate():
    """--remove must refuse a statusLine this tool did not write.

    This gate exists because it already regressed once: --remove deleted any
    entry unconditionally, so a user with a hand-configured statusline lost it
    by running `/planning:statusline remove` to tidy up. It was implemented in
    remediation and nothing asserted it, which is how it would regress again.
    """
    print("18. --remove honours the same ownership gate as --install:")
    home = mkdtemp()
    os.makedirs(os.path.join(home, ".claude"))
    settings = os.path.join(home, ".claude", "settings.json")
    third_party = {"type": "command", "command": 'node /home/u/my-statusline.js'}
    with open(settings, "w") as f:
        json.dump({"statusLine": third_party, "theme": "dark"}, f, indent=2)
    before = open(settings, "rb").read()
    env = dict(os.environ, HOME=home)
    r = subprocess.run([sys.executable, SCRIPT, "--remove"],
                       env=env, capture_output=True, text=True)
    check(r.returncode != 0, "--remove on a third-party entry exits non-zero")
    check("refusing to remove" in r.stderr, "refusal names what it will not do")
    check(open(settings, "rb").read() == before,
          "the third-party entry is left byte-identical")
    r2 = subprocess.run([sys.executable, SCRIPT, "--remove", "--force"],
                        env=env, capture_output=True, text=True)
    check(r2.returncode == 0, "--remove --force succeeds")
    with open(settings) as f:
        after = json.load(f)
    check("statusLine" not in after, "--force actually removes it")
    check(after.get("theme") == "dark", "unrelated keys survive the forced removal")


def _base_home(tag, script_body='#!/bin/bash\ncat >/dev/null\nprintf "MYBASE"\n'):
    """A HOME whose settings.json wires a plain `bash <script>` statusline."""
    home = Path(mkdtemp(prefix=f"sl-{tag}-"))
    (home / ".claude").mkdir()
    base = home / ".claude" / "mybase.sh"
    base.write_text(script_body)
    os.chmod(base, 0o755)
    write_canonical(home / ".claude" / "settings.json",
                    {"statusLine": {"type": "command", "command": f'bash "{base}"'},
                     "theme": "dark"})
    return home, base


def _command(home):
    return json.loads((home / ".claude" / "settings.json").read_text()).get(
        "statusLine", {}).get("command", "")


def case_repair_preserves_base():
    """A repair install must CARRY a preserved base, and --status must not
    advise the repair that would drop it.

    Reproduced defect: --force preserved the user's statusline as a
    PLAN_STATUSLINE_BASE prefix, then cmd_install's `merged.update(desired)`
    overwrote `command` with the unprefixed form, so the very next plain
    --install destroyed it. --status made it worse by comparing the whole
    prefixed string against a fresh install's command -- never equal -- so it
    permanently printed "run `--install` to repair", steering the user into
    exactly the call that lost their config.
    """
    print("19. a repair install carries a preserved base forward:")
    home, base = _base_home("repair")
    r = run(home, ["--install", "--force"])
    check(r.returncode == 0, "force-install over a third-party bash statusline succeeds")
    check("PLAN_STATUSLINE_BASE=" in _command(home), "the base is preserved as a prefix")

    st = run(home, ["--status"])
    check("differs from what a fresh install would write" not in st.stdout,
          "--status does NOT advise repairing a correctly-chained entry")
    check(str(base) in st.stdout, "--status names the chained base")

    r2 = run(home, ["--install"])
    check(r2.returncode == 0, "a subsequent plain --install succeeds")
    check("PLAN_STATUSLINE_BASE=" in _command(home),
          "the preserved base SURVIVES the repair (was silently dropped)")
    check(str(base) in _command(home), "and still points at the user's own script")


def case_remove_restores_base():
    """--remove is the inverse of whatever install it undoes.

    It used to `del data["statusLine"]` unconditionally, so a user whose own
    statusline had been preserved as the base lost it entirely -- recoverable
    only from a .bak they had no reason to know existed -- while README.md
    describes remove as merely taking the bar back out.
    """
    print("20. --remove restores a preserved base instead of clearing the key:")
    home, base = _base_home("removebase")
    run(home, ["--install", "--force"])
    r = run(home, ["--remove"])
    check(r.returncode == 0, "--remove on our own chained entry succeeds")
    data = json.loads((home / ".claude" / "settings.json").read_text())
    check("statusLine" in data, "statusLine key is NOT deleted when a base was chained")
    check(data["statusLine"]["command"] == f'bash "{base}"',
          f"the user's original command is restored (got {data['statusLine'].get('command')!r})")
    check(data.get("theme") == "dark", "unrelated keys survive")

    print("20b. --remove still clears the key when no base was chained:")
    home2 = Path(mkdtemp(prefix="sl-nobase-"))
    (home2 / ".claude").mkdir()
    write_canonical(home2 / ".claude" / "settings.json", {"theme": "dark"})
    run(home2, ["--install"])
    run(home2, ["--remove"])
    data2 = json.loads((home2 / ".claude" / "settings.json").read_text())
    check("statusLine" not in data2, "plain install/remove round trip still clears the key")


def case_doubled_bar_refused():
    """A base that runs plan-progress.py itself must NOT be chained.

    This repo's own live wiring is exactly that shape -- a hand-written
    statusline-with-plan.sh that calls plan-progress.py on a hard-coded path --
    so `--install --force` chained it in and the progress bar rendered TWICE,
    with nothing at install or render time to say so. The upgrade path hit this,
    not a hypothetical user.
    """
    print("21. a base that already prints the plan bar is refused, not chained:")
    home, base = _base_home(
        "double",
        '#!/bin/bash\ncat >/dev/null\nprintf "OLDBASE"\n'
        'python3 "$HOME/dev/x/plan-progress.py" 2>/dev/null\n',
    )
    r = run(home, ["--install", "--force"])
    check(r.returncode == 0, "force-install still succeeds")
    check("PLAN_STATUSLINE_BASE=" not in _command(home),
          "the doubling wrapper is NOT chained in as the base")
    check("NOT chained in" in r.stderr, "the refusal is explained on stderr")
    check("twice" in r.stderr, "and says why -- the bar would print twice")


def case_is_ours_is_structural():
    """is_ours() matches a path COMPONENT, not a substring of the command.

    A raw `"statusline-chain.sh" in command` test claimed ownership of any
    third-party entry that merely mentioned the name, and a bare --install then
    "repaired" it -- bypassing the --force gate README.md promises.
    """
    print("22. is_ours() does not claim a look-alike third-party script:")
    home = Path(mkdtemp(prefix="sl-ours-"))
    (home / ".claude").mkdir()
    imposter = home / ".claude" / "my-statusline-chain.sh"
    imposter.write_text('#!/bin/bash\nprintf "MINE"\n')
    os.chmod(imposter, 0o755)
    settings = home / ".claude" / "settings.json"
    write_canonical(settings, {"statusLine": {"type": "command",
                                             "command": f'bash "{imposter}"'}})
    before = settings.read_bytes()
    r = run(home, ["--install"])
    check(r.returncode != 0,
          "a bash my-statusline-chain.sh entry is treated as third-party, not ours")
    check("refusing to overwrite" in r.stderr, "and the refusal names the --force gate")
    check(settings.read_bytes() == before, "the look-alike entry is left byte-identical")


def case_non_dict_statusline():
    """A bare-string statusLine must not crash --force.

    chain_through() returned "" for a non-dict and the caller then called
    .get() on it anyway, so --force -- the documented escape hatch -- died with
    an unactionable "'str' object has no attribute 'get'".
    """
    print("23. a bare-string statusLine is handled, not crashed on:")
    home = Path(mkdtemp(prefix="sl-str-"))
    (home / ".claude").mkdir()
    settings = home / ".claude" / "settings.json"
    write_canonical(settings, {"statusLine": "bash /opt/mine.sh", "theme": "dark"})
    r = run(home, ["--install"])
    check(r.returncode != 0, "bare --install still refuses a third-party entry")

    r2 = run(home, ["--install", "--force"])
    check("Traceback" not in r2.stderr, "no traceback on --force")
    check("object has no attribute" not in r2.stderr,
          f"no AttributeError leaks to the user (stderr={r2.stderr!r})")
    check(r2.returncode == 0, "--force actually completes")
    data = json.loads(settings.read_text())
    check(data.get("statusLine", {}).get("command") == EXPECTED_COMMAND,
          "the entry is replaced with ours")
    check(data.get("theme") == "dark", "unrelated keys survive")

    st = run(home, ["--status"])
    check(st.returncode == 0, "--status handles the same shape without dying")


def case_non_utf8_settings():
    """A settings.json that is not valid UTF-8 gets a clear refusal.

    Both read paths used read_text() with no encoding, so they fell back to the
    locale codec: under LC_ALL=C any non-ASCII byte died with "'ascii' codec
    can't decode". write_settings() already passed encoding="utf-8".
    """
    print("24. non-UTF-8 settings.json refuses cleanly under a C locale:")
    home = Path(mkdtemp(prefix="sl-enc-"))
    (home / ".claude").mkdir()
    settings = home / ".claude" / "settings.json"
    settings.write_bytes(b'{"name": "caf\xe9"}\n')  # latin-1, not UTF-8
    before = settings.read_bytes()
    env = dict(os.environ, HOME=str(home), LC_ALL="C", LANG="C",
               PYTHONCOERCECLOCALE="0", PYTHONUTF8="0")
    r = subprocess.run([sys.executable, str(SCRIPT), "--install"],
                       env=env, capture_output=True, text=True)
    check(r.returncode != 0, "install refuses")
    check("Traceback" not in r.stderr, "no traceback")
    check("codec" not in r.stderr.lower() or "not valid UTF-8" in r.stderr,
          f"the message is actionable, not a raw codec error (stderr={r.stderr!r})")
    check(settings.read_bytes() == before, "the file is left byte-identical")

    print("24b. a UTF-8 settings.json still works under the same C locale:")
    home2 = Path(mkdtemp(prefix="sl-enc2-"))
    (home2 / ".claude").mkdir()
    s2 = home2 / ".claude" / "settings.json"
    s2.write_text('{\n  "name": "café"\n}\n', encoding="utf-8")
    env2 = dict(env, HOME=str(home2))
    r2 = subprocess.run([sys.executable, str(SCRIPT), "--install"],
                        env=env2, capture_output=True, text=True)
    check(r2.returncode == 0, "install succeeds on valid UTF-8 under LC_ALL=C")
    check(json.loads(s2.read_text(encoding="utf-8")).get("name") == "café",
          "the non-ASCII value survives verbatim")


def main():
    tmp = Path(mkdtemp(prefix="statusline-install-test-"))

    print("1. install into settings.json with no statusLine:")
    home1 = fresh_home(tmp, "home1")
    settings1 = home1 / ".claude" / "settings.json"
    write_canonical(settings1, {"foo": "bar"})
    r = run(home1, ["--install"])
    check(r.returncode == 0, "install rc 0")
    data = json.loads(settings1.read_text())
    check(data.get("statusLine", {}).get("type") == "command", "statusLine.type == command")
    check(data.get("statusLine", {}).get("command") == EXPECTED_COMMAND,
          "statusLine.command points at resolved chain script")
    check(data.get("foo") == "bar", "unrelated key survives")

    print("2. install into a MISSING settings.json (and missing ~/.claude):")
    home2 = fresh_home(tmp, "home2")
    settings2 = home2 / ".claude" / "settings.json"
    check(not settings2.exists(), "precondition: settings.json absent")
    r = run(home2, [])  # bare invocation defaults to install
    check(r.returncode == 0, "install rc 0 with no flags")
    check(settings2.is_file(), "settings.json created")
    data2 = json.loads(settings2.read_text())
    check(data2.get("statusLine", {}).get("command") == EXPECTED_COMMAND,
          "created file wired correctly")

    print("3. install twice -> byte-identical:")
    once = settings1.read_bytes()
    r = run(home1, ["--install"])
    check(r.returncode == 0, "second install rc 0")
    twice = settings1.read_bytes()
    check(once == twice, "installing twice is byte-identical")

    print("4. populated settings with nested object + array survive verbatim:")
    home4 = fresh_home(tmp, "home4")
    settings4 = home4 / ".claude" / "settings.json"
    original4 = {
        "theme": "dark",
        "nested": {"a": 1, "b": [1, 2, 3], "c": {"deep": True}},
        "list": ["x", "y", {"z": True}, None],
        "other": None,
        "n": 3.5,
    }
    write_canonical(settings4, original4)
    r = run(home4, ["--install"])
    check(r.returncode == 0, "install rc 0")
    data4 = json.loads(settings4.read_text())
    for k, v in original4.items():
        check(data4.get(k) == v, f"key {k!r} survives verbatim")
    check("statusLine" in data4, "statusLine added alongside")

    print("5. pre-existing third-party statusLine is not clobbered:")
    home5 = fresh_home(tmp, "home5")
    settings5 = home5 / ".claude" / "settings.json"
    third_party = {"type": "command", "command": 'bash "/opt/other/statusline.sh"'}
    write_canonical(settings5, {"statusLine": third_party})
    before5 = settings5.read_bytes()
    r = run(home5, ["--install"])
    check(r.returncode != 0, "install without --force exits non-zero")
    check("/opt/other/statusline.sh" in (r.stderr + r.stdout), "message names the existing command")
    check(settings5.read_bytes() == before5, "file left untouched without --force")
    r = run(home5, ["--install", "--force"])
    check(r.returncode == 0, "install --force exits 0")
    data5 = json.loads(settings5.read_text())
    check(data5.get("statusLine", {}).get("command") == EXPECTED_COMMAND,
          "--force replaces the third-party statusLine")

    print("6. install then --remove on a canonical file is byte-identical to the original:")
    home6 = fresh_home(tmp, "home6")
    settings6 = home6 / ".claude" / "settings.json"
    original6 = {"alpha": 1, "beta": {"x": 2}, "gamma": [1, 2, 3]}
    write_canonical(settings6, original6)
    original6_bytes = settings6.read_bytes()
    r = run(home6, ["--install"])
    check(r.returncode == 0, "install rc 0")
    check(settings6.read_bytes() != original6_bytes, "install actually changed the file")
    r = run(home6, ["--remove"])
    check(r.returncode == 0, "remove rc 0")
    check(settings6.read_bytes() == original6_bytes,
          "install-then-remove is byte-identical to the pre-canonical original")

    print("7. malformed JSON is refused and left byte-identical:")
    home7 = fresh_home(tmp, "home7")
    settings7 = home7 / ".claude" / "settings.json"
    settings7.parent.mkdir(parents=True)
    settings7.write_text("{ this is not valid json")
    before7 = settings7.read_bytes()
    r = run(home7, ["--install"])
    check(r.returncode != 0, "install on malformed JSON exits non-zero")
    check(r.stdout == "", "no stdout noise on refusal")
    check("Traceback" not in r.stderr, "no traceback on malformed JSON")
    check(settings7.read_bytes() == before7, "malformed file left byte-identical")
    backups7 = list(settings7.parent.glob("settings.json.bak.*"))
    check(backups7 == [], "no backup taken when the write never happens")

    print("8. atomicity:")
    # The two source-greps that used to stand here ("os.replace(" in src,
    # "tempfile.mkstemp(" in src) were the shape this plan learned to distrust:
    # they assert the implementation's tokens rather than its behavior, so they
    # would keep passing across a rewrite that lost atomicity while retaining
    # the words. The fault injection below is the real assertion.
    # Strongest practical check: make ~/.claude read-only (as the real owning,
    # non-root user) so the write cannot land at all, and confirm the
    # settings file survives untouched with no partial/temp file left behind
    # and no traceback — this doubles as the read-only-~/.claude requirement.
    home8 = fresh_home(tmp, "home8")
    claude8 = home8 / ".claude"
    claude8.mkdir()
    settings8 = claude8 / "settings.json"
    write_canonical(settings8, {"k": "v"})
    before8 = settings8.read_bytes()
    os.chmod(claude8, 0o500)
    try:
        r = run(home8, ["--install"])
        check(r.returncode != 0, "install into a read-only ~/.claude exits non-zero")
        check("Traceback" not in r.stderr, "no traceback on read-only ~/.claude")
    finally:
        os.chmod(claude8, 0o700)
    check(settings8.read_bytes() == before8, "settings.json unchanged after failed write")
    leftovers = [p for p in claude8.iterdir() if p.name != "settings.json"]
    check(leftovers == [], "no partial temp file left behind after the simulated failure")

    print("9. --status on an unwired settings file:")
    home9 = fresh_home(tmp, "home9")
    settings9 = home9 / ".claude" / "settings.json"
    write_canonical(settings9, {"foo": 1})
    r = run(home9, ["--status"])
    check(r.returncode == 0, "--status rc 0 on unwired file")
    check("not wired" in r.stdout, "--status reports not wired")

    print("10. install-then-remove is byte-identical for non-canonical indent styles:")
    original10 = {"theme": "dark", "nested": {"a": 1, "b": [1, 2, 3]}, "plain": "x"}
    canonical10 = json.dumps(original10, indent=2) + "\n"
    fixtures10 = [
        ("4-space", json.dumps(original10, indent=4) + "\n"),
        ("tab", json.dumps(original10, indent="\t") + "\n"),
        ("compact", json.dumps(original10) + "\n"),
    ]
    for label, text in fixtures10:
        check(text != canonical10,
              f"[{label}] fixture is NOT pre-canonicalised to the installer's own indent=2 output")
        home = fresh_home(tmp, f"home10-{label}")
        settings = home / ".claude" / "settings.json"
        write_raw(settings, text)
        before = settings.read_bytes()
        r = run(home, ["--install"])
        check(r.returncode == 0, f"[{label}] install rc 0")
        check(settings.read_bytes() != before, f"[{label}] install actually changed the file")
        r = run(home, ["--remove"])
        check(r.returncode == 0, f"[{label}] remove rc 0")
        check(settings.read_bytes() == before,
              f"[{label}] install-then-remove restores the original formatting byte-for-byte")

    print("11. non-ASCII values survive install byte-verbatim:")
    home11 = fresh_home(tmp, "home11")
    settings11 = home11 / ".claude" / "settings.json"
    original11 = {"label": "café ✓", "greeting": "Привет мир"}
    text11 = json.dumps(original11, indent=2, ensure_ascii=False) + "\n"
    write_raw(settings11, text11)
    r = run(home11, ["--install"])
    check(r.returncode == 0, "install rc 0")
    raw11 = settings11.read_text(encoding="utf-8")
    check("café ✓" in raw11, "café ✓ survives as literal UTF-8, not re-escaped")
    check("Привет мир" in raw11, "Cyrillic string survives as literal UTF-8, not re-escaped")
    check("\\u" not in raw11, "no \\uXXXX escape sequences appear anywhere in the file")
    data11 = json.loads(raw11)
    check(data11.get("label") == "café ✓", "label value round-trips correctly")
    check(data11.get("greeting") == "Привет мир", "greeting value round-trips correctly")

    print("12. file mode is preserved across install:")
    home12 = fresh_home(tmp, "home12")
    settings12 = home12 / ".claude" / "settings.json"
    write_canonical(settings12, {"k": "v"})
    os.chmod(settings12, 0o640)
    r = run(home12, ["--install"])
    check(r.returncode == 0, "install rc 0")
    mode12 = settings12.stat().st_mode & 0o777
    check(mode12 == 0o640, f"file mode preserved as 0640 (got {oct(mode12)})")

    print("13. symlinked settings.json is followed, not replaced:")
    home13 = fresh_home(tmp, "home13")
    claude13 = home13 / ".claude"
    claude13.mkdir(parents=True)
    real13 = home13 / "elsewhere" / "real-settings.json"
    real13.parent.mkdir(parents=True)
    write_canonical(real13, {"foo": "bar"})
    link13 = claude13 / "settings.json"
    os.symlink(real13, link13)
    r = run(home13, ["--install"])
    check(r.returncode == 0, "install rc 0")
    check(link13.is_symlink(), "settings.json is STILL a symlink after install")
    check(Path(os.readlink(link13)) == real13, "symlink still points at the original real file")
    data13 = json.loads(real13.read_text())
    check(data13.get("statusLine", {}).get("command") == EXPECTED_COMMAND,
          "the real target file received the statusLine write")
    check(data13.get("foo") == "bar", "unrelated key on the real target survives")

    print("14. relocation: a stale-but-ours absolute path is repaired without --force,")
    print("    while a genuinely third-party statusLine is still refused:")
    home14 = fresh_home(tmp, "home14")
    settings14 = home14 / ".claude" / "settings.json"
    stale14 = {
        "type": "command",
        "command": 'bash "/old/plugins/cache/marketplace/planning/0.12.0/scripts/statusline-chain.sh"',
    }
    write_canonical(settings14, {"statusLine": stale14})
    r = run(home14, ["--install"])
    check(r.returncode == 0,
          "plain --install repairs a relocated statusline-chain.sh entry (no --force needed)")
    data14 = json.loads(settings14.read_text())
    check(data14.get("statusLine", {}).get("command") == EXPECTED_COMMAND,
          "relocated entry is repaired to the current resolved command")

    home14b = fresh_home(tmp, "home14b")
    settings14b = home14b / ".claude" / "settings.json"
    third_party14 = {"type": "command", "command": 'bash "/opt/other/thing.sh"'}
    write_canonical(settings14b, {"statusLine": third_party14})
    r = run(home14b, ["--install"])
    check(r.returncode != 0,
          "genuinely third-party entry (no statusline-chain.sh in command) still refused without --force")
    data14b = json.loads(settings14b.read_text())
    check(data14b.get("statusLine") == third_party14, "third-party entry left untouched")

    print("15. extra keys on our own entry survive a repair install:")
    home15 = fresh_home(tmp, "home15")
    settings15 = home15 / ".claude" / "settings.json"
    ours_with_extra15 = {
        "type": "command",
        "command": 'bash "/old/version/path/statusline-chain.sh"',
        "padding": 2,
    }
    write_canonical(settings15, {"statusLine": ours_with_extra15})
    r = run(home15, ["--install"])
    check(r.returncode == 0, "repair install rc 0 without --force")
    data15 = json.loads(settings15.read_text())
    check(data15.get("statusLine", {}).get("command") == EXPECTED_COMMAND,
          "stale command is repaired to the current resolved command")
    check(data15.get("statusLine", {}).get("padding") == 2,
          "user-added padding key survives the repair")

    print("16. resolve_command(): versioned vs literal mode, and version-ordering correctness:")
    spec = importlib.util.spec_from_file_location("statusline_install", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    versioned_target = (
        "/home/u/.claude/plugins/cache/some-marketplace/planning/0.37.0/"
        "skills/executing-plans/scripts/statusline-chain.sh"
    )
    cmd16, mode16 = mod.resolve_command(versioned_target)
    check(mode16 == "versioned",
          "path under plugins/cache/<marketplace>/<plugin>/<version>/... resolves to versioned mode")
    check("*" in cmd16, "versioned command contains a glob wildcard")
    check("sort -t." in cmd16 and "-k1,1n" in cmd16, "versioned command sorts versions numerically, not lexically")
    check("0.37.0" not in cmd16, "versioned command does not hardcode the literal version number")

    literal_target = "/home/u/dev/checkout/planning/skills/executing-plans/scripts/statusline-chain.sh"
    cmd16b, mode16b = mod.resolve_command(literal_target)
    check(mode16b == "literal", "path outside the plugins/cache layout resolves to literal mode")
    check(cmd16b == f'bash "{literal_target}"', 'literal command is exactly bash "<path>"')

    # numeric field sort, not lexical sort: 0.37.0 must be picked over 0.9.0 (lexically
    # "0.37.0" < "0.9.0" since '3' < '9', which would wrongly pick 0.9.0).
    vtmp = Path(mkdtemp(prefix="statusline-resolve-version-test-"))
    vbase = vtmp / "plugins" / "cache" / "mkt" / "planning"
    for v, tag in [("0.9.0", "V0.9.0"), ("0.37.0", "V0.37.0")]:
        d = vbase / v / "scripts"
        d.mkdir(parents=True)
        stub = d / "statusline-chain.sh"
        stub.write_text(f'#!/bin/bash\nprintf "{tag}"\n')
        os.chmod(stub, 0o755)
    probe_target = str(vbase / "0.9.0" / "scripts" / "statusline-chain.sh")
    cmd16c, mode16c = mod.resolve_command(probe_target)
    check(mode16c == "versioned", "probe target resolves to versioned mode")
    proc16 = subprocess.run(cmd16c, shell=True, capture_output=True, text=True)
    check(proc16.returncode == 0, "versioned command exits 0")
    check(proc16.stdout == "V0.37.0",
          f"version sort picks the highest version 0.37.0 over 0.9.0, not the lexical max (got {proc16.stdout!r})")

    print()
    case_space_in_path()
    case_apostrophe_in_path()
    case_bom_settings()
    case_backup_atomic_and_pruned()
    case_hardlinked_settings()
    case_remove_ownership_gate()
    case_repair_preserves_base()
    case_remove_restores_base()
    case_doubled_bar_refused()
    case_is_ours_is_structural()
    case_non_dict_statusline()
    case_non_utf8_settings()

    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
