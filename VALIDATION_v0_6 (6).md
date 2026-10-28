# v0.6 Guided Desktop Localizer — Test & Safety Report

**Release type:** Windows graphical Python **TEST** application. Not a fully certified Windows installer or prebuilt EXE.

## What was changed

The previous v0.5.1 patch engine is retained. The desktop interface was redesigned into a three-stage wizard: **Find Saves → Choose DLC → Review & Apply** with **Apply English Localization** as the emphasized final action and **Finish & Close** as the terminal screen.

A new, separate `safe_install.py` module adds direct installation into an explicitly chosen local PPSSPP save directory. It is never invoked for input ZIP archives and can be bypassed with **Prepare ZIP only**.

## Verified protections

- **Analysis:** read-only preview using the established decoder and current catalog; source fingerprint is rechecked during patch creation.
- **Verified package:** the existing engine writes a new ZIP and validates every archive member, decoded DLC text, allowed byte differences, quest record SHA, game checksum and original encryption mode.
- **Explicit install approval:** the interface requires confirmation that PPSSPP is closed. The installer additionally checks for running PPSSPP processes on Windows using `tasklist`.
- **Verified original backup:** all files in affected MHP3rd save folders (including original BIN/SFO and auxiliary icons) are archived before any installation and re-read for exact matching. The backup is always retained.
- **Narrow installation:** only affected `ULJM05800`/`ULJM05800QST` `MHP3RD.BIN` and `PARAM.SFO` files are replaced; no unrelated game folders or images are overwritten.
- **Atomic per-file stage and replace:** replacement bytes are staged and hashed before `os.replace`; installed bytes are compared with the verified package and the game-save analyzer is rerun.
- **Rollback:** on a synthetic mid-install write error, the original savedata was restored exactly and a recovery backup remained available.
- **Encrypted preservation:** mode 5 encrypted test fixtures were used; earlier version regression coverage included unencrypted and mixed-encryption inputs. The underlying engine's mode-preservation logic was not rewritten.
- **Localization scope:** 66 approved quest translations, five downloaded Palicoes and separately optional recruited Palico text; custom names, other player data, owner/creator names and unknown DLC remain protected.

## Automated tests

- `test_v06_wizard.py` under a graphical test display: source selection, three wizard screens, one-click full DLC preset, custom selection controls, mandatory install consent, visible primary action, completion and window close — **PASS**.
- `test_v06_wizard.py` ZIP-input path: forced package-only mode; completion explicitly says no installation occurred — **PASS**.
- `test_v06_installer.py` with a **private** encrypted save fixture: generated localized output with source unchanged; injected failure on the second write restored original files byte-for-byte; real install created a validated backup and post-install analysis recognized translated records — **PASS** (development fixture, not real PPSSPP gameplay).
- `test_v051_hired.py` no-private-fixture structural/catalog suite — **PASS**; encrypted/mixed fixture-dependent cases intentionally skipped when private inputs not provided to that command.

## Limits and unverified items

1. This test was performed in a Linux graphical test environment with a disposable PPSSPP save-folder copy. **The new direct installer and three-step GUI need user testing on Windows.** The `tasklist` branch cannot be fully exercised under Linux.
2. Automatic backup and rollback are robust against ordinary Python/file-write failures, but cannot guarantee recovery from power loss, process termination during a multi-file replace, physical disk failure or unusual network-filesystem behavior. Keep your own separate backup.
3. v0.5.1 recruited Palico changes and the revised HagiToko English comment remain unconfirmed after full in-game save/reload. Earlier v0.4.1 source quest/Palico localization and DLC detection were manually spot-checked in PPSSPP.
4. No prebuilt Windows EXE is provided. The Windows PowerShell EXE build recipe is optional and has not been run in this environment.
5. ZIP-only mode **does not install** content. The wizard clearly indicates this outcome and provides the output location.

Do not run the installer against an active emulator or overwrite the only save you possess. Results, backups and full technical reports are private user artifacts.
