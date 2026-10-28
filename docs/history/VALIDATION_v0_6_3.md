# v0.6.3 validation — 2026-10-27

**Scope:** UI and user-consent behavior only; no new game-format modifications.

## Passed

- Graphical wizard smoke tests under Xvfb at 760×540, 800×590, and 1120×740. Synthetic sources with **0**, **2**, and **5** recognized promotional Palicoes yielded exactly matching available selections. Missing entries were disabled.
- Direct-install and ZIP-export GUI flows reached the expected Finish & Close screens with no redundant approval checkbox. The primary Apply action remained visible. Partial cases were accepted only via an explicit confirmation dialog and passed `allow_partial=True` to the patch engine.
- Unknown/unselected Palico inventory entries did not trigger partial approval. A **selected** customized Palico correctly required explicit partial approval.
- Invalid save inventory check displayed an error and disabled Next rather than letting an unsupported source proceed.
- Original fullwidth catalog validation, Japanese/legacy Palico text conversion and custom Meowster protection test passed.
- Actual user-provided **mode-5 encrypted** save backup analyzed read-only: 66 installed quest records, five recognized promotional records.
- **End-to-end quest-only** patch: new v0.6.3 approved analysis matched writer; 66 quests localized, output re-analyzed with all 66 as `already_localized`; main character folder excluded; input archive SHA-256 unchanged. Patch writer additionally skips decoding unrelated unselected main containers.
- `python -m py_compile` passed for modified app, analyzer, and patcher modules.
- GUI partial-approval test passed: selected customized content requires clear consent in a single Apply confirmation, without a checkbox.

## Not claimed

- A Windows-native test of the revised GUI is pending. Xvfb is not a substitute for all Windows DPI/accessibility combinations.
- A full in-game save/reload and DLC quest completion check for v0.6.3 has not been performed in this session.
- Re-ran the full disposable-copy direct-install and rollback test against your encrypted save backup: an injected mid-install failure was refused and restored exact original bytes; a subsequent clean install re-analyzed correctly, with an intact recovery ZIP. The live save installation was **not** performed.

**Important:** Missing DLC will remain missing. Selecting all applies only to recognized records already present; this program never downloads official DLC.
