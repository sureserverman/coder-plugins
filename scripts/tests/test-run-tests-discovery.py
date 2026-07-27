#!/usr/bin/env python3
"""Discovery contract for scripts/run-tests.sh.

BL-020 was not "the bash suite is missing from the runner" — it was "the runner's
notion of what a suite is cannot grow". A runner that happens to find today's
suites proves nothing about the next one, in a new home or a new language, which is
exactly how the original gap appeared: the Preflight glob enumerated two
directories and one extension, so a bash suite added to a third directory was
invisible and silently skipped.

So these pin discovery itself, not a suite count:

  * every test-*.py / test-*.sh on disk appears in `run-tests.sh --list`, walked
    independently of the runner rather than by re-using its own glob;
  * a suite planted in a directory the runner has never seen is still discovered
    (the generality claim — this is the assertion that would have caught BL-020);
  * a planted .sh in a .py-only tree is discovered (the cross-language claim);
  * the comparison has teeth: a listing with one path withheld is reported as a
    discrepancy, so a passing run means agreement and not a vacuous match;
  * --list is side-effect free (it must not execute the suites it names);
  * an unknown argument is rejected rather than silently treated as a full run.

No pytest. Plain assertions, non-zero exit on failure.
Run: python3 scripts/tests/test-run-tests-discovery.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUNNER = ROOT / "scripts" / "run-tests.sh"

fails: list[str] = []


def chk(cond, msg):
    if not cond:
        fails.append(msg)
    print(f"  {'ok' if cond else 'FAIL'}: {msg}")


def listing() -> set[str]:
    """Suite paths the runner reports, as a set of repo-relative strings.

    Deliberately NOT check=True: a nonzero --list (the runner refusing because of an
    unsupported suite, an unreadable subtree, or leftover state from an interrupted
    run) would raise CalledProcessError and abort the whole file with a traceback,
    which is precisely the unstructured failure this suite's own reporting discipline
    exists to avoid. Return the empty set and let the caller's chk() report it.
    """
    out = subprocess.run(
        ["bash", str(RUNNER), "--list"],
        capture_output=True, text=True, cwd=ROOT)
    if out.returncode != 0:
        chk(False, f"--list exited {out.returncode}: {(out.stderr or out.stdout).strip()[:160]}")
        return set()
    return {line.strip() for line in out.stdout.splitlines() if line.strip()}


def walk_disk() -> set[str]:
    """Every suite file on disk, walked WITHOUT re-using the runner's glob.

    Deliberately an independent implementation: a test that asked the runner what
    it found and then checked the runner found it would pass no matter how narrow
    the runner's discovery became.
    """
    found = set()
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in {".git", "node_modules"}]
        for fn in filenames:
            if fn.startswith("test-") and (fn.endswith(".py") or fn.endswith(".sh")):
                found.add(str(Path(dirpath, fn).relative_to(ROOT)))
    return found


print("group 1 — every suite on disk is discovered")
disk = walk_disk()
listed = listing()
missing = sorted(disk - listed)
extra = sorted(listed - disk)
chk(not missing, f"no suite on disk is absent from --list (missing: {missing or 'none'})")
chk(not extra, f"--list names nothing that is not on disk (extra: {extra or 'none'})")
chk(len(disk) > 0, f"the walk found suites at all ({len(disk)} on disk)")

print("group 2 — discovery generalizes to homes and languages the runner has never seen")
planted_dir = ROOT / "tools" / "experimental" / "tests"
planted_sh = planted_dir / "test-planted-generality.sh"
planted_py = ROOT / "android-dev" / "tests" / "test-planted-crosslang.py"
created_roots = []
try:
    if not (ROOT / "tools").exists():
        created_roots.append(ROOT / "tools")
    if not (ROOT / "android-dev" / "tests").exists():
        created_roots.append(ROOT / "android-dev" / "tests")
    planted_dir.mkdir(parents=True, exist_ok=True)
    planted_py.parent.mkdir(parents=True, exist_ok=True)
    planted_sh.write_text("#!/usr/bin/env bash\nexit 0\n")
    planted_py.write_text("import sys\nsys.exit(0)\n")

    after = listing()
    rel_sh = str(planted_sh.relative_to(ROOT))
    rel_py = str(planted_py.relative_to(ROOT))
    chk(rel_sh in after, f"a .sh suite in an unseen directory is discovered ({rel_sh})")
    chk(rel_py in after, f"a .py suite in a bash-only plugin tree is discovered ({rel_py})")

    print("group 3 — the comparison has teeth (against a real listing, not set algebra)")
    # The previous form asserted `bool((after - (after - {x})) - set())`, which is an
    # identity: true for any set containing x, and therefore a restatement of group 2
    # rather than a test. It never re-invoked the runner. This deletes the planted file
    # from DISK and re-reads the runner's actual output.
    planted_sh.unlink()
    after_removal = listing()
    chk(rel_sh not in after_removal,
        "a suite deleted from disk disappears from a FRESH --list invocation")
    chk(rel_py in after_removal,
        "and its sibling is still listed, so the drop was specific, not a wholesale failure")
    planted_sh.write_text("#!/usr/bin/env bash\nexit 0\n")
    chk(rel_sh in listing(), "restoring the file brings it back — discovery is live, not cached")
finally:
    for p in (planted_sh, planted_py):
        if p.exists():
            p.unlink()
    for d in (planted_dir, planted_py.parent):
        if d.exists() and not any(d.iterdir()):
            d.rmdir()
    for r in created_roots:
        if r.exists() and not any(r.iterdir()):
            r.rmdir()
    if (ROOT / "tools" / "experimental").exists() and not any((ROOT / "tools" / "experimental").iterdir()):
        (ROOT / "tools" / "experimental").rmdir()
    if (ROOT / "tools").exists() and not any((ROOT / "tools").iterdir()):
        (ROOT / "tools").rmdir()

print("group 4 — a suite in an unrunnable language fails loudly, never silently")
# The BL-020 class, generalized: a suite the runner cannot execute must not be
# skipped in silence. Planted under a tests/ dir because that is what scopes the
# check away from test-scope-tiers.md and test-fixtures/.
rb = ROOT / "scripts" / "tests" / "test-planted-unrunnable.rb"
try:
    rb.write_text("puts 'hi'\n")
    res = subprocess.run(["bash", str(RUNNER)], capture_output=True, text=True, cwd=ROOT)
    chk(res.returncode != 0, "an unrunnable-language suite makes the runner exit non-zero")
    chk("test-planted-unrunnable.rb" in (res.stderr + res.stdout),
        "the failure names the offending file")
    chk(".py, .sh" in (res.stderr + res.stdout),
        "the failure states which extensions ARE supported")
    res_list = subprocess.run(["bash", str(RUNNER), "--list"],
                              capture_output=True, text=True, cwd=ROOT)
    chk(res_list.returncode != 0, "--list refuses too rather than reporting a clean set")
finally:
    if rb.exists():
        rb.unlink()

print("group 5 — the check does not fire on non-suite paths named test-*")
for benign in ["planning/skills/planning-projects/references/test-scope-tiers.md",
               "planning/skills/applying-design-handoff/scripts/test-fixtures"]:
    chk((ROOT / benign).exists(), f"benign path still present and not swept: {benign}")
chk(subprocess.run(["bash", str(RUNNER), "--list"], capture_output=True,
                   cwd=ROOT).returncode == 0,
    "with only benign test-* paths present, --list succeeds")

print("group 6 — --list is side-effect free and arguments are validated")
# The previous form checked for a sentinel nothing ever wrote, so it passed even if
# --list executed every suite. This plants a suite that DOES write one when run.
#
# It runs in a THROWAWAY tree, never the real repo, for two reasons. Invoking the full
# runner from inside a suite the runner discovers is unbounded recursion (this file ->
# run-tests.sh -> this file -> ...) — found the hard way, the first cut hung until it
# was killed. And a hard kill mid-test leaves planted files behind in the repo under
# test, which is exactly what happened.
with tempfile.TemporaryDirectory() as td:
    tmp = Path(td)
    (tmp / "scripts" / "tests").mkdir(parents=True)
    shutil.copy(RUNNER, tmp / "scripts" / "run-tests.sh")
    sentinel = tmp / "sentinel"
    spy = tmp / "scripts" / "tests" / "test-planted-spy.sh"
    spy.write_text(f"#!/usr/bin/env bash\ntouch '{sentinel}'\nexit 0\n")
    tmp_runner = tmp / "scripts" / "run-tests.sh"

    lst = subprocess.run(["bash", str(tmp_runner), "--list"],
                         capture_output=True, text=True, cwd=tmp)
    chk("scripts/tests/test-planted-spy.sh" in lst.stdout, "the spy suite is discovered")
    chk(not sentinel.exists(),
        "--list did NOT execute the spy suite (sentinel absent after a listing)")
    subprocess.run(["bash", str(tmp_runner)], capture_output=True, text=True, cwd=tmp)
    chk(sentinel.exists(),
        "a full run DOES execute it — proving the sentinel is a live signal, not a dead check")

bad = subprocess.run(["bash", str(RUNNER), "--bogus"],
                     capture_output=True, text=True, cwd=ROOT)
chk(bad.returncode != 0, "an unknown argument exits non-zero rather than running everything")
chk("--bogus" in (bad.stderr + bad.stdout), "the rejection message names the offending argument")

print()
if fails:
    print(f"FAILED — {len(fails)} check(s):")
    for f in fails:
        print(f"  {f}")
    sys.exit(1)
print(f"OK — discovery contract holds across {len(disk)} suite(s).")
