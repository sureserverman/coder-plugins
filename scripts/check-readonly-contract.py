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
this file and its tests quote the term they are about. Both exclusions are named here rather
than left as a silent glob boundary, and the suite asserts each against a fixture root that
actually contains the collision — an earlier version of this paragraph claimed that for both
while only `android-dev/` had a fixture, which is the same overclaim this file exists to
catch, made about itself.

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

**An inversion of `contracts/read-only.md` itself.** The block is pinned to that file, so
this decides they MATCH — not that the canonical text is right. Editing the source and the
copy together is green, and the suite is too, since its fixtures render from the same source.
Inherent to a required literal: it moves the question from "what does this prose mean" to "is
this the agreed text", and whether the agreed text is correct stays a review question. The
compensating control is that it is visible in any diff touching `contracts/`.

**A paraphrase outside `PARAPHRASE_SCOPE`.** That lane reads `git-github/` and
`planning/skills/executing-plans/` — the agent and the dispatchers. A competing definition
written in a third plugin is not seen. Named because the first cut read one directory and
said nothing about it, which reads as "no paraphrase ships" rather than "none ships here".

**An untracked dispatch site.** The population is `git ls-files`, so a new site in a file
nobody has staged yet is invisible until it is added. The sibling validator walks the tree
instead, so the two disagree about untracked files by design: this one describes what
ships, and a `(read-only)` claim only binds once it is in the tree.

Read-only. Exit 0 when every site points, the definition is canonical, and no paraphrase
competes with it. Exit 1 otherwise — and also, before any problem is computed, when a member
of `EXPECTED_SITES` has stopped carrying one, or when the population cannot be enumerated at
all (BLOCKED: a sweep that cannot run has no verdict to give).
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _contract_block import extract, span, flat  # noqa: E402

class SweepUnavailable(RuntimeError):
    """The population could not be enumerated — a BLOCKED sweep, not a clean tree."""


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

# {N_SITES} renders a sentence that says "dispatch sites in `executing-plans`", so it is
# counted over THAT directory alone. The orphan sweep stays repo-wide: those are different
# questions, and conflating them meant a site added in git-github/ either inflated a
# sentence about executing-plans or forced an author to write a false number to go green.
COUNTED_DIR = "planning/skills/executing-plans/"

# A pinned SET, not a floor: any six satisfies a floor of six, so a site deleted here and
# one added there keeps the number whole and the sweep silent.
EXPECTED_SITES = (
    "planning/skills/executing-plans/SKILL.md",
    "planning/skills/executing-plans/references/close-out.md",
    "planning/skills/executing-plans/references/integration.md",
    "planning/skills/executing-plans/references/light-plans.md",
    "planning/skills/executing-plans/references/stage-gate.md",
    "planning/skills/executing-plans/references/task-execution.md",
)

# Narrower restatements of the contract. Each is a literal that shipped, or the shape one
# shipped in. Matched outside the canonical block only — the block is allowed to define the
# thing it defines.
RESTATED_PARAPHRASES = (
    "never edits, commits, or merges",
    "no write tools",
    "no Edit/Write tools",
)
PARAPHRASE_SCOPE = ("git-github/", "planning/skills/executing-plans/")

WORD_NUMBERS = {1: "One", 2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six",
                7: "Seven", 8: "Eight", 9: "Nine", 10: "Ten", 11: "Eleven",
                12: "Twelve"}


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
        try:
            out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z", "*.md"],
                                 capture_output=True, text=True, check=True)
        except (OSError, subprocess.CalledProcessError) as exc:
            # A traceback is not a verdict. The sweep cannot run, so say that and let the
            # caller fail loudly rather than crashing mid-enumeration.
            raise SweepUnavailable(f"`git ls-files` failed: {exc}") from exc
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
            if n in skip:
                continue
            # Every occurrence, not the first: two dispatch sites on one line would be
            # two sites. No line in the tree carries two today — the reason to handle it
            # is that the population has ~1,000-char single lines (`SKILL.md:467` is 1,005)
            # where a second dispatch is entirely plausible.
            for m in READONLY_RE.finditer(line):
                out.append((rel, n, line, m.start()))
    return out


