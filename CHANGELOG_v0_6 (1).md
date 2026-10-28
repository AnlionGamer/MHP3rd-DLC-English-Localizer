# Changes from v0.5.1 to v0.6

- Replaced the multi-panel advanced desktop screen with a compact, ordered **Find Saves → Choose DLC → Review & Apply** wizard.
- Replaced the confusing action name **Create localized output ZIP** with a prominent **Apply English Localization** button.
- Added simple presets: quests only (conservative initial selection), all recognized downloadable DLC, or custom individual Palicoes. Recruited-roster edits remain separately optional and off by default.
- Added an explicitly authorized **Install directly into PPSSPP** option for local save directories. It constructs an independently verified package first, creates a new validated backup and only then replaces recognized edited DLC save files.
- Added safe **Prepare ZIP only** fallback for backup archive inputs, manual testing and users who do not want direct installation.
- Added original-hash checks, Windows PPSSPP-running detection, staged writes, post-install verification and best-effort rollback with a permanently retained recovery backup.
- Added a clear completion page with backup and output paths, plus **Finish & Close**.
- Fixed a GUI thread-boundary problem found during testing: Tk variables are now read only on the UI thread before background analysis.
- Fixed a shutdown event-loop callback issue.
- Preserved the validated translation catalog and the v0.5.1 recognized/recruited Palico handling, including literal `ｕｅ．` and `ｍａｋｉ` formatting.

The program is a **Python desktop application with an optional Windows EXE build script**, not a shipped precompiled EXE. The new direct-install path has offline fixture tests but still requires Windows PPSSPP field testing.
