# Malformed-domain decisions

Fixture register exercising the degrade-never-drop contract. Domain tag: MAL

---

## GDEC-MAL-001 — Entry missing its Reason field

- **Decided:** 2026-07-20
- **Status:** accepted
- **Applies to:**
  - ai-tools/[[fixture-project]] (missing Reason on purpose; DEC-900)

---

## This heading is not a GDEC id at all

- **Decided:** 2026-07-21
- **Status:** accepted
- **Reason:** The heading cannot be parsed as an id, so the block must surface
  flagged rather than vanish — an invisible decision is worse than a malformed one.
- **Applies to:**
  - ai-tools/[[fixture-project]] (unparseable heading on purpose)

---

## GDEC-MAL-002 — Superseded entry stays visible

- **Decided:** 2026-07-01
- **Status:** superseded by GDEC-MAL-001
- **Reason:** Recorded so the digest can prove it marks supersessions rather than
  hiding them; what was believed and why is the record.
- **Applies to:**
  - ai-tools/[[fixture-project]] (supersession fixture)
