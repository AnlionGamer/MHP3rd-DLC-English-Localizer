# MHP3rd DLC English Localizer v1.0.0 — Windows Builder

This is the **complete source/builder package**, not the end-user release. The builder compiles two self-contained Windows EXEs, then automatically creates a **clean seven-file release ZIP**. You do not need an old ZIP, an earlier build, or any separate packaging script.

## Build — one command

On Windows x64 with Python **3.15.2** and PowerShell **7** installed:

1. Extract this builder ZIP to a normal working directory (not PPSSPP's `SAVEDATA`).
2. Open PowerShell in `MHP3rd_DLC_Localizer_v1.0.0_Source`.
3. Run:

   ```powershell
   .\Build_Windows_EXE.ps1
   ```

4. When it prints **SUCCESS**, open the new `Release` folder.

The only files in `Release` are:

- `MHP3rd_DLC_Localizer_v1.0.0_Windows_x64.zip` — **the ZIP for end users**
- `MHP3rd_DLC_Localizer_v1.0.0_Windows_x64.zip.sha256` — checksum to publish separately

The end-user ZIP contains exactly:

```text
MHP3rd_DLC_Localizer.exe
MHP3rd_Recovery.exe
README.md
Documentation/
    Recovery_Guide.md
    LICENSE_GPLv3.txt
    THIRD_PARTY_TRANSLATION_RIGHTS.md
    Release_Notes_v1.0.0.md
```

**Nothing from the builder** (Python source, tests, build logs, lock files, catalog hashes, spec files, or build tools) is placed in the end-user ZIP. The Python environment stays in `.build-venv` (reused if already installed); intermediate files stay in `.build`. Neither is bundled.

## Running the completed program

End users extract their ZIP and run `MHP3rd_DLC_Localizer.exe`; no Python installation is needed. The wizard follows **Find Saves → Choose DLC → Review & Apply**, localizes recognized existing DLC only, and creates a verified original backup before a direct installation. See the packaged `README.md` and recovery guide.

## Distribution notice

The GPL-covered corresponding source should be made available to users alongside the EXEs. This builder ZIP is the source package, not a file to put inside the end-user ZIP. Public redistribution rights for the included third-party translation wording are **not yet established**; read `THIRD_PARTY_TRANSLATION_RIGHTS.md` before public release. No ISO, downloaded DLC containers, or user saves are provided.
