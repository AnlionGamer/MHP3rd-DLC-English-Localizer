# MHP3rd DLC Localizer v0.6.1 — Validation and limits

## Completed offline checks

- 81 selected records recognized in the original encrypted user save ZIP: 66 quests, 5 downloaded Palicoes, and 10 recruited promotional copies across 2 hunter slots.
- Full encrypted rebuild of all 81 records completed. Main save and quest files preserved PSP mode 5. Decoded all five downloaded and ten recruited name/comment/Meowster records: they matched every approved English catalog field exactly.
- Compared reconstructed decrypted main save to the original: **zero changed bytes outside the 15 selected 0xA0 records' allocated name/comment/Meowster fields and required inner checksum**. The original ZIP SHA-256 was unchanged.
- v0.4.1 legacy ZIP reanalysis passed: 66 quests already localized; 13 Palico records eligible for newly localized text/Meowster and 2 eligible for earlier editorial repair (5 downloadable, 10 recruited).
- Five-Palico focused in-memory patch test passed; a custom Meowster label was protected and four other recognized Palicoes remained eligible; selecting no Palicoes produced byte-identical output.
- GUI smoke tests passed under a virtual desktop with mock data at 760x540, 860x630, 1080x760, 1470x850; navigation/footer remained visible and review retained scroll space.
- Previous v0.6 wizard flow smoke test passed for install and export with mocked patch/install workers.
- Translation catalog quality audit: 0 errors and 0 warnings.

## Not yet completed

- Windows native DPI/font rendering and Windows direct-install test with v0.6.1 must be validated by the player.
- In-game save/reload check specifically for the five newly romanized Meowster labels.
- Full end-to-end reanalysis of newly patched ZIP was not completed as part of the final timed regression run; the independently decoded record content and byte-difference checks passed.
- The `Haggy` spelling is editorial, not independently verified as an official English spelling.

## Recovery and scope

Backups preserve original bytes before direct installation. The Meowster UTF-16 field is intentionally localized **only for explicitly selected, recognized promotional Palicoes**. Player-edited creator labels are protected. Related hunter stats/skills/gear, other Palicoes and unselected DLC records are outside the permitted edit set.
