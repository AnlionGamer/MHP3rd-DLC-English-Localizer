# MHP3rd DLC English Localizer v1.0.0 — Source and one-command Windows builder

Run `./Build_Windows_EXE.ps1` in PowerShell 7 on Windows x64 with Python 3.15.2. The builder compiles the localizer and independent recovery utility and automatically generates **only the required seven end-user files** in `Release/MHP3rd_DLC_Localizer_v1.0.0_Windows_x64.zip`.

Build environments (`.build-venv`), PyInstaller intermediates (`.build`), build tools, tests, and original source code stay outside that ZIP in the builder folder. There is **no separate repackaging step** and no dependency on previous builds. The SHA-256 checksum is next to the release archive, not inside it. See `README_FIRST.md` for step-by-step instructions.

## Frozen application features

- Guided **Find Saves → Choose DLC → Review & Apply** UI.
- Only recognized already-downloaded content: up to 66 quests, up to 5 promotional Palicoes, and optional recognized recruited Palicoes.
- Preservation of original fullwidth Latin lettering and typography.
- No changes to gameplay data, character items, progression or unrelated save information.
- Verified backups and crash-interruption recovery, including an independent recovery executable.
- Support for independently encrypted or unencrypted PPSSPP save containers.

The localization catalog, save-data patching logic, recovery engine, and GUI are **unchanged** from the previously tested v1.0.0 source. Changes here affect **builder/package logic and build documentation only**.

## Requirements / rights

The builder needs pinned Python/PyInstaller dependencies; the finished EXEs need no Python. Both binaries have Windows file version 1.0.0.0. No game ISO, original DLC, or private saves are part of this source or release. Source code uses GPLv3; the bundled translation text has additional third-party rights considerations. Read `THIRD_PARTY_TRANSLATION_RIGHTS.md` before uploading the application publicly.
