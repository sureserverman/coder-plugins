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
ANCHOR = "code-reviewer"
NEAR = 120


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
        if ANCHOR not in line[lo:hi]:
            bad.append((p.relative_to(ROOT).as_posix(), n))
    return bad


def definition_present():
    if not AGENT.exists():
        return False
    t = AGENT.read_text(encoding="utf-8", errors="replace")
    return OPEN in t and CLOSE in t and t.index(OPEN) < t.index(CLOSE)


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
    if not definition_present():
        problems.append(
            f"  {AGENT.relative_to(ROOT).as_posix()}: NO-DEFINITION — no "
            f"`{OPEN}` block; every site points here and would resolve to nothing")

    print(f"{len(found)} (read-only) dispatch site(s); {len(problems)} problem(s).")
    print("  (android-dev's Docker-mount '(read-only)' is a different property and is "
          "deliberately out of scope)")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
