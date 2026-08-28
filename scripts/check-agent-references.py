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

WHAT THIS DECIDES, AND WHY IT IS DECIDABLE
------------------------------------------
**The block must be the canonical contract, byte for byte after whitespace flattening.**
Not "a block containing the words confirm and exists" — the canonical text itself, held in
`contracts/reference-resolution.tmpl.md`, with exactly three substitution points:

  {PLUGIN}      the plugin directory the agent lives in, taken from its own path
  {NOUN}        the agent's output noun in the banner (REVIEW, TRANSLATION, ADVICE …),
                constrained to one all-caps word
  {DEPTH_NOTE}  which of three fixed sentences applies, **computed from disk** — whether
                the plugin has `references/` at its root, under `skills/<name>/`, or both

Three earlier cuts of this file tried to infer the contract from prose — first from an
agent's ordinary text, then from tokens inside a delimited block. Reviewers defeated every
one of them, and the last round is the reason this file no longer tries: `confirm the
VARIABLE exists` satisfied a check whose stated purpose was rejecting exactly that; `do not
check that each resolved reference exists` satisfied it too, because presence of a token
cannot distinguish an instruction from its own prohibition; a reversed fallback list passed
by seeding decoy `1.`/`2.` digits in ordinary prose. `honest-gates` § *A test does not
exist until its mutant dies* names the two ways out and only two — make the property
structural, or leave it to review and say so. A **required literal** is the structural one,
and it is available here precisely because these blocks are generated boilerplate rather
than authored prose.

So polarity, subject, order and wording are all decided now, because none of them can vary:
an inverted clause is not the canonical text, and neither is a reworded one.

  NON-CANONICAL-CONTRACT  the block is not the canonical text for this plugin. The report
                          names the first differing run of words in both directions.
  NO-CONTRACT-BLOCK       no `<!-- reference-resolution-contract -->` block at all.
  DUPLICATE-CONTRACT-BLOCK  more than one pair; only one would ever be read.
  RESTATED-CONTRACT       a sentence outside the block uses the contract's own vocabulary
                          without pointing at the block, so it is a second copy of the
                          rules, free to drift from the one that is checked.

The population is every `*/agents/*.md` naming `${CLAUDE_PLUGIN_ROOT}` — enumerated here
rather than hardcoded, so a new agent joins the check by existing. `EXPECTED_AGENTS` guards
the other direction: a population that *shrinks* is a sweep that stopped looking, and only
a floor catches that. Both guards are needed; neither implies the other.

WHAT THIS STILL CANNOT SCREEN, disclosed per DEC-008
----------------------------------------------------
**Whether a dispatched agent follows the block.** Only its live output shows that, and no
static check ever reaches it. Saying so is the rule — claiming more would be the overreach
the banner itself exists to prevent.

**The out-of-block lane decides RESTATEMENT, not compliance, and it is incomplete in one
direction.** Both halves of that matter. It is decidable — "does this sentence contain one
of these fixed strings without also naming the contract" is a substring test, not a reading
of what the sentence means — so it never has to judge whether prose is compliant, which is
the judgment this file may not make. But a second copy of the rules written in entirely
different words carries none of the markers and is not caught. That gap is real and is the
accepted cost of not being noisy: the previous, wider trigger flagged four unrelated
sentences for every genuine site, and a check whose findings are mostly noise is one whose
readers learn to skip it.

