# Android decisions

Cross-project decisions binding every Android project in the portfolio.
Domain tag: AND

---

## GDEC-AND-003 — Circuit isolation comes from Orbot per-app mode

- **Decided:** 2026-07-20
- **Status:** accepted
- **Reason:** Owner-match iptables rules need root and break under GrapheneOS
  UID reassignment. Orbot per-app VPN mode is the only rootless mechanism that
  survives profile switches.
- **Applies to:**
  - android/[[multitor-android]] (ships the isolation path; DEC-007)
  - android/[[tens-town]] (no decisions.md — unresolved on purpose)

---

## GDEC-AND-011 — Target SDK tracks latest stable minus one

- **Decided:** 2026-05-10
- **Status:** accepted
- **Reason:** Gives AMO and F-Droid reviewers a settled platform to test on.
- **Applies to:**
  - android/[[multitor-android]] (asymmetric on purpose — no back-link)
