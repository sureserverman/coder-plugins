# Decisions

Architectural decisions binding this project, newest first.

---

## DEC-007 — Per-app Tor circuits via Orbot, not iptables owner-match

- **Decided:** 2026-07-20
- **Status:** accepted
- **Domains:** android, tor
- **Source:** sec-audit report `sec-audit-20260720-1830.md` (local-only)
- **Reason:** Owner-match rules need root and break under GrapheneOS per-app
  network policy, which reassigns UIDs on profile switch. Orbot's per-app mode
  gets isolation from the VPN service with no root. Cost: hard Orbot dependency.
- **Global:** [[decisions/android#GDEC-AND-003]]

---

## DEC-006 — Ship a single ABI split per release

- **Decided:** 2026-06-02
- **Status:** superseded by DEC-007
- **Domains:** android
- **Source:** plans/2026-06-01-packaging-plan.md — Stage 2
- **Reason:** F-Droid reproducible builds were failing on universal APKs.

---

## DEC-005 — Malformed on purpose

- **Decided:** 2026-05-01
- **Status:** accepted
