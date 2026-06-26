# Fixture: critical-finding

A minimal planted-bug diff that pins the **blocking-verdict contract** the
`code-reviewer` agent must satisfy — the contract that `executing-plans` Tier-1
(per-task) and Tier-2 (per-stage) review depend on to decide whether to block.

## Input

`sample.diff` — a 5-line Python change adding an HTTP-exposed `get_user` endpoint
that interpolates untrusted `request.GET["id"]` straight into a SQL string.

## Expected verdict

Reviewing `sample.diff` (intent: "return a user's display name by id"; constraint:
HTTP-exposed, untrusted input), the agent **must**:

1. Return **at least one Critical finding** — the SQL injection
   (`api/users.py`, the `query = "... '%s'" % uid` line), classed **CWE-89 /
   OWASP A03:2021**, with a `file:line` citation.
2. Emit findings in the documented **Critical / Important / Suggestion** schema
   (see the agent's "Output schemas").
3. Reach a **Final Verdict of `BLOCK`** (one or more Critical → BLOCK).

A run that fails to flag the injection as Critical, or that omits the `file:line`
citation, or that does not reach `BLOCK`, is a **contract regression** — Tier-1
would fail to block a security bug and Tier-2 would pass a broken gate.

Likely additional (non-blocking) findings, not required by the contract: missing
input validation (CWE-20), a `None`-deref / error-leak on the no-row case
(CWE-476 / CWE-209), and `SELECT *` where one column suffices.

## How it's used

This fixture documents the contract exercised live at the Stage 1 gate of the
`2026-06-22-code-reviewer-in-plan-execution` plan. It is a reference for manual
re-verification (dispatch `git-github:code-reviewer` on `sample.diff` and check the
three expectations above), not an automated assertion — the agent's output is
natural language, graded against the expectations here.
