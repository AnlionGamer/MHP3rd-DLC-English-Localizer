# v1.0.0 Windows build — final clean release

## Build

1. Install Python 3.15.2 x64 and PowerShell 7 (if not installed already).
2. Open this extracted source directory in PowerShell.
3. Run `./Build_Windows_EXE.ps1` **once**.
4. The finished `Release` folder contains just the end-user ZIP and its external `.sha256` file.

The build environment is under `.build-venv`; temporary build output is under `.build`. The builder validates the exact v1.0.0 catalog hash, the PyInstaller/cryptography versions, and both EXE version resources before packaging. The archive packager uses an explicit seven-file allowlist and verifies the ZIP contents byte-for-byte against the compiled EXEs and selected documents.

You do not need `Package_Windows_Release.ps1`, an earlier release ZIP, or any extra packaging command. The release source and translator rights notice should be hosted separately from the binary download.

## Clean archive contents

`MHP3rd_DLC_Localizer.exe`, `MHP3rd_Recovery.exe`, `README.md`, `Documentation/Recovery_Guide.md`, `Documentation/LICENSE_GPLv3.txt`, `Documentation/THIRD_PARTY_TRANSLATION_RIGHTS.md`, and `Documentation/Release_Notes_v1.0.0.md`.

## Scope of this revision

The application engine, translation catalog, UI, save handling, recovery behavior, and Windows version numbers have not been altered. This revision replaces only the packaging/build workflow and associated documentation. Existing in-game localization regressions need not be repeated for a ZIP layout change.

**Before public redistribution:** Resolve third-party translation permissions (see `THIRD_PARTY_TRANSLATION_RIGHTS.md`). Make the corresponding GPL-covered source available. Do not distribute saves or ISOs.
