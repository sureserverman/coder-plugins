#!/usr/bin/env python3
"""Every "(read-only)" dispatch site points at one definition, and that definition is real.

Six sites in `executing-plans` dispatch `git-github:code-reviewer (read-only)`. The word
was a convention with no definition anywhere, so it meant whatever each reader assumed —
and the readings differ in the way that matters: "does not edit the files under review" and
"creates nothing in the tree under review" are not the same rule, and only the second one
keeps a reviewer's scratch file out of the caller's `git status` mid-gate.

This binds the two halves that a convention leaves unbound:

  ORPHAN-READONLY   a site says "(read-only)" without naming the agent whose block defines
                    it, so the pointer resolves to nothing.
  NO-DEFINITION     the agent carries no canonical definition for the pointer to reach.
  RESTATED-CONTRACT a narrower paraphrase of the contract lives outside the block, free to
                    drift from it. `git-github/README.md` carried two ("never edits,
                    commits, or merges" — which permits *creating* a report, the one thing
                    the definition singles out), and the agent itself carried a third that
                    was flatly false against its own frontmatter ("no write tools by
                    design", with an unrestricted `Bash` grant).

WHAT THIS DECIDES, AND WHY IT IS DECIDABLE
------------------------------------------
**The block must be the canonical text**, held in `contracts/read-only.md`, with one
substitution point — `{N_SITES}`, rendered from the count this script computes, so the
sentence "Six dispatch sites …" cannot go stale while the validator that knows better
prints the true number and says nothing.

The previous cut checked that the block existed and named three obligation keywords. That
is a meaning test wearing a keyword's clothes, and it failed the way meaning tests fail: a
block saying *"You may freely create files anywhere in the target tree… You may modify and
delete whatever you like… Do NOT use the session scratchpad"* contains `create`, `modify`,
`scratchpad`, is over the length floor, and passed — the definition inverted, the check
green. `honest-gates` § *A test does not exist until its mutant dies* allows exactly two
ways out; the required literal is the structural one, and it is available because this
block is one canonical text rather than seven authored ones.

**The population is swept from the whole repo**, not from a hardcoded directory list. The
previous cut walked two directories, so a seventh dispatch site added in
`git-github/skills/code-review/` — a file that really does dispatch this agent — would have
been invisible while the printed count still said six. `EXPECTED_SITES` guards the opposite
direction: a population that shrinks is a sweep that stopped looking.

**Scope, and what is deliberately outside it.** `android-dev/README.md` and
`android-dev/infrastructure/README.md` say "(read-only)" about a **Docker bind mount** —
same two words, unrelated property, and sweeping them in would produce findings nobody can
act on, which is how a check teaches its readers to skip it. `scripts/` is excluded because
this file and its tests quote the term they are about. Both exclusions are named here
rather than left as a silent glob boundary, and both are asserted by the test suite against
a fixture root that actually contains them.

WHAT THIS CANNOT SCREEN, disclosed per DEC-008
-----------------------------------------------
**Whether a dispatched agent obeys the block.** Only its live output shows that.

**Whether an occurrence is a dispatch or a mention.** The pointer test is "the agent's name
within one clause", which a sentence merely *discussing* the agent also satisfies. The
consequence is bounded and in the safe direction: a mention gets held to the same pointer
rule a dispatch is, which costs a few words and misleads nobody.

**A paraphrase written in words this file does not list.** `RESTATED_PARAPHRASES` is a
literal set — decidable, and incomplete by construction. It catches the three that shipped
and the shapes they belong to, not every sentence someone could write.

Read-only. Exit 0 when every site points, the definition is canonical, and no paraphrase
competes with it, 1 otherwise.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _contract_block import extract, span, flat  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "scripts" / "contracts"

AGENT_REL = "git-github/agents/code-reviewer.md"
AGENT = ROOT / AGENT_REL

READONLY_RE = re.compile(r"\(read-only\)", re.I)
OPEN, CLOSE = "<!-- read-only-contract -->", "<!-- /read-only-contract -->"

# Documented above. Kept as path prefixes so the exclusion is checkable by reading it.
EXCLUDED_PREFIXES = ("android-dev/", "scripts/")

ANCHOR = "code-reviewer"
NEAR = 120

EXPECTED_SITES = 6

# Narrower restatements of the contract. Each is a literal that shipped, or the shape one
# shipped in. Matched outside the canonical block only — the block is allowed to define the
# thing it defines.
RESTATED_PARAPHRASES = (
    "never edits, commits, or merges",
    "no write tools",
    "no Edit/Write tools",
)
PARAPHRASE_SCOPE = ("git-github/",)

WORD_NUMBERS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six",
                7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten"}


def markdown_files():
    """Every shipped markdown file, as (path, repo-relative posix path).

    TRACKED files only, when the root is a git repo. A local, gitignored artifact is not
    part of the shipped contract: the first repo-wide sweep flagged
    `sec-audit-report-20260428-2015.md`, an untracked local report that says "(read-only)"
    about something else entirely — a finding nobody can act on, in a file that is not in
    the tree this validator describes. Falls back to a plain walk when there is no git
    directory, which is how the fixture roots in the test suite are read.
    """
    if (ROOT / ".git").exists():
        out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "*.md"],
                             capture_output=True, text=True, check=True)
        rels = sorted(r for r in out.stdout.split("\0") if r)
        paths = ((ROOT / r, r) for r in rels)
    else:
        paths = ((p, p.relative_to(ROOT).as_posix()) for p in sorted(ROOT.rglob("*.md")))
    for p, rel in paths:
        if rel.startswith(EXCLUDED_PREFIXES) or "/.git/" in rel:
            continue
        if p.is_file():
            yield p, rel


def sites():
    """(rel, line_no, line) for every (read-only) occurrence in the swept population.

    The canonical block's interior is excluded **for the agent file only**. The definition
    quotes the term it defines, and without the exclusion the sole finding this validator
    ever produced was itself. Scoping it to the agent matters: applied to every file, the
    marker pair became a suppression mechanism — wrapping real dispatch sites in
    `<!-- read-only-contract -->` deleted them from the population silently.
    """
    out = []
    for p, rel in markdown_files():
        text = p.read_text(encoding="utf-8", errors="replace")
        skip = set()
        if rel == AGENT_REL:
            got = span(text, OPEN, CLOSE)
            if got:
                skip = set(range(got[0], got[1] + 1))
        for n, line in enumerate(text.splitlines(), 1):
            if n not in skip and READONLY_RE.search(line):
                out.append((rel, n, line))
    return out


def orphans():
    bad = []
    for rel, n, line in sites():
        m = READONLY_RE.search(line)
        lo, hi = max(0, m.start() - NEAR), min(len(line), m.end() + NEAR)
        if not re.search(r"\b" + re.escape(ANCHOR) + r"\b", line[lo:hi]):
            bad.append((rel, n))
    return bad


def definition_problems(n_sites):
    """[] if the agent carries the canonical definition, else the reasons it does not."""
    if not AGENT.exists():
        return ["the agent file does not exist"]
    text = AGENT.read_text(encoding="utf-8", errors="replace")
    body, err = extract(text, OPEN, CLOSE)
    if err is not None:
        return [err[1]]
    expected = CONTRACTS / "read-only.md"
    want = flat(expected.read_text(encoding="utf-8").replace(
        "{N_SITES}", WORD_NUMBERS.get(n_sites, str(n_sites))))
    got = flat(body)
    if got == want:
        return []
    a, b = got.split(" "), want.split(" ")
    for i in range(max(len(a), len(b))):
        if i >= len(a) or i >= len(b) or a[i] != b[i]:
            return [f"the block is not `contracts/read-only.md` rendered for {n_sites} "
                    f"sites — at word {i + 1}: block has "
                    f"…{' '.join(a[max(0, i - 4):i + 6]) or '<end>'}… / canonical has "
                    f"…{' '.join(b[max(0, i - 4):i + 6]) or '<end>'}…"]
    return []


def paraphrases():
    out = []
    for p, rel in markdown_files():
        if not rel.startswith(PARAPHRASE_SCOPE):
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        skip = set()
        if rel == AGENT_REL:
            got = span(text, OPEN, CLOSE)
            if got:
                skip = set(range(got[0], got[1] + 1))
        for n, line in enumerate(text.splitlines(), 1):
            if n in skip:
                continue
            for phrase in RESTATED_PARAPHRASES:
                if phrase in line:
                    out.append((rel, n, phrase))
    return out


def main():
    found = sites()
    problems = []

    if len(found) < EXPECTED_SITES:
        # Zero is a broken glob; fewer than ship today is a population that quietly lost
        # members, which a zero-check cannot see.
        print(f"FAIL: {len(found)} (read-only) site(s), expected at least "
              f"{EXPECTED_SITES} — the sweep is wrong, not the tree. Lower "
              f"EXPECTED_SITES deliberately if a site was really removed.",
              file=sys.stderr)
        return 1

    problems += [f"  {rel}:{n}: ORPHAN-READONLY — '(read-only)' with no `{ANCHOR}` within "
                 f"{NEAR} chars on the same line; the agent name is the pointer to the "
                 f"definition" for rel, n in orphans()]
    problems += [f"  {AGENT_REL}: NO-DEFINITION — {why}; every site points here and would "
                 f"resolve to nothing" for why in definition_problems(len(found))]
    problems += [f"  {rel}:{n}: RESTATED-CONTRACT — \"{phrase}\" is a narrower second "
                 f"definition, free to drift from the canonical block; point at the block "
                 f"instead" for rel, n, phrase in paraphrases()]

    print(f"{len(found)} (read-only) dispatch site(s); {len(problems)} problem(s).")
    print("  (decides the block IS `contracts/read-only.md` — not that a dispatched agent "
          "obeyed it; android-dev's Docker-mount '(read-only)' and scripts/ are excluded)")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