**REVOCATION and REFRAMING are not caught at all, and they are a different thing from
paraphrase.** The lane asks whether a sentence restates the contract. It does not ask
whether some other sentence tells the agent to disregard the block ("the boxed rules below
are obsolete"), or wraps it in a frame that neutralises it ("kept only so you can recognise
and ignore it"). Those defeat the contract without restating one word of it, and no
substring test decides them — this is the residue that belongs to review, and it is written
down rather than left for the next reviewer to rediscover.

Read-only. Exit 0 when every in-scope agent carries the canonical block and no sentence
outside it restates the contract's vocabulary without pointing at the block, 1 otherwise.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _contract_block import extract, flat  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CONTRACTS = ROOT / "scripts" / "contracts"

# An agent is in scope when it tells the model to read a plugin-rooted reference. Matched
# on the NAME, not on one spelling of it: `$CLAUDE_PLUGIN_ROOT` without braces reads the
# same variable, and keying the population to `${...}` meant an agent could join the repo
# and miss the sweep entirely while the docstring claimed it joins "by existing".
TRIGGER = "CLAUDE_PLUGIN_ROOT"

OPEN = "<!-- reference-resolution-contract -->"
CLOSE = "<!-- /reference-resolution-contract -->"

# A pinned SET, not a count. A floor of 7 is satisfied by any 7, so removing one agent's
# block and adding one compliant agent kept the number whole and the sweep silent. Naming
# the members makes attrition and substitution both visible, and adding an agent is a
# deliberate one-line edit a reviewer sees.
EXPECTED_AGENTS = (
    "business/agents/market-researcher.md",
    "game-dev/agents/game-design-expert.md",
    "git-github/agents/code-reviewer.md",
    "i18n/agents/translator.md",
    "planning/agents/design-handoff-reproducer.md",
    "release-promo/agents/post-drafter.md",
    "rust-dev/agents/rust-expert.md",
)

# --- the out-of-block lane -------------------------------------------------------------
# What a second resolution site actually does wrong is RESTATE the contract instead of
# pointing at it — that is how `rust-expert` ended up carrying its own copy of the fallback
# rules, free to drift from the block three screens above. Restatement is decidable as a
# substring test, so that is what this lane tests.
#
# The markers are the contract's distinctive vocabulary, chosen because they do not occur
# in ordinary agent prose. Two earlier triggers were tried and both were the wrong
# mechanism: `if … unset` missed "is not set" and "is empty" entirely, and widening to the
# whole negation family flagged four unrelated sentences ("if any required field is
# missing", "installs … if missing") for every real site it found. A check that noisy
# teaches its readers to skip it, which is worse than the gap it closes. `fall back` is
# deliberately NOT a marker: `translator.md` falls back to its own translation after a
# rate-limit, which is nothing to do with reference resolution.
RESTATEMENT_MARKERS = ("dev checkout", "versioned plugin cache", "versioned cache",
                       "DEGRADED")
# The escape, and the form the contract wants: a sentence may name the banner when it
# POINTS AT the block. Single-sourcing is the fix, so it must not be what trips the check.
#
# But the escape is NOT unconditional, which is how the first cut of it failed: a sentence
# reading "for scripts the reference-resolution contract is relaxed — prefer a dev checkout
# over the versioned plugin cache, and never emit a DEGRADED banner" carried the pointer and
# three inversions and passed. A delegating sentence has no reason to restate the fallback
# ARMS — that is the part it is delegating — so naming them revokes the exemption. `DEGRADED`
# is exempt-able because an output-shape section legitimately needs to say where the banner
# goes (post-drafter does exactly that).
DELEGATION = "reference-resolution contract"
UNLAUNDERABLE = ("dev checkout", "versioned plugin cache", "versioned cache")
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def noun_slot():
    return r"(?P<noun>[A-Z]+)"


def depth_variants():
    """{name: sentence} from the canonical depth file, so the three live in one place."""
    out = {}
    for line in (CONTRACTS / "reference-resolution.depth.md").read_text(
            encoding="utf-8").splitlines():
        if ":" in line:
            name, _, text = line.partition(":")
            out[name.strip()] = text.strip()
    return out


def depth_kind(plugin):
    """Which depth sentence is TRUE for this plugin, computed from disk.

    Hand-written, this sentence was pattern-copied onto a plugin whose premise was false
    (`planning` was told it keeps references "at more than one depth"; it has no root
    `references/` at all). Deriving it removes the whole class: the note cannot disagree
    with the tree, because the tree is where it comes from.
    """
    root_refs = (ROOT / plugin / "references").is_dir()
    skill_refs = any((ROOT / plugin / "skills").glob("*/references"))
    if root_refs and skill_refs:
        return "BOTH"
    if skill_refs:
        return "SKILLS_ONLY"
    return "ROOT_ONLY"


def expected_pattern(plugin):
    """The canonical block for this plugin, as a regex with the noun as the only slot."""
    tmpl = (CONTRACTS / "reference-resolution.tmpl.md").read_text(encoding="utf-8")
    note = depth_variants()[depth_kind(plugin)].replace("{PLUGIN}", plugin)
    body = tmpl.replace("{PLUGIN}", plugin)
    body = body.replace("{DEPTH_NOTE}", (" " + note) if note else "")
    parts = flat(body).split("{NOUN}")
    return re.compile(noun_slot().join(re.escape(p) for p in parts)), flat(body)


def first_difference(actual, expected):
    """The first word where the two diverge, with a little context from each side."""
    a, b = actual.split(" "), expected.split(" ")
    for i in range(max(len(a), len(b))):
        if i >= len(a) or i >= len(b) or a[i] != b[i]:
            return (f"at word {i + 1}: block has …{' '.join(a[max(0, i - 4):i + 6]) or '<end>'}… "
                    f"/ canonical has …{' '.join(b[max(0, i - 4):i + 6]) or '<end>'}…")
    return "no textual difference (the noun slot did not match `DEGRADED <ALLCAPS> —`)"


def agents():
    """Every shipped agent markdown, in sorted order."""
    return sorted(p for p in ROOT.glob("*/agents/*.md") if p.is_file())


def out_of_block_sites(raw):
    """(line_no, marker) for each sentence outside the block that restates the contract."""
    out = []
    body, err = extract(raw, OPEN, CLOSE)
    if err is not None:
        return out
    segments = [(0, raw[:raw.index(OPEN)]),
                (raw.index(CLOSE) + len(CLOSE), raw[raw.index(CLOSE) + len(CLOSE):])]
    # Scanned SEPARATELY, and each carries its own offset into `raw`. Concatenating them
    # would put text from before the block next to text from after it; and sharing one
    # offset was the bug that reported every finding at the file's FIRST matching line,
    # sending an author to compliant text and making a real defect look like a failed fix.
    for base, seg in segments:
        pos = 0
        for sentence in SENTENCE_SPLIT.split(seg):
            start = seg.index(sentence, pos)
            pos = start + len(sentence)
            one = flat(sentence)
            launderable = not any(m in one for m in UNLAUNDERABLE)
            if DELEGATION in one and launderable:
                continue                 # points at the block: the form the contract wants
            hit = next((m for m in RESTATEMENT_MARKERS if m in one), None)
            if hit:
                # The marker's OWN offset, not the fragment's. A run of lines with no
                # sentence-ending punctuation between them is one fragment, so reporting
                # its start pointed a reader at the first filler line above the real site
                # — the same "wrong line" defect as the round-1 `raw.index()` bug, one
                # level in. Matched whitespace-flexibly because the fragment is raw text
                # while the marker was found in the flattened copy.
                rx = re.compile(r"\s+".join(re.escape(w) for w in hit.split()))
                m = rx.search(sentence)
                at = start + (m.start() if m else 0)
                out.append((raw.count("\n", 0, base + at) + 1, hit))
    return out


def findings_for(path):
    raw = path.read_text(encoding="utf-8", errors="replace")
    if TRIGGER not in raw:
        return None                      # not in the population
    out = []
    body, err = extract(raw, OPEN, CLOSE)
    if err is not None:
        return [err]

    plugin = path.relative_to(ROOT).parts[0]
    pattern, canonical = expected_pattern(plugin)
    actual = flat(body)
    if not pattern.fullmatch(actual):
        out.append(("NON-CANONICAL-CONTRACT",
                    f"the block is not `contracts/reference-resolution.tmpl.md` rendered "
                    f"for `{plugin}` ({depth_kind(plugin)}) — "
                    f"{first_difference(actual, canonical)}"))

    for line, marker in out_of_block_sites(raw):
        out.append(("RESTATED-CONTRACT",
                    f"line {line}: `{marker}` outside the contract block restates it and "
                    f"is free to drift from it; point at the block by naming the "
                    f"`{DELEGATION}` in the same sentence instead"))
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

    missing = [rel for rel in EXPECTED_AGENTS if rel not in in_scope]
    if missing:
        # A pinned set, not a floor: any seven satisfies a floor of seven, so dropping one
        # agent's block while adding a compliant agent kept the count whole and the sweep
        # silent. Naming the members makes attrition and substitution both visible.
        print(f"FAIL: {len(missing)} expected agent(s) no longer name "
              f"CLAUDE_PLUGIN_ROOT: {', '.join(missing)} — the sweep is wrong, or the "
              f"agent really changed and EXPECTED_AGENTS needs the deliberate edit.",
              file=sys.stderr)
        return 1

    print(f"{len(in_scope)} agent(s) name a plugin-rooted reference; "
          f"{len(problems)} problem(s).")
    print("  (decides the block IS the canonical contract text, and that no sentence "
          "outside it carries the contract's vocabulary without naming it)")
    if problems:
        print("\n".join(problems), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
