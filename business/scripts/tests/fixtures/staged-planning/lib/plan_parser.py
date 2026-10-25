"""A stand-in for staged-planning's lib/plan_parser.py: only the two regexes business-scan reads.

Copied from staged-planning plugins/claude/planning/lib/plan_parser.py (v1.0.1; unchanged in v1.0.2), so the gtm
cases run without an installed planning plugin. STAGED_PLANNING_ROOT points at this folder.
"""
import re

UNCHECKED = re.compile(r"^\s*-\s*\[ \]\s+(.+)$")
CHECKED = re.compile(r"^\s*-\s*\[x\]\s+", re.I)
