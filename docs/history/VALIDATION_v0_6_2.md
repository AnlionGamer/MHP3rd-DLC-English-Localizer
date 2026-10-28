# MHP3rd DLC Localizer v0.6.2 — validation and remaining limits

## Corrected behavior

The **original fullwidth Latin display characters** are preserved exactly in the localized program output, including the original period and case. This applies to Palico names `ｕｅ．`, `ｍａｋｉ` and creator/Meowster display names `ｉｎｏ．`, `ＭＡＫＩ`, and `ＳＥＡＭＯ`. Their v0.6.1 narrow-ASCII Meowster equivalents `ino.`, `MAKI`, `SEAMO` are recognized only as approved legacy inputs for repair. Japanese-script creator display names remain separate, editorial romanizations: `ピエールたき` to `Pierre Taki`; `ハギー` to `Haggy`.

The catalog validator blocks any future changes that would normalize original fullwidth Latin *Palico names or Meowster credits* to ASCII.

## Completed checks

- Five original downloadable records and the recognized v0.6.1 legacy spellings passed targeted Unicode, catalog, field boundary, and re-analysis tests.
- Legacy ASCII creator spellings were restored to the exact original fullwidth forms; Japanese-script creator names previously romanized were left unchanged.
- Customized/unrecognized creator text was classified as **protected**, not overwritten.
- Real encrypted backup (`PSP mode 5`): updated five downloadable records and ten recruited copies in a newly generated ZIP. Decrypted rebuilt records matched all approved fields, with **no changed decoded bytes** beyond selected name/comment/creator fields and required inner checksum.
- Real mixed-encryption backup (`ULJM05800` unencrypted): the same 15-record test passed and the original main-save encryption state was retained. Both tests independently re-analyzed output as already localized. Original archive SHA-256 unchanged.
- The five-Palico focused v0.6.1 regression test passed against the revised catalog.
- GUI resize smoke test passed at 760×540, 860×630, 1080×760 and 1470×850, with action buttons remaining visible.
- Python source compilation and translation catalog audit passed: zero blocking errors and zero advisories.

## Still required

- Native Windows direct-install and PPSSPP save/reload testing of v0.6.2, especially verification of the Meowster display lettering in-game.
- This update changed the desktop catalog, detection, output patching and display wording but **did not rewrite** the prior backup-first installer or quest translation algorithm. Earlier versions' broader tests do not automatically certify the new version's entire end-to-end Windows installation workflow.
- The `Haggy` spelling and other romanizations remain editorial, not verified official English spellings.

All fixture ZIPs remained outside the distributed application package. **No player character saves are included.**
