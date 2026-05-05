---
name: no-fafo-debugging
description: >
  Use when debugging any issue, especially when tempted to propose quick fixes without evidence.
  Trigger on "debug this", "why is X broken", "fix this bug", or any diagnostic request where
  the user expects root-cause analysis over speculative patches.
---

# No-FAFo Debugging

**FAFo = "Fix And Forget"** — the anti-pattern of applying speculative fixes without understanding root cause, then moving on when the symptom disappears.

## The rule

Do NOT propose fixes until you can explain:
1. **What** is failing (specific error, symptom, or misbehavior)
2. **Why** it is failing (root cause, not just the symptom)
3. **How** the proposed fix addresses the root cause

If you cannot answer all three, you need more diagnostics, not more guesses.

## What FAFo looks like

- "Try restarting the service" (without knowing why it failed)
- "Maybe change this config value" (without verifying the current value causes the issue)
- "Let's try a different approach" (without understanding why the first one failed)
- Proposing 3 possible fixes and asking which one to try
- A fix "works" but you can't explain why the original behavior occurred

## What correct debugging looks like

1. **Observe** — read logs, check state, gather evidence
2. **Hypothesize** — form one specific hypothesis based on evidence
3. **Test** — run a single diagnostic command that confirms or refutes
4. **Repeat or fix** — if refuted, form new hypothesis. If confirmed, fix the root cause

## When something "fixes itself"

If an issue disappears without a deliberate fix, that is NOT resolved. Something changed — find what. Common culprits:
- Timeout/retry succeeded on a transient failure
- A background process restarted
- A config file was reloaded
- DNS/routing cache expired
- You changed something else that had a side effect

"It works now" without understanding why is a future outage waiting to happen.
