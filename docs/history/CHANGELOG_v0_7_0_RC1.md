# v0.7.0 RC1 — Release hardening

- Retained the user-approved v0.6.3 three-step wizard and the 66-quest/5-Palico recognized-only localization engine. No catalog or gameplay translation values changed.
- Added backup-linked persistent installation journal in the save-root `SAVEDATA` folder; checked for pending recovery before installation, cleared only after successful post-install verification/rollback.
- Added strict standalone recovery module/console entry point, with SHA-256-validated recovery archive and per-target original/new hash allowlist, idempotent restoration, no overwriting unrelated edits, and a welcome-page emergency restore option.
- Moved default private output, reports, and backup directories to Windows `%LOCALAPPDATA%`, away from potentially cloud-synced Documents, while leaving earlier backup locations untouched.
- Added free-disk-space preflight checks and directory fsync on supported local filesystems.
- Conservatively anonymized all human-entered fields in shareable HTML, including downloaded and already-recruited Palico names and Meowsters, unknown/custom text and .dlo references. Private technical reports remain private.
- Added process-death recovery and privacy regression tests with encrypted/mixed save fixtures stored externally (never distributed).
- Pinned top-level Windows build dependencies and supplied staged Windows-native PyInstaller recipe for test-folder then self-contained one-file app and companion recovery executable.
- Clarified manual restore, first run, redistribution rights, Windows acceptance gates and source/package privacy. No compiled Windows EXE is claimed to have been tested in this environment.
