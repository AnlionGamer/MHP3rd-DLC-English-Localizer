# Validation — MHP3rd DLC Localizer Desktop v0.5.0

**Release classification:** functional GUI **development/test build**. Full offline binary verification passed with both edited containers; in-game v0.5 English spelling/comment changes remain to be inspected. No native Windows EXE is included in this archive.

## Passed

| Area | Evidence | Status |
|---|---|---|
| Catalog integrity | `audit_catalog`: zero errors, zero warnings | PASS |
| Punctuation | Original approved quest title `Island Egg Festival！` retained with fullwidth exclamation | PASS |
| Exact names | `ｕｅ．` and `ｍａｋｉ` remain fullwidth and lowercase as in original DLC | PASS |
| Previously patched v0.4.1 save | `maki` and old `Go all out!` are identified as *eligible editorial repairs*, not custom/corrupt | PASS |
| Approved legacy migration | Output changes only the two selected previous translation fields, preserves other Palicoes and original owner text | PASS |
| Encrypted save reconstruction | Full 66-quest plus five-Palico rebuild, encrypted PSP **mode 5** in both containers | PASS |
| Independent output decoding | Both containers decoded cleanly, with valid integrity checks after writing; all 71 records `already_localized` in fresh inspection | PASS |
| Original source preservation | SHA-256 of source ZIP unchanged across full engine output operation | PASS |
| Quest/gameplay data | Per-record allowed-diff verification inside engine; six text fields per quest roundtrip; data outside approved text/pointer/checksum spans unchanged | PASS |
| Promoted name and creator text | Original `ｕｅ．`, `ｍａｋｉ` and original owner fields preserved; HagiToko revised comment roundtrip | PASS |
| Graphical desktop startup | Tkinter GUI instantiated under X virtual framebuffer; five Palico selections initially OFF | PASS (Linux GUI simulation) |
| Graphical end-to-end | GUI Analyze -> preview HTML -> approval -> new output ZIP with approved old-version migration; original source hash unchanged | PASS (Linux GUI simulation) |
| GUI approval state | Identified and corrected an issue where Create ZIP/View Report buttons were not reenabled after successful Analyze | PASS after correction |
| Source-free automated smoke tests | `python test_v05_desktop.py` verifies catalog, Unicode, UI summary/partial status and exits normally | PASS |

### Test records

1. Encrypted original development fixture: 66 Japanese quest records, five original promotional Palicoes. Analyze classified **71 eligible**, patch engine produced new ZIP with **66 quest translations + five Palico localizations**, and a separate decode classified **all 71 as already localized**. Modes **5/5** preserved. `m60029.mib` retains the fullwidth exclamation. Source ZIP hashes were equal before/after.
2. Previously patched v0.4.1 output from user's prior Windows test: selected `maki` and `hagitokoroo`; analyzer identified **two editorial repairs**, engine rebuilt **only the main save** with existing encryption mode 5. Old `maki` became `ｍａｋｉ`; old `Go all out!` became `HagiToko! Go!`; other promotional text and owner fields preserved. No quest folder in migration-only output.
3. GUI virtual-display test: analyzed the previous v0.4.1 output using the interface and generated its technical and HTML reports, displayed 71 records, exposed enabled review/patch controls, created a fresh ZIP after simulated explicit approval, and confirmed the input archive hash stayed unchanged. **This validates application wiring, not the actual Windows file dialogs or Windows executable.**
4. Earlier v0.4.1 engine baseline passed offline encrypted/unencrypted/mixed-encryption fixtures and was spot-checked in PPSSPP for five Palico translations and downloader recognition. The underlying encryption/rebuilding primitives were not rewritten for v0.5; newly updated Palico edits were tested on encrypted mode 5. An additional standalone v0.5 mixed/unencrypted matrix is recommended before broad community release.

## Unverified and remaining limitations

- No Windows `Build_Windows_EXE.ps1` / PyInstaller build was executed in this Linux environment; build and test on Windows.
- No first-run dependency-installer Windows GUI clickthrough was executed here. The user previously tested the v0.3/v0.4 console dependency provisioning on Windows, not the v0.5 GUI bootstrap.
- **The new v0.5 names and HagiToko comment have not yet been verified on-screen in PPSSPP.** Earlier v0.4.1 localization was inspected in-game; do not conflate the versions.
- PPSSPP save/reload and downloadable quest completion/rewards have not been independently confirmed by the user in this thread.
- Other untouched bonus DLC content beyond 66 documented quest records and five selected promotional Palicoes is preserved, not claimed translated.
- The five promotional Palico name/comment English adaptations are editorial; original kana does not prove Western capitalization or official preferred spellings.
- ZIPs with any Palico edits include private hunter data because Palicoes are stored in the main save; do not share those output ZIPs publicly.

## Safety controls

Source file fingerprint verification occurs before and during output creation. No output path may coincide with source or be located inside a selected directory. The new ZIP is created through a verified temporary archive and committed using a no-clobber link. Unknown/custom data remains unchanged; partial omissions require separate approval. Output itself must pass encryption/format/checksum and restricted decoded-byte comparisons. Nothing is auto-installed into PPSSPP.
