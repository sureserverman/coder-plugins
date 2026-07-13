"""Shared frontmatter-scanning primitives for the marketplace context-budget
lane. Both scripts/check-frontmatter-budget.py and scripts/build-capability-index.py
import from here so the rules that must agree — which files are components, what
is excluded, where the frontmatter block is, and whether a component is
dispatch-only — are defined in exactly one place.

Stdlib-only, so the budget script keeps running without PyYAML (the index
generator hard-requires PyYAML for its own name/description/model parsing, but
none of the shared helpers below need it).
"""
import re

# Component globs, relative to the repo root, and the path segments that mark
# test data rather than shipped components. Identical rules must govern every
# tool that reasons about "the set of marketplace components".
PATTERNS = (
    ("skill", "*/skills/*/SKILL.md"),
    ("agent", "*/agents/*.md"),
    ("command", "*/commands/*.md"),
)
EXCLUDE_SEGMENTS = ("/tests/", "/fixtures/")


def frontmatter_block(text):
    """Return the raw YAML frontmatter block (between the leading `---` fences),
    or None when the text has no frontmatter."""
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    return m.group(1) if m else None


def is_excluded(rel_path):
    """True when a repo-relative path is test data (under tests/ or fixtures/)
    and must not be treated as a shipped component."""
    norm = "/" + rel_path.replace("\\", "/")
    return any(seg in norm for seg in EXCLUDE_SEGMENTS)


def disable_model_invocation(text):
    """True when the frontmatter sets `disable-model-invocation: true`. Such a
    component's description is NOT injected into session context (Claude Code
    omits it), so it costs nothing against the always-on footprint even though
    it still ships and is user-/dispatch-invocable.

    Recognizes exactly the authored convention `true`/`false` (case-insensitive,
    quote-tolerant), NOT YAML-1.1's wider truthy set (`yes`/`on`/…). A single
    regex rule keeps the answer independent of PyYAML availability and identical
    across every tool that reads the flag — no cross-script or cross-environment
    divergence.
    """
    fm = frontmatter_block(text)
    if fm is None:
        return False
    m = re.search(r"^disable-model-invocation:[ \t]*(\S+)", fm, re.M)
    return bool(m) and m.group(1).strip().strip("'\"").lower() == "true"
