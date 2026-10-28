# Monster Hunter Portable 3rd — DLC English Localizer v1.0.0

Unofficial offline Windows x64 utility for translating **existing downloaded** MHP3rd DLC in PPSSPP. No Python installation is needed. The program does not download DLC or modify the game's ISO.

## How to use

1. Extract this entire ZIP to a normal folder (not your PPSSPP SAVEDATA folder).
2. Close PPSSPP before applying a patch.
3. Run **MHP3rd_DLC_Localizer.exe**.
4. Follow **Find Saves → Choose DLC → Review & Apply → Finish & Close**.

The program previews changes and creates a verified backup before modifying supported save files. It preserves quest gameplay values, character progression, and unselected/custom Palicoes. Original fullwidth names are preserved.

## Recovery

If an installation was interrupted, **keep your original saves and backup**. Close PPSSPP, use **Restore an interrupted installation…** on the first application page, or use **MHP3rd_Recovery.exe**. See `Documentation/Recovery_Guide.md` before manually changing any files.

Private backups and exported reports may contain character/save data. Do not upload those files publicly.

## Legal and source information

This unofficial tool is not endorsed by Capcom, PPSSPP, or translation contributors. The code is under GPLv3; see `Documentation/LICENSE_GPLv3.txt`. Public redistribution of the bundled translation text requires a separate rights review; read `Documentation/THIRD_PARTY_TRANSLATION_RIGHTS.md` **before publishing or mirroring this release**.

The corresponding editable Python source and build scripts are supplied separately as the v1.0.0 source/builder package. Redistributors must make the corresponding GPL-covered source available in accordance with GPLv3; sharing only this EXE ZIP may be insufficient.
