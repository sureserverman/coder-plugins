#!/usr/bin/env python3
"""Heading extraction for a skill trunk, with fenced code blocks excluded.

Shared by check-extraction-classification.py and check-trunk-retention.py.

A `^#{2,4} ` regex over a SKILL.md does not read markdown, it reads lines — so a
heading inside a ```fence``` counts as a section of the trunk. That is not a
pedantic distinction here. `planning-projects/SKILL.md` shows an author what a
plan's `## Decisions in force` section should look like by printing one inside a
```markdown fence, and a fence-blind scan reports it as the trunk's own heading.

Both guards then go wrong, and neither is recoverable by allowlisting:

  * check-extraction-classification.py demands a classification row for it, so
    the table has to file a decision about a code sample. Worse, the row is a
    time bomb: the day someone edits the example, the row "names no such
    heading" and the guard fails on a change that touched nothing real.
  * check-trunk-retention.py reads its binding sections from that same table, so
    it would sweep a section that does not exist and report the count as
    coverage.

The classification is the authority for what may leave a trunk, so it has to
quantify over the trunk's real sections and nothing else.

Why the two callers share this rather than each keeping a copy: they deliberately
keep their own PAIRS lists, because those are policy and may legitimately differ.
Parsing is not policy. Two guards disagreeing about what counts as a heading in
the same file is a silent divergence, and the one that sees fewer headings is the
one that stops guarding.

**Scoped to headings on purpose.** An earlier cut of this module also stripped
fences before the retention check's substring match, reasoning that a marker
should be satisfied by the trunk's prose rather than by a code sample. Measured
against the live table, that broke a legitimate marker: `Step 3.3` pins
`Executor: dispatched — <subagent_type>`, and the trailer shapes are a fenced
block because the rule *is* the literal. A rule may be a code block; only a
heading may not be. So the marker check still reads the whole trunk.

Fence tracking is deliberately simple and matches CommonMark's common case: a
line whose first non-space characters are ``` or ~~~ toggles fenced state. It
does not model info strings, indented code blocks, or differing fence lengths,
because a SKILL.md that needs those has a bigger problem than this parser.
"""
import re

HEADING_RE = re.compile(r"^#{2,4} (.+)$")
_FENCE_RE = re.compile(r"^\s*(```|~~~)")


def headings(text):
    """Every `^#{2,4} ` heading OUTSIDE a fenced block, in document order.

    Returns a list, not a set: a duplicate heading text is itself a finding the
    callers report, and a set would hide it.
    """
    out, in_fence = [], False
    for line in text.split("\n"):
        if _FENCE_RE.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if m:
            out.append(m.group(1).strip())
    return out
