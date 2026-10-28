# MHP3rd DLC Localizer — v0.6.1 (test)

- Selected downloadable Palicoes now localize the verified Meowster (original creator/hunter display name) as well as nickname and comment.
- Optional already-recruited promotional copies receive the same approved Meowster display localization, with protected custom owner fields.
- Credited creator identity unchanged; original writing remains in verified recovery ZIP backup. Names follow an explicit, documented five-entry mapping, including the `ino.` period.
- Review preview shows old and new Meowster names alongside Palico names. HTML report includes proposed creator display text.
- Responsive window sizing, reserved bottom navigation bar, horizontally scrollable review table, scrollable Choose DLC page, browser controls on their own row. No maximized/fixed-resolution requirement.
- Engine retains Analyze fingerprint recheck, source encryption modes, checksum verification, edited-byte allowlist, and backup/rollback logic from v0.6.
- Important change from v0.6: the Meowster display bytes *are intentionally modified when selected*; do not describe them as byte-identical to the original save.
- Remains a Python desktop test release, not a precompiled Windows EXE. In-game save/reload of newly localized Meowster names has not yet been verified.