def orphans():
    bad = []
    for rel, n, line, at in sites():
        lo, hi = max(0, at - NEAR), min(len(line), at + len("(read-only)") + NEAR)
        if not re.search(r"\b" + re.escape(ANCHOR) + r"\b", line[lo:hi]):
            bad.append((rel, n))
    return bad


def definition_problems(n_sites):
    """[] if the agent carries the canonical definition, else (code, why) for each reason.

    NO-DEFINITION and STALE-SITE-COUNT are separated because they call for opposite
    actions: one says the pointer resolves to nothing, the other says it resolves to a
    correct definition whose opening sentence names the wrong number. Reporting the second
    as the first sent a reader looking for a missing block that was there all along.
    """
    if not AGENT.exists():
        return [("NO-DEFINITION", "the agent file does not exist; every site points here "
                                  "and would resolve to nothing")]
    text = AGENT.read_text(encoding="utf-8", errors="replace")
    body, err = extract(text, OPEN, CLOSE)
    if err is not None:
        return [("NO-DEFINITION", f"{err[1]}; every site points here and would resolve to "
                                  f"nothing")]
    expected = CONTRACTS / "read-only.md"
    want = flat(expected.read_text(encoding="utf-8").replace(
        "{N_SITES}", WORD_NUMBERS.get(n_sites, str(n_sites))))
    got = flat(body)
    if got == want:
        return []
    a, b = got.split(" "), want.split(" ")
    only_count = (len(a) == len(b)
                  and sum(1 for x, y in zip(a, b) if x != y) == 1
                  and any(x in WORD_NUMBERS.values() for x, y in zip(a, b) if x != y))
    code = "STALE-SITE-COUNT" if only_count else "NO-DEFINITION"
    for i in range(max(len(a), len(b))):
        if i >= len(a) or i >= len(b) or a[i] != b[i]:
            tail = ("" if only_count else
                    "; every site points here and would resolve to nothing")
            return [(code,
                     f"the block is not `contracts/read-only.md` rendered for {n_sites} "
                     f"executing-plans site(s) — at word {i + 1}: block has "
                     f"…{' '.join(a[max(0, i - 4):i + 6]) or '<end>'}… / canonical has "
                     f"…{' '.join(b[max(0, i - 4):i + 6]) or '<end>'}…{tail}")]
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


def counted_sites(found):
    """The sites the canonical sentence is ABOUT — executing-plans only (see COUNTED_DIR)."""
    return [s for s in found if s[0].startswith(COUNTED_DIR)]


def main():
    try:
        found = sites()
    except SweepUnavailable as exc:
        print(f"BLOCKED: {exc} — the population could not be enumerated, so this "
              f"validator has no verdict to give.", file=sys.stderr)
        return 1
    problems = []

    present = {rel for rel, _, _, _ in found}
    missing = [rel for rel in EXPECTED_SITES if rel not in present]
    if missing:
        # A pinned set, not a floor: substitution keeps a count whole while the sweep goes
        # quiet, so the members are named and their absence is the finding.
        print(f"FAIL: {len(missing)} expected (read-only) site file(s) no longer carry "
              f"one: {', '.join(missing)} — the sweep is wrong, or the site really moved "
              f"and EXPECTED_SITES needs the deliberate edit.", file=sys.stderr)
        return 1

    problems += [f"  {rel}:{n}: ORPHAN-READONLY — '(read-only)' with no `{ANCHOR}` within "
                 f"{NEAR} chars on the same line; the agent name is the pointer to the "
                 f"definition" for rel, n in orphans()]
    problems += [f"  {AGENT_REL}: {code} — {why}"
                 for code, why in definition_problems(len(counted_sites(found)))]
    problems += [f"  {rel}:{n}: RESTATED-CONTRACT — \"{phrase}\" is a narrower second "
                 f"definition, free to drift from the canonical block; point at the block "
                 f"instead" for rel, n, phrase in paraphrases()]

    print(f"{len(found)} (read-only) site(s), {len(counted_sites(found))} of them in "
          f"executing-plans; {len(problems)} problem(s).")
    print("  (decides the block IS `contracts/read-only.md` — not that a dispatched agent "
          "obeyed it; android-dev's Docker-mount '(read-only)' and scripts/ are excluded)")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
