# MHP3rd DLC Patcher v0.4.1 — offline engineering validation

Date: 2026-10-27. All testing on copies in isolated workspace; PPSSPP gameplay tests NOT performed for this v0.4 build.

| Test | Result | Notes |
|---|---|---|
| Live encrypted DLC quest archive, technical v0.3 fingerprint | PASS | 66 quests translated; re-read output decoded all 66 as `already_localized`; PSP mode 5 preserved; output excludes `ULJM05800` |
| Exact title punctuation after encoding | PASS | `m60029.mib`: `Island Egg Festival！` identical in approved catalog and rebuilt UTF-8 string; no Unicode normalization |
| Catalog validation | PASS | 0 errors, 0 warnings; two earlier U+FFFD apostrophe repairs retained |
| Live mixed encryption, quests + one selected Palico | PASS | Quest PSP mode 5; general-save mode 0; 66 quests + one Palico; original general-save hunter region and creator text unchanged |
| Entirely unencrypted DLC-only source, quests + two Palicoes | PASS | Modes 0 / 0 preserved; 66 quests + two Palicoes |
| Live encrypted general save, Palico-only | PASS | Mode 5 preserved; one Palico localized, no quest file included; owner and hunter region preserved |
| Previously translated English build | PASS | 64 quests already localized, two known broken-apostrophe records repaired; only the two changed |
| Stale fingerprint | PASS | Refused with no output |
| Synthetic unknown/custom quest | PASS | 65 eligible + one unknown; refused without `--approve-partial`, succeeded with explicit approval while preserving unknown quest slot exactly |
| Synthetic modified gameplay byte in quest | PASS | Altered non-text byte survives targeted text repacking unchanged |
| v0.2/v0.3 path, privacy, QA and format regression suite | PASS | 9 unit tests |
| End-to-end ZIP creation/readback | PASS | ZIP members and entire byte contents checked; output-only, source file hashes unchanged |

Key preservation proof: `patch_dlc.py` uses a per-byte allowlist comparison on decoded quest and general-save data, then verifies the complete result via both MH inner cipher and PSP savedata decoder. It does not copy any entire translated quest record over custom gameplay data. Non-matching character/quest fields are skipped or rejected.

**Not yet verified:** GUI/Windows live launcher execution, running a quest and saving/reloading in PPSSPP, PSP encrypted modes 1/3 on authentic files, Palico editorial wording accuracy, online compatibility, translations for other bonus content and third-party redistributability.

Reproducibility: source code and test cases supplied. `test_v04.py`, `test_gameplay_v04.py` and `test_partial_v04.py` use private fixture filenames under `/mnt/data` during development; those actual saves are NOT bundled. No private player data is included in the distributable source package.

## v0.4.1: ｕｅ． fullwidth-name preservation

The 2026-10-27 correction treats the original `ｕｅ．` as the approved localized name, retaining its exact UTF-16 code points (fullwidth `ｕ`, `ｅ`, `．`). No ASCII spaces exist in the original, but glyph width conveys the intentional separation. Selecting the `ue` promotional Palico now localizes its comment ONLY. Owner attribution is never edited.

| Offline validation | Result |
|---|---|
| Mixed encryption input (main save plaintext, QST encrypted), select `ue` comment | PASS |
| Fully encrypted input (PSP mode 5), select `ue` comment | PASS |
| Source archive SHA-256 remains unchanged after patching | PASS, both inputs |
| Original name field bytes, owner field bytes, unrelated main save payload | PASS, exact decoded byte comparison |
| New output retains original main-save encryption mode | PASS, modes 0 and 5 |
| Writer changes exactly comment UTF-16 field and required main checksum in decoded save | PASS, both inputs |
| Re-analyzer recognizes patched record as already localized | PASS, encrypted output |
| Catalog audit | 0 blocking errors, 0 warnings |

This is an **offline test release**, not evidence that PPSSPP gameplay/save/reload has passed. Re-analyze under v0.4.1: the catalog and plan fingerprints changed. If an earlier v0.4 output already changed the name to ASCII `ue.`, do not treat it as fresh original save; this release does not automatically rewrite it back. Start from an unchanged backup instead.
