# MHP3rd DLC Localizer v0.6.2 — Original typography correction (TEST)

- Corrected the regression introduced by v0.6.1: source fullwidth Latin Meowster names `ｉｎｏ．`, `ＭＡＫＩ`, `ＳＥＡＭＯ` are now preserved byte-for-byte; no case, punctuation or width normalization.
- Names originally in Japanese kana remain eligible for editorial romanization (`ピエールたき` to `Pierre Taki`; `ハギー` to `Haggy`).
- Recognizes ASCII Meowster variants from v0.6.1 (`ino.`, `MAKI`, `SEAMO`) as approved legacy inputs and can restore the original typography without rewriting already-localized quest records.
- The catalog validator now rejects future changes that would turn known fullwidth Latin creator or Palico names into ASCII.
- Previous encryption-preserving engine, save backups, rollback and three-stage wizard retained.
- Not yet validated through a native Windows PPSSPP save/reload test.
