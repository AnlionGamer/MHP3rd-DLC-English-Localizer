# v0.7.0 RC1 verification — 2026-10-27

## Release classification

**Offline hardening release candidate — NOT YET A FINAL PUBLIC WINDOWS EXE.** The current environment runs Linux, not Windows. Native Windows compilation, anti-malware/SmartScreen behavior, PPSSPP testing of this precise build, and permission for third-party translation prose remain pending.

## Changes in this revision

The quest/Palico translation catalog and approved gameplay diff policy were retained from v0.6.3. New work is restricted to reliable installation, persistent recovery, report privacy, Windows build reproducibility and documentation. The GUI's original three-step flow is preserved, with one optional emergency restore button on the first page.

## Automated checks completed here

- `python -m compileall -q .` — passed.
- `python test_v063_selection.py` — passed; only selected known records may cause partial approval.
- `python test_v062_fullwidth.py` — passed; fullwidth Latin policy and catalog guard.
- `python test_v061_meowster.py` — passed; original/legacy Palico text, Meowsters, custom creator protection and allowlisted decoded diffs.
- `xvfb-run -a python test_v063_wizard.py` — passed; 0/2/5 Palico discovery, normal small-window review, no extraneous checkbox, invalid source refusal.
- `xvfb-run -a python test_v063_partial_gui.py` — passed; selected-only partial approval via one confirmation.
- `python test_v070_release.py` — passed; shareable HTML/JSON redaction of synthetic private text (including recruited Palicoes and .dlo fields); interrupt/restore exact bytes; reject unrecognized current target bytes.
- `python test_v070_release.py --fixture [PRIVATE ENCRYPTED SAVE ZIP]` — passed. Staged a real 66-quest + selected Palico patch, terminated a dedicated subprocess with `os._exit(79)` after the first actual save-file replacement (so the normal exception handler could not perform rollback), confirmed the journal/backup remain, confirmed new installs refuse pending recovery, restored exact source BIN/SFO bytes from the backup, and completed a subsequent clean install/re-analysis. Input fixture untouched.
- Same test with an independent **mixed encrypted/unencrypted** personal-save backup — passed.

**Testing limits:** source tests ran on Python 3.13.5 with cryptography 46.0.4. The source Windows release builder pins Python 3.15.2, cryptography 50.0.2 and PyInstaller 6.22.3; that *Windows* combination is not directly tested in this environment. Existing older in-game PPSSPP validation does not constitute validation of this new installer/recovery wrapper.

One superseded v0.5 GUI helper test embodies an older partial-selection policy and is archived under `Docs/Previous validation/Obsolete tests` for historical reference. The current v0.6.3 selection tests supersede it. An extended original v0.6 installer regression was not counted after an execution timeout; the new targeted v0.7 exit/recovery tests above passed and cover the hardened installer.

## Explicit release gates remaining

1. Run `Build_Windows_EXE.ps1 -Stage TestFolder` on Windows and verify the one-folder EXE, including bundling of `catalog.json` and private reports.
2. After confirming the folder build, run `-Stage SingleFile`. Test both produced executables as a normal user with no Python, including their hashes and console recovery.
3. Run PPSSPP save/reload, quest completion/rewards and downloaded/recruited Palico validation on disposable working saves. Confirm compatibility with normal and mixed-mode sources.
4. Confirm output/backup behavior, live-PPSSPP refusal, read-only/low-space conditions, Windows DPI, and Windows forced-process-termination restore.
5. Review translator credits and obtain permission/independent replacement for reused community translations before **public distribution**. Keep original game assets and personal save files out of distributed ZIPs.

Only after those gates pass should the **same tested EXE bits** be designated final; do not rebuild the code after testing without repeating the acceptance checks.
