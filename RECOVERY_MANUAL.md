# Recovering an interrupted MHP3rd DLC localization

**If PPSSPP reports a corrupted save or the installer terminates unexpectedly, close PPSSPP. Do not delete, edit, or overwrite any files in `SAVEDATA`, `Backups`, or the pending journal.**

Version 1.0.0 writes a pending recovery journal named `.mhp3rd_localizer_pending.json` into the same `SAVEDATA` directory as the affected `ULJM05800` and/or `ULJM05800QST` folders. It is written **only after** a complete backup has been created and verified, and before any game save file is replaced.

## Recommended restoration through the main app

1. Close PPSSPP completely.
2. Launch the localizer.
3. On **Find Saves**, click **Restore an interrupted installation…**.
4. If the program did not automatically detect the correct `SAVEDATA`, browse to it.
5. Read the confirmation, select **Yes**, and check for the **Recovery successful** message.
6. Start PPSSPP and verify your original save loads normally. Your separate recovery ZIP remains available.

The app refuses a new installation while a pending recovery journal remains.

## Recovery without the main GUI

On Windows, use the separately packaged standalone console executable in the *compiled EXE candidate* directory:

```powershell
.\MHP3rd_Recovery.exe --savedata "C:\Path\To\PPSSPP\memstick\PSP\SAVEDATA" --check
.\MHP3rd_Recovery.exe --savedata "C:\Path\To\PPSSPP\memstick\PSP\SAVEDATA"
```

For the source package, the equivalent is `python recovery.py --savedata "C:\Path\To\SAVEDATA"` (Python and installed `cryptography` needed to load the source toolchain).

The recovery operation validates the backup ZIP SHA-256, its member manifest, the original bytes, and the current state of **all** affected save files before writing. A file may be either the original bytes or the exact patch output bytes. Any other state causes recovery to refuse to overwrite that file; a manual specialist investigation is then necessary. Recovery changes only affected `MHP3RD.BIN` and `PARAM.SFO`, never companion icons or unrelated files. It retains the recovery ZIP.

A successful installation clears the pending journal; this command is designed for **interrupted** installs, not as a general undo button after an already committed install. For restoring a completed installation, preserve and manually copy the original files from your verified backup, matching the original folder names. Avoid copying an unrelated hunter's save.

Do not upload recovery ZIPs or private technical JSON reports publicly: they may contain original hunter data.
