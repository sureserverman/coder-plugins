# Rust decisions

Domain tag: RS

---

## GDEC-RS-001 — GTK4 apps use gtk-rs, never raw FFI

- **Decided:** 2026-04-11
- **Status:** accepted
- **Reason:** Raw FFI reintroduces the lifetime bugs gtk-rs exists to prevent.
- **Applies to:**
  - anon-tools/[[appimage-control]] (GTK4 AppImage manager; DEC-002)
