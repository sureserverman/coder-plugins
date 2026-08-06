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
import glob
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "statusline-install.py"
CHAIN = SCRIPT.parent / "statusline-chain.sh"
EXPECTED_COMMAND = f'bash "{CHAIN}"'

FAILURES = []


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


def main():
    tmp = Path(tempfile.mkdtemp(prefix="statusline-install-test-"))

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
    src = SCRIPT.read_text()
    check("os.replace(" in src, "source uses os.replace() for the swap")
    check("tempfile.mkstemp(" in src and "dir=" in src,
          "source creates its temp file with an explicit same-directory dir=")
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
    vtmp = Path(tempfile.mkdtemp(prefix="statusline-resolve-version-test-"))
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
    if FAILURES:
        print(f"{len(FAILURES)} failure(s):")
        for f in FAILURES:
            print(f"  - {f}")
        sys.exit(1)
    print("all checks passed")


if __name__ == "__main__":
    main()
