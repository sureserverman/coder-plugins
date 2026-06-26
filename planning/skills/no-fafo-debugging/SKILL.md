---
name: no-fafo-debugging
description: >
  Use at the START of ANY debugging or diagnostic work — before forming theories or proposing
  fixes — not only when tempted by a quick fix. Fires whenever the task is to find out why
  something misbehaves: "debug this", "why is X broken", "fix this bug", "diagnose", "investigate",
  "it's not working", "this is failing", "tests are failing", "flaky test", a stack trace, an
  error message, a crash, a hang or timeout, a regression, or any unexpected behavior. Drives
  evidence-first root-cause analysis AND gathers that evidence autonomously, so the user is pulled
  in only as a last resort.
---

# No-FAFo Debugging

**FAFo = "Fix And Forget"** — the anti-pattern of applying speculative fixes without understanding root cause, then moving on when the symptom disappears.

## When this fires

Any debugging or diagnostic work — the moment a symptom, error, failing test, crash, or "it's not working" shows up. Don't wait until you're about to guess; engage this discipline *first*, before the first hypothesis. If you are investigating why something behaves unexpectedly, you are in this skill.

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

1. **Observe** — read logs, check state, gather evidence *yourself* (see below)
2. **Hypothesize** — form one specific hypothesis based on evidence
3. **Test** — run a single diagnostic command that confirms or refutes
4. **Repeat or fix** — if refuted, form new hypothesis. If confirmed, fix the root cause

## Gather the evidence yourself — don't outsource it to the user

The user is a fallback, not your first instrument. Default to obtaining evidence with your own tools before involving them. Asking the user to fetch what you could have fetched is its own anti-pattern.

**Do this autonomously (no need to ask first — it's read-only or reversible):**
- Read the logs, source, configs, and state directly. Don't ask the user to paste a log when you can open it.
- Run read-only diagnostics yourself: status checks, `grep`/searches, version/health probes, test runs, `--dry-run`, reproductions in a scratch dir.
- Reproduce the failure yourself. A reproduction you control beats a secondhand description.
- Build diagnostic tooling when the evidence isn't lying around: temporary logging, an interceptor/proxy, a protocol decoder, an instrumented build. Capture the *actual* bytes/behavior rather than asking the user what they saw.
- Verify every claim against source or official docs before stating it as fact. If you can't, say "I don't know" and go investigate — don't hand the question back to the user.

**Only escalate to the user when you are genuinely blocked — meaning one of:**
1. **Access you don't have** — a credential, secret, VPN, account, or a machine/log you can't reach.
2. **A world-action only they can do** — plug in a device, power-cycle hardware, click something in a GUI you can't drive, trigger a flow gated behind their identity.
3. **A decision only they can make** — which environment to touch, authorization for a destructive/irreversible step, or a trade-off between valid options.

**When you must escalate, make it cheap for them:** ask once, batched and specific. Name the exact command to run (so they can paste output), the exact file you need, or the exact action — never a vague "what do you see?". Explain why you can't get it yourself, so the ask is obviously necessary. Then resume autonomously with what they return.

## When something "fixes itself"

If an issue disappears without a deliberate fix, that is NOT resolved. Something changed — find what. Common culprits:
- Timeout/retry succeeded on a transient failure
- A background process restarted
- A config file was reloaded
- DNS/routing cache expired
- You changed something else that had a side effect

"It works now" without understanding why is a future outage waiting to happen.
