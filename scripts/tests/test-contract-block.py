#!/usr/bin/env python3
"""Fixture tests for scripts/_contract_block.py.

This helper exists because three copies of "find the text between two markers" had already
diverged: one grew a duplicate-marker guard after a review found that only the first pair
was ever read, and the other did not — so the same malformed file was a finding in one
validator and invisible in the other. The cases below are the ones that divergence turned
into defects, pinned once so both consumers inherit the same answer.

Stdlib only.
"""
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "_contract_block.py"

spec = importlib.util.spec_from_file_location("cb", SCRIPT)
cb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cb)

O, C = "<!-- x -->", "<!-- /x -->"
FAILURES = []


def check(ok, msg):
    print(f"  {'ok' if ok else 'FAIL'}: {msg}")
    if not ok:
        FAILURES.append(msg)


def main():
    print("_contract_block — extract:")
    body, err = cb.extract(f"a\n{O}\nrule\n{C}\nb\n", O, C)
    check(err is None and body.strip() == "rule", "a well-formed block yields its body")

    _, err = cb.extract("no markers here\n", O, C)
    check(err and err[0] == cb.MISSING, "no markers is NO-CONTRACT-BLOCK")

    _, err = cb.extract(f"{C}\nbody\n{O}\n", O, C)
    check(err and err[0] == cb.MISSING, "CLOSE before OPEN is not a block")

    _, err = cb.extract(f"{O}\none\n{C}\n{O}\ntwo\n{C}\n", O, C)
    check(err and err[0] == cb.DUPLICATE,
          "TWO blocks is DUPLICATE, not silently the first — resolving to the first is "
          "how a second, contradicting block went unchecked")

    _, err = cb.extract(f"{O}\nbody\n", O, C)
    check(err and err[0] == cb.MISSING, "an unclosed block is not a block")

    body, err = cb.extract(f"{O}{C}", O, C)
    check(err is None and body == "",
          "an EMPTY block extracts cleanly — emptiness is the caller's judgment to make, "
          "not a parse error, and both callers do reject it")

    print("_contract_block — span:")
    text = f"line1\n{O}\nrule\n{C}\nafter\n"
    check(cb.span(text, O, C) == (2, 4), "span is 1-indexed and inclusive of both markers")
    check(cb.span("nothing\n", O, C) is None, "no block means no span, not a guessed one")
    check(cb.span(f"{O}\na\n{C}\n{O}\nb\n{C}\n", O, C) is None,
          "a DUPLICATED block yields no span — excluding a guessed range would hide real "
          "findings, which is worse than excluding nothing")

    print("_contract_block — flat:")
    check(cb.flat("a\n  b\n\nc") == "a b c", "whitespace collapses to single spaces")

    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
