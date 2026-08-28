#!/usr/bin/env python3
"""Every agent that names a `${CLAUDE_PLUGIN_ROOT}` reference can survive it being absent.

DEC-009 has two halves: an agent's reference paths are plugin-rooted, and **a reference
it cannot read is disclosed**. The first half was shipped and the second was left to each
agent's own prose, which drifted — some agents said "say so in your return", some said
nothing, and none of them distinguished the variable being UNSET from the resolved file
being MISSING. That distinction is the whole defect: `${CLAUDE_PLUGIN_ROOT}` points at a
real directory in a partially-installed or superseded plugin cache, so an unset-only check
reports success and the agent proceeds ungrounded, producing output shaped exactly like
the grounded kind.

What it checks, and why each one:

  NO-EXISTENCE-CHECK  the agent's resolution prose covers only the unset case. It must
                      instruct checking that the resolved PATH exists, because "set" and
                      "there" are different facts and only one of them is verified by
                      reading the variable.
  NO-FALLBACK-ORDER   the fallback does not order versioned-cache before dev-checkout, or
                      does not require saying which was used. Order matters: the cache is
                      what the operator is running, so silently preferring a checkout
                      grounds the work in rules that are not in force — and an
                      undisclosed choice between two sources is not reproducible.
  NO-DEGRADED-BANNER  no first-line `DEGRADED <NOUN> —` banner is mandated. A closing
                      caveat is not enough: a degraded run and a complete one are
                      identical in shape, so the disclosure has to arrive before the
                      content or a skimming reader never meets it.

The population is every `*/agents/*.md` naming `${CLAUDE_PLUGIN_ROOT}` — enumerated here
rather than hardcoded, so a new agent joins the check by existing. That is the point: the
one-shot gate sweep this replaces could only ever have covered the seven agents present on
the day it ran, and the defect class is "an agent whose reference went unread", which every
future agent inherits.

**Why a delimited block rather than prose matching.** The first two cuts of this file
tried to infer the contract from an agent's ordinary prose, and a reviewer defeated every
check twice — once with constructed text, once with a decoy sentence *already shipped* in
code-reviewer.md's Protocol 2. That was predictable, and `honest-gates` § "A behavioral
claim is a gate too" already says why: **no validator can decide whether an English
sentence asserts behavior.** Hardening the regexes buys one evasion class per round.

So the property was made decidable instead. Each in-scope agent carries the contract inside
`<!-- reference-resolution-contract -->` … `<!-- /reference-resolution-contract -->`, and
every check below runs **only on the text between those markers**, with the fallback order
anchored to the enumerated `1.`/`2.` list rather than to first-occurrence-anywhere. A decoy
elsewhere in the file cannot satisfy anything, because nothing outside the block is read.
That is not a stronger regex; it is a smaller question.

**What this still cannot check.** Whether a dispatched agent *follows* the block. Only its
live output shows that. Saying so is the rule — claiming more would be the overreach the
banner itself exists to prevent.

Read-only. Exit 0 when every such agent carries all three, 1 otherwise.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# An agent is in scope when it tells the model to read a plugin-rooted reference.
TRIGGER = "${CLAUDE_PLUGIN_ROOT}"

OPEN = "<!-- reference-resolution-contract -->"
CLOSE = "<!-- /reference-resolution-contract -->"

# All matched INSIDE the block only, on whitespace-flattened text (an instruction is a
# sentence, not a line — matching raw text made these checks sensitive to where a
# paragraph happened to wrap).
EXISTENCE_RE = re.compile(
    r"\b(confirm|check|verify|ensure)\b[^.]{0,90}\b(exists?|is there|is present)\b", re.I)
CACHE_ITEM_RE = re.compile(r"1\.[^2]{0,120}?versioned\s+\**plugin cache\**", re.I)
CHECKOUT_ITEM_RE = re.compile(r"2\.[^1]{0,120}?\**dev\s+checkout\**", re.I)
SAID_WHICH_RE = re.compile(r"say which (one|arm) you used", re.I)
BANNER_RE = re.compile(r"`?DEGRADED [A-Z]+ —", re.I)
FIRST_LINE_RE = re.compile(r"FIRST[ -]LINE", re.I)

# A resolution site OUTSIDE the block that branches on the variable rather than the file.
# Kept because the block cannot cover a second site elsewhere in the document, and that is
# a real defect this contract has already hit once (rust-expert's script-location block).
UNSET_RE = re.compile(r"\bif\b[^.]{0,60}\bunset\b", re.I)
# Opt-OUT, not opt-in. An earlier cut only treated an out-of-block `if unset` as a
# resolution site when a plugin-root token sat nearby, so a paraphrase ("scripts live in
# the plugin's own directory… if that location variable is unset…") was invisible — the
# exact defect class this contract exists to catch, wearing different words. Now every
# such conditional counts unless it is plainly a parameter default, because a false
# positive is visible and fixable while a false negative is the bug shipping.
PARAM_DEFAULT_RE = re.compile(r"default[^.]{0,60}unset|unset[^.]{0,60}default", re.I)
# Proximity to something that could BE a resolution site. An opt-in on one keyword was
# blind to a paraphrase; no gate at all flagged an unrelated `if LOCALE is unset`. The
# middle is a broad noun set: narrow enough not to fire on unrelated prose, wide enough
# that a paraphrase still lands. Disclosed rather than assumed complete — a resolution
# site phrased without any of these words is not caught, and that is the accepted cost.
RESOLUTION_CTX_RE = re.compile(
    r"CLAUDE_PLUGIN_ROOT|plugin root|plugin's own|reference|script location|"
    r"install location|catalog|rubric|located?\b|find it|glob", re.I)
NEAR = 500


def flat(s):
    """Prose with whitespace collapsed — an instruction is a sentence, not a line."""
    return " ".join(s.split())


ABBREV_RE = r"(?<!\brev)(?<!\bno)(?<!\bvs)(?<!\bcf)(?<!\betc)(?<!\be\.g)(?<!\bi\.e)(?<!\bfig)(?<!\bapprox)"


def sentences(s):
    r"""Sentence split that does not fire on a common abbreviation.

    Two failed attempts are recorded here because each was wrong in an instructive
    direction. A naive `(?<=[.!?])\s+` treats "rev. 2" as a boundary, cutting one
    instruction in half and failing an agent a human reads as compliant. Widening to
    accept ADJACENT sentence pairs fixed that and immediately reopened the hole this
    check exists for — two unrelated sentences in one paragraph are adjacent, so the
    pair carried the banner token and the FIRST-LINE mandate and passed.

    So the boundary itself is made accurate instead: split only where a period is
    followed by whitespace and a capital, and not after a known abbreviation. The unit
    stays exactly one sentence, which is the property.
    """
    return re.split(ABBREV_RE + r"(?<=[.!?])\s+(?=[A-Z`*])", s)


def agents():
    """Every shipped agent markdown, in sorted order."""
    return sorted(p for p in ROOT.glob("*/agents/*.md") if p.is_file())


def findings_for(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    if TRIGGER not in raw:
        return None                      # not in the population
    out = []

    if raw.count(OPEN) > 1 or raw.count(CLOSE) > 1:
        # Only the first pair was ever extracted, so a second block's missing banner or
        # missing order went unchecked entirely. Reported distinctly rather than by
        # silently checking one of them.
        return [("DUPLICATE-CONTRACT-BLOCK",
                 f"{raw.count(OPEN)} open / {raw.count(CLOSE)} close markers; exactly "
                 f"one contract block per agent, or only the first is ever checked")]
    if OPEN not in raw or CLOSE not in raw or raw.index(CLOSE) < raw.index(OPEN):
        return [("NO-CONTRACT-BLOCK",
                 f"no `{OPEN}` … `{CLOSE}` block; the contract is checked only inside "
                 f"it, because prose elsewhere cannot be told from a decoy")]
    block = flat(raw[raw.index(OPEN) + len(OPEN):raw.index(CLOSE)])

    if not EXISTENCE_RE.search(block):
        out.append(("NO-EXISTENCE-CHECK",
                    "the block never instructs confirming the resolved path exists"))
    if not (CACHE_ITEM_RE.search(block) and CHECKOUT_ITEM_RE.search(block)):
        out.append(("NO-FALLBACK-ORDER",
                    "the block's numbered fallback is not `1.` versioned cache then "
                    "`2.` dev checkout"))
    elif not SAID_WHICH_RE.search(block):
        out.append(("NO-FALLBACK-ORDER",
                    "ordered, but the agent is not told to say which arm it used"))
    # One SENTENCE, not one paragraph: a paragraph holds two unrelated sentences, and a
    # FIRST-LINE mandate about something else plus a stray DEGRADED token is the defect.
    if not any(BANNER_RE.search(s) and FIRST_LINE_RE.search(s) for s in sentences(block)):
        out.append(("NO-DEGRADED-BANNER",
                    "no single sentence both names `DEGRADED <NOUN> —` and mandates it "
                    "as the FIRST LINE"))

    # The two segments are scanned SEPARATELY. Concatenating them would place text from
    # before the block adjacent to text from after it, and a proximity window would then
    # read across a gap that does not exist in the document.
    for seg in (raw[:raw.index(OPEN)], raw[raw.index(CLOSE) + len(CLOSE):]):
        for m in UNSET_RE.finditer(seg):
            lo, hi = max(0, m.start() - NEAR), min(len(seg), m.end() + NEAR)
            window = flat(seg[lo:hi])
            if PARAM_DEFAULT_RE.search(flat(seg[max(0, m.start() - 80):m.end() + 60])):
                continue                 # a parameter default, not a resolution site
            if not RESOLUTION_CTX_RE.search(window):
                continue                 # nothing nearby suggests reference resolution
            if not EXISTENCE_RE.search(window):
                line = raw.count("\n", 0, raw.index(m.group(0))) + 1 \
                    if m.group(0) in raw else 0
                out.append(("NO-EXISTENCE-CHECK",
                            f"line {line}: a resolution site OUTSIDE the contract block "
                            f"branches on a variable being unset with no existence "
                            f"check near it"))
    return out


def main():
    in_scope, problems = [], []
    for path in agents():
        found = findings_for(path)
        if found is None:
            continue
        rel = path.relative_to(ROOT).as_posix()
        in_scope.append(rel)
        for code, why in found:
            problems.append(f"  {rel}: {code} — {why}")

    if not in_scope:
        # An empty population is a broken sweep, not a clean bill of health: this
        # repo ships agents that name plugin-rooted references, so zero means the
        # glob or the trigger stopped matching.
        print("FAIL: no agent references ${CLAUDE_PLUGIN_ROOT} — the sweep is wrong, "
              "not the tree.", file=sys.stderr)
        return 1

    print(f"{len(in_scope)} agent(s) name a plugin-rooted reference; "
          f"{len(problems)} problem(s).")
    print("  (checks the instruction is PRESENT and shaped right — not that a "
          "dispatched agent followed it)")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
