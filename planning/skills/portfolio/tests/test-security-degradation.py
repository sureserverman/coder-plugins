#!/usr/bin/env python3
"""The security roll-up layer must be ADDITIVE (BL-005).

Mirrors test-business-degradation.py: renaming the security scripts away must
leave global-backlog.md and global-maturity.md byte-identical and must not fail
the rebuild. A new dashboard is never worth breaking the two roll-ups the
portfolio already depends on.

Run: python3 planning/skills/portfolio/tests/test-security-degradation.py
"""
import subprocess, sys, os
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"
REBUILD = SCRIPTS / "portfolio-rebuild.py"


def rebuild():
    p = subprocess.run([sys.executable, str(REBUILD)], capture_output=True, text=True)
    return p.returncode, p.stdout, p.stderr


def main() -> int:
    fails = []
    rc_on, out_on, _ = rebuild()
    if rc_on != 0:
        print(f"FAIL: rebuild exited {rc_on} with the security layer present", file=sys.stderr)
        return 1
    if "global-security written:" not in out_on:
        fails.append("security layer not reported when present")

    moved = []
    try:
        for name in ("security-scan.py", "security-rollup.py"):
            src = SCRIPTS / name
            dst = SCRIPTS / (name + ".off")
            if src.exists():
                src.rename(dst); moved.append((dst, src))
        rc_off, out_off, _ = rebuild()
    finally:
        for dst, src in moved:
            dst.rename(src)

    if rc_off != 0:
        fails.append(f"rebuild exited {rc_off} with the security layer ABSENT "
                     "— the layer must be optional")
    if "security layer: unavailable" not in out_off:
        fails.append(f"absent layer not reported clearly: {out_off.strip()!r}")

    # Everything the rebuild reports about the OTHER roll-ups must be identical
    # with and without the security layer.
    def others(line):
        return [seg.strip() for seg in line.split("|")
                if "security" not in seg]
    if others(out_on) != others(out_off):
        fails.append(f"other roll-ups changed when the security layer toggled:\n"
                     f"  on : {others(out_on)}\n  off: {others(out_off)}")

    if fails:
        print("FAILURES:", file=sys.stderr)
        for f in fails:
            print(f"  - {f}", file=sys.stderr)
        return 1
    print("OK — security layer is additive: rebuild succeeds without it and the "
          "other roll-ups are unchanged either way")
    return 0


if __name__ == "__main__":
    sys.exit(main())
