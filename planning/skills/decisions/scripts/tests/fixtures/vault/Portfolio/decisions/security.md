# Security decisions

Cross-project decisions binding every project in the portfolio on security
grounds. Domain tag: SEC

---

## GDEC-SEC-001 — Security findings are recorded as decisions; reports stay local

- **Decided:** 2026-07-25
- **Status:** accepted
- **Reason:** sec-audit reports enumerate live weaknesses and are gitignored so they
  never reach a remote, which leaves the constraints they impose with no durable
  home. Projects record the constraint as their own entry, citing the report by
  filename and date only. The register must stay useful to a reader who cannot
  open the report.
- **Applies to:**
  - ai-tools/[[coder-plugins]] (defines the register and the sourcing rule; DEC-001)
