#!/usr/bin/env python3
"""Fixture tests for scripts/check-agent-references.py.

The load-bearing cases are the ones proving the sweep REJECTS. A contract check that
only ever passes certifies that every agent discloses an unread reference while the
eighth agent quietly ships without the banner — the decay check-agent-pins.py exists to
stop, one contract over.

**Half these fixtures are a reviewer's work, not the author's.** Two rounds of review
defeated two cuts of this validator, both of which tried to infer the contract from an
agent's ordinary prose: a section heading passed as an existence instruction, both
fallback arms present passed as ordered, and a `FIRST LINE` mandate about something else
plus a stray `DEGRADED` token passed as a banner. One proof-of-concept used a decoy
sentence *already shipped* in code-reviewer.md. The design changed rather than the
regexes: the contract now lives inside a delimited block and nothing outside it is read,
which is why those evasions are rejected here structurally rather than by a pattern
written to catch each one. Every one of them is kept below as a case, because the next
cut of this file must not quietly reacquire them.

Stdlib only.
"""
import importlib.util
import os
import pathlib
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(os.path.dirname(HERE), "check-agent-references.py")

spec = importlib.util.spec_from_file_location("refs", SCRIPT)
refs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refs)

O, C = refs.OPEN, refs.CLOSE
FAILURES = []


def check(ok, msg):
    print(f"  {'ok' if ok else 'FAIL'}: {msg}")
    if not ok:
        FAILURES.append(msg)


HEAD = "# A\n\nRead `${CLAUDE_PLUGIN_ROOT}/references/y.md`.\n\n"
EXISTENCE = "Confirm each resolved reference exists before relying on it."
ORDER = ("Fall back in this order, and say which one you used:\n\n"
         "1. the **versioned plugin cache** — `Glob` `**/x/*/y`\n"
         "2. a **dev checkout** — `Glob` `**/x/y`\n")
BANNER = ("Open with `DEGRADED REVIEW — what was unread` as the FIRST LINE of your "
          "output.")


def block(existence=EXISTENCE, order=ORDER, banner=BANNER):
    return f"{O}\n{existence}\n\n{order}\n{banner}\n{C}\n"


def codes(tmp, body, name="a.md"):
    p = pathlib.Path(tmp) / name
    p.write_text(body)
    found = refs.findings_for(p)
    return None if found is None else sorted(c for c, _ in found)


def main():
    print("check-agent-references — the population:")
    with tempfile.TemporaryDirectory() as t:
        check(codes(t, "# A\n\nNo plugin-rooted reference here.\n") is None,
              "an agent naming no ${CLAUDE_PLUGIN_ROOT} reference is out of scope, "
              "not a silent pass")
        check(codes(t, HEAD + block()) == [],
              "a complete contract passes — every rejection below discriminates")
        check(codes(t, HEAD + "Some prose, no block at all.\n") == ["NO-CONTRACT-BLOCK"],
              "an in-scope agent with no contract block is rejected outright")

    print("check-agent-references — each clause, missing from the block:")
    with tempfile.TemporaryDirectory() as t:
        check(codes(t, HEAD + block(existence="If the variable is unset, use Glob.")) ==
              ["NO-EXISTENCE-CHECK"],
              "an unset-only block is rejected — a set variable pointing at a missing "
              "file is the whole defect")
        check(codes(t, HEAD + block(order="Fall back however you like.")) ==
              ["NO-FALLBACK-ORDER"],
              "a block with no enumerated fallback is rejected")
        check(codes(t, HEAD + block(order=ORDER.replace(
                  "Fall back in this order, and say which one you used:",
                  "Fall back in this order:"))) == ["NO-FALLBACK-ORDER"],
              "ordered but never told to say WHICH arm it used is rejected")
        check(codes(t, HEAD + block(banner="If a reference was unread, note it at the "
                                           "end of your report.")) ==
              ["NO-DEGRADED-BANNER"],
              "a closing caveat instead of a first-line banner is rejected")

    print("check-agent-references — the reviewer's evasions, kept as cases:")
    with tempfile.TemporaryDirectory() as t:
        # 1. A decoy existence sentence outside the block. The PoC for this used text
        #    already shipped in code-reviewer.md's Protocol 2 — not a contrived string.
        body = (HEAD + "Check that the files the plan implies exist.\n\n"
                + block(existence="If the variable is unset, use Glob."))
        check(codes(t, body) == ["NO-EXISTENCE-CHECK"],
              "a decoy existence sentence OUTSIDE the block cannot satisfy the check — "
              "nothing outside the block is read")

        # 2. A second resolution site that paraphrases the location, naming no
        #    plugin-root token. An opt-in keyword scan was blind to exactly this.
        body = (HEAD + block() + "\n" + ("Filler.\n\n" * 40) +
                "Scripts live in the plugin's own directory. If that location variable "
                "is unset, locate it once with find.\n")
        check(codes(t, body) == ["NO-EXISTENCE-CHECK"],
              "a PARAPHRASED second resolution site is still caught — the scan is "
              "opt-out, so a defect does not escape by avoiding a keyword")

        # 3. A decoy mention of the cache preceding a genuinely reversed list. First
        #    occurrence anywhere used to win the position comparison.
        body = (HEAD + block(order=(
            "This one does not silently trust the versioned plugin cache.\n\n"
            "Fall back in this order, and say which one you used:\n\n"
            "1. a **dev checkout** — `Glob` `**/x/y`\n"
            "2. the **versioned plugin cache** — `Glob` `**/x/*/y`\n")))
        check(codes(t, body) == ["NO-FALLBACK-ORDER"],
              "a decoy cache mention before a REVERSED list is rejected — the order is "
              "anchored to the enumerated items, not to first occurrence")

        # 4. Both tokens in one paragraph, two unrelated sentences.
        body = (HEAD + block(banner=(
            "Keep your commit subject as the FIRST LINE under 70 chars. Avoid vague "
            "words like `DEGRADED REVIEW — x` in chat.")))
        check(codes(t, body) == ["NO-DEGRADED-BANNER"],
              "same paragraph, different sentences is rejected — the unit is the "
              "sentence, because a paragraph holds unrelated ones")

        # 5. ...and the false-positive guard, which is what keeps 2 honest.
        body = (HEAD + block() + "\n" + ("Filler.\n\n" * 40) +
                "Depth is `triage`, `brief` or `deep` — default `triage` if unset.\n")
        check(codes(t, body) == [],
              "an unrelated parameter default is NOT flagged — a checker that fires on "
              "unrelated text teaches its readers to ignore it")

    print("check-agent-references — the live tree:")
    live = [p for p in refs.agents()
            if refs.TRIGGER in p.read_text(encoding="utf-8", errors="replace")]
    check(len(live) >= 7,
          f"the population is enumerated from disk, not hardcoded ({len(live)} agents)")
    bad = {p.name: refs.findings_for(p) for p in live if refs.findings_for(p)}
    check(not bad, f"every shipped in-scope agent satisfies the contract ({bad or 'none'})")

    print()
    if FAILURES:
        print(f"FAIL: {len(FAILURES)} check(s) failed")
        sys.exit(1)
    print("OK")


if __name__ == "__main__":
    main()
