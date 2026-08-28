#!/usr/bin/env python3
"""Every "(read-only)" dispatch site points at a definition that exists.

`executing-plans` calls `git-github:code-reviewer` "(read-only)" at six sites. Until this
check existed the word had no definition anywhere in the repo, so it meant whatever each
reader assumed — and the readers are dispatched agents, which is the worst case for an
assumed convention. A reviewer that writes a report beside the code makes its caller's
next `git status` ambiguous at exactly the moment the caller is deciding whether the tree
is clean enough to quote a gate result from.

What it checks, and why each one:

  ORPHAN-READONLY   a "(read-only)" dispatch site that does not name the agent whose
                    definition governs it. The sites already read
                    `git-github:code-reviewer (read-only)`, so the pointer is the agent
                    name — this keeps it that way rather than letting a site drift into
                    an unanchored adjective.
  NO-DEFINITION     the agent named by those sites carries no
                    `<!-- read-only-contract -->` block. The pointer resolving to nothing
                    is the same defect as no pointer.

**Why a delimited block, and why adjacency rather than prose.** `honest-gates` § "A test
does not exist until its mutant dies" opens with the rule that decided this file's shape:
before writing a checker, ask whether the mechanism can decide the property. "Does this
paragraph define read-only?" is a question about meaning and no pattern can answer it.
"Is this occurrence within N characters of the agent name, and does that agent carry a
delimited contract block?" is structural, and it is the same question for practical
purposes — a site that names the agent has pointed, and a block that exists has defined.
Sibling: `check-agent-references.py`, which reached the same shape the expensive way.

**Scope, and what is deliberately outside it.** The population is `(read-only)` inside
`planning/skills/executing-plans/` and `git-github/agents/` — dispatch sites and the agent
they name. `android-dev/README.md` and `android-dev/infrastructure/README.md` also say
"(read-only)", about a **Docker bind mount**. Same two words, unrelated property, and
sweeping them in would produce findings nobody can act on — which is how a check teaches
its readers to skip it. Recorded here rather than left as a silent glob boundary.

Also outside it, and named for the same reason: three plugin READMEs describe this agent
as read-only in prose without the literal parenthetical — `git-github/README.md`,
`planning/README.md`, `testing/README.md`. They DESCRIBE the property to a human reader;
they do not dispatch, so they cannot orphan a pointer. `git-github/README.md` used to
restate the contract in its own narrower words ("never edits, commits, or merges"), which
is a second definition free to drift; it now points at the canonical block instead. The
other two only name the property in passing and are left alone.

Read-only. Exit 0 when every site points and the definition exists, 1 otherwise.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SITE_DIRS = ("planning/skills/executing-plans", "git-github/agents")
AGENT = ROOT / "git-github" / "agents" / "code-reviewer.md"

READONLY_RE = re.compile(r"\(read-only\)", re.I)
OPEN, CLOSE = "<!-- read-only-contract -->", "<!-- /read-only-contract -->"
# The pointer is the agent's name sitting next to the adjective. 120 chars is one clause
# either side — wide enough for "dispatch `git-github:code-reviewer` (read-only) as a
# fresh dispatch", narrow enough that a mention elsewhere in the paragraph does not count.
ANCHOR_RE = re.compile(r"\bcode-reviewer\b")
ANCHOR = "code-reviewer"
NEAR = 120

# The obligations the block must actually state. Presence-checked inside the delimited
# block only — the same shape as check-agent-references.py, and for the same reason: the
# question "does this paragraph define read-only" is about meaning and undecidable, while
# "does the block name each obligation" is structural. An earlier cut checked only that
# the two markers existed and were ordered, so an EMPTY block passed — the exact "pointer
# resolving to nothing" this file's docstring says it exists to catch, in the one place
# nobody thought to look.
OBLIGATIONS = {
    "create": re.compile(r"\bcreate\b", re.I),
    "modify/delete": re.compile(r"\bmodif|\bdelet", re.I),
    "scratchpad": re.compile(r"scratchpad", re.I),
}
MIN_BODY = 200


def sites():
    """(path, line_no, line) for every (read-only) DISPATCH occurrence.

    The contract block's own interior is excluded: the definition quotes the term it
    defines ('six dispatch sites call this agent "(read-only)"'), and a definition is not
    a dispatch site. Without this the block fails the check it exists to satisfy — which
    would be a checker whose only finding is itself.
    """
    out = []
    for d in SITE_DIRS:
        for p in sorted((ROOT / d).rglob("*.md")):
            text = p.read_text(encoding="utf-8", errors="replace")
            lines = text.splitlines()
            skip = set()
            if OPEN in text and CLOSE in text:
                a = text[:text.index(OPEN)].count("\n")
                b = text[:text.index(CLOSE)].count("\n")
                skip = set(range(a + 1, b + 2))          # 1-indexed, inclusive
            for n, line in enumerate(lines, 1):
                if n not in skip and READONLY_RE.search(line):
                    out.append((p, n, line))
    return out


def orphans():
    bad = []
    for p, n, line in sites():
        m = READONLY_RE.search(line)
        lo, hi = max(0, m.start() - NEAR), min(len(line), m.end() + NEAR)
        if not ANCHOR_RE.search(line[lo:hi]):
            bad.append((p.relative_to(ROOT).as_posix(), n))
    return bad


def definition_problems():
    """[] if the agent carries a real definition, else the reasons it does not.

    Markers present and ordered is NOT a definition. An empty block satisfied the first
    cut of this check, which made it a pointer-check whose own pointer could resolve to
    nothing — the failure it was written to prevent, one level up.
    """
    if not AGENT.exists():
        return ["the agent file does not exist"]
    t = AGENT.read_text(encoding="utf-8", errors="replace")
    if not (OPEN in t and CLOSE in t and t.index(OPEN) < t.index(CLOSE)):
        return [f"no `{OPEN}` … `{CLOSE}` block"]
    body = t[t.index(OPEN) + len(OPEN):t.index(CLOSE)].strip()
    out = []
    if len(body) < MIN_BODY:
        out.append(f"the block holds {len(body)} chars; a definition is not two markers "
                   f"with nothing between them")
    missing = [name for name, rx in OBLIGATIONS.items() if not rx.search(body)]
    if missing:
        out.append(f"the block never states: {', '.join(missing)}")
    return out


def definition_present():
    return not definition_problems()


def main():
    found = sites()
    if not found:
        # An empty sweep is a broken glob, not a clean tree: executing-plans dispatches a
        # read-only reviewer at six documented sites, so zero means the population moved.
        print("FAIL: no (read-only) dispatch site found — the sweep is wrong, not the "
              "tree.", file=sys.stderr)
        return 1

    problems = [f"  {rel}:{n}: ORPHAN-READONLY — '(read-only)' with no `{ANCHOR}` within "
                f"{NEAR} chars; the agent name is the pointer to the definition"
                for rel, n in orphans()]
    for why in definition_problems():
        problems.append(
            f"  {AGENT.relative_to(ROOT).as_posix()}: NO-DEFINITION — {why}; every site "
            f"points here and would resolve to nothing")

    print(f"{len(found)} (read-only) dispatch site(s); {len(problems)} problem(s).")
    print("  (android-dev's Docker-mount '(read-only)' is a different property and is "
          "deliberately out of scope)")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
