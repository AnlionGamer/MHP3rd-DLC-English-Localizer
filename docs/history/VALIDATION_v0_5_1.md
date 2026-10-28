# MHP3rd DLC Localizer v0.5.1 — Offline validation

## New behavior

Downloaded promotional Palicoes and recruited/hired copies are separate saved records. The **opt-in** recruited editor is limited to the 5 known promotional IDs and their approved name/comment fields. It is OFF by default and only acts on records positively identified by their original or whitelisted legacy text. It does not target ordinary/custom Palicoes.

The supported general-save size is 1,183,744 decoded bytes. Two populated hunter slots were inspected in the user's private encrypted and mixed-encryption backups. The observed recruited roster arrays start at 0x5DA68 and 0xBDA68 (0x60000 hunter stride) with 0xA0-byte entries; a third expected hunter position is bounded at 0x11DA68 but **not yet tested with an occupied third hunter slot**. The new operation is conservative, recognizes only exact documented layout/identity and refuses unsafe edits. Fullwidth Latin names (`ｕｅ．`, `ｍａｋｉ`) are preserved.

## Completed offline tests

| Test | Result |
|---|---|
| Original encrypted (PSP mode 5) source, separate opted-out analysis | PASS: recruited inventory is not scanned when disabled |
| Original encrypted source, opted-in recruited analysis | PASS: five recognizable promotional Palicoes in each of two hunter slots |
| Encrypted rebuilt output, 5 downloaded + 10 recruited copies | PASS: all 15 text records translated; mode 5 retained |
| Decoded byte-diff allowlist for entire main save | PASS: every change falls inside approved name/comment regions or required checksum |
| Original creator/owner text | PASS: exact original attribution unchanged |
| Changed gameplay data or Palico statistics | None in offline byte-diff verification |
| Fresh analyzer scan of localized output | PASS: all 10 recruited copies `already_localized` |
| Input ZIP hash before and after | PASS: input unchanged |
| Mixed-encryption sample (main unencrypted; quests encrypted) | PASS: modified main output stays unencrypted; unmodified QST folder omitted |
| v0.4.1 localized ZIP re-analysis | PASS: 10 recruited original Japanese copies recognized, separate from already-localized downloaded definitions |
| Deliberately altered recruited nickname (in-memory test) | PASS: customized name `protected_custom_text`; another supported copy can still be safely localized |
| Whole-flow 66 quest + 5 downloadable Palicoes + 10 recruited copies | PASS: 81 records re-analyzed as `already_localized`, both edited containers retain mode 5 |
| GUI launch under virtual graphical desktop | PASS: v0.5.1 window opens, option defaults off |
| GUI record list | PASS: 66 quest, 5 downloaded and 10 recruited entries displayed distinctly |
| Prior v0.5 catalog and GUI summary regression | PASS (fixture-free subset) |

One combined regression run containing both encrypted and mixed-encryption fixture tests **timed out after completing the encrypted checks**. The mixed-encryption scenario passed as an earlier focused test, but the combined run is not claimed as completed. A fully encrypted disposable save with simulated custom nickname was not rebuilt end-to-end due to timeouts; customized-name protection was tested directly against the decoded record writer and full decoded byte allowlist instead.

## NOT YET verified

- In-game PPSSPP behavior of the newly edited recruited Palico roster copies: loading, changing the active Palico, saving, reopening and roster stability.
- An occupied **third** hunter slot and unfamiliar/custom modded character layouts.
- Windows native `.pyw`/Tkinter execution in a real Windows desktop for this exact version (graphical launch tested in Linux virtual display).
- Optional PyInstaller self-contained Windows `.exe` build and execution.
- All custom/unsupported PSP encryption modes beyond the tested original plaintext and PSP mode 5 paths.

**Status:** Offline-verified pre-release. Do not install into an active PPSSPP save without isolated in-game verification and an original backup. The patcher never directly installs or overwrites source saves.

## Final GUI usability correction

During virtual-display inspection the original stacked layout allowed the output-location row to collapse below the viewport when the options section grew. This was fixed by moving the output/approval controls above the vertically flexible record preview and compacting the Palico checkboxes into one row. Verified under a 1190×825 virtual desktop: all buttons, input fields, partial-approval checkbox, and record list remain visible. At the minimum 980×690 window the record list is narrow vertically and the user should enlarge the window for comfortable detailed review.
