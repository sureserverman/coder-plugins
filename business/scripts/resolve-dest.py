#!/usr/bin/env python3
"""resolve-dest — print the global-business.md destination path.

Reuses business-scan.py's load_env() (the sole portfolio-config resolver) so a
missing or malformed portfolio-config/registry yields the same clean
"portfolio not configured: ..." message on stderr with a non-zero exit — never a
raw traceback. This lets biz-portfolio's atomic-write pipeline resolve its
destination without duplicating the resolver convention inline.

Usage: python3 resolve-dest.py   # prints <vault_dir>/Portfolio/global-business.md
"""
import importlib.util
import sys
from pathlib import Path

# Hyphenated sibling filename → importlib. business-scan.py runs nothing at
# import (its main() is __main__-guarded), so importing it is side-effect-free.
_SCAN = Path(__file__).resolve().parent / "business-scan.py"
_spec = importlib.util.spec_from_file_location("business_scan", _SCAN)
_bs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_bs)


def main():
    vault, _projects = _bs.load_env()      # sys.exit(clean msg) if misconfigured
    sys.stdout.write(str(vault / "Portfolio" / "global-business.md") + "\n")


if __name__ == "__main__":
    main()
