# Promotional Palico localization review — v0.6.2

The names and original Japanese comments below were read from **original downloaded DLC records**, not inferred from a screenshot. Fullwidth Latin Palico names are deliberate identifiers and kept unchanged; recognized promotional **Meowster display names** written in Japanese script can be romanized without changing who the creator is. Fullwidth Latin credit text remains exactly intact. See the linked project audit for historical references and fuller linguistic context; the romanizations are editorial proposals, **not confirmed official English names**.

- `ｕｅ．` — Preserve EXACTLY: three fullwidth codepoints including final fullwidth period; **no literal spaces**. Original comment `ｉｎｏ．は頼りになるニャ！！`, localized `Count on ino.!`. The name `ino.` inside the comment and the Meowster `ｉｎｏ．` are recognizable. Meowster display name remains the original `ｉｎｏ．` when selected. Omission of “meow” and one exclamation is due to 14-character in-game text limit.
- `ｍａｋｉ` — Preserve EXACTLY: four lowercase fullwidth Latin letters. Original comment `可愛がると喜びます！` approximately “I get happy when you show me affection!”; concise localized `Love me lots!`. Previous v0.4.1 used `maki`; this exact previous spelling is whitelisted as an approved *legacy* value, not as a new default.
- `ピエルー` — In-game `Pieru`. Romanization approx. `Pierū`/`Pieruu`, with a prolonged final vowel. Keep readable v0.4.1 `Pieru` unless independently verified official spelling arises. Original `ハロにちわ～。連れてって～！` contains a blended greeting and playful elongation. `Hiya! Take me!` is a shortened adaptation.
- `ハギとこルー` — In-game `HagiTokoRoo` (editorial camel case reflecting branded `ハギとこ`). Original comment `ハギーのとこトンやってみよう` refers to the HagiToko program. Revise former `Go all out!` to **`HagiToko! Go!`**, length 13, to preserve the intended allusion and action. This is an editorial condensed branding adaptation, not a literal translation or official quote. Prior string retained as a migration alias.
- `コシーモ` — In-game `Koshiimo`, approximate formal Romanization `Koshīmo`. Original `毒関係はまかせてほしいなり！` asks to leave poison-related matters to the Palico; `Poison's mine!` conveys the tactical gist within the comment limit. Initial capital K is editorial.

**Hard requirements:** only romanize a positively identified Japanese-script Meowster name to the approved English display form; preserve all original fullwidth Latin name characters in the live result and the exact original text in the recovery backup; refuse custom Meowster edits; never silently uppercase, lowercase, strip a period or normalize fullwidth glyphs; validate exact UTF-16 round-trips; detect approved legacy spellings for migration; protect other customization; surface confidence/translation notes in UI and report. No changes to gameplay fields.

Reference audit: `MHP3rd_Promotional_Palico_Name_Language_Audit_20261027.md` in the development project, not bundled because it includes original save-file paths.

## Recruited-copy policy (v0.6.2)

The five downloaded promotional Palico names/comments are distinct from copies already hired into a hunter's personal roster. Opting in to retroactive recruited localization is a separate selection, **disabled by default**. Only approved promotional name/comment/Meowster fields are eligible. The string `ｕｅ．` retains its exact fullwidth presentation, and `ｍａｋｉ` is not converted into ASCII. Original fullwidth Latin Meowster names remain unchanged. Japanese-script Meowster names are romanized only when positively identified. Fullwidth Latin writing is also preserved in the localized save; Japanese-script original text is preserved in the backup and its credited identity remains unchanged. Any custom nickname/comment is protected rather than overwritten. Other Palicoes and gameplay data are never edited. The analysis preview identifies each recruited copy by hunter and roster position without including raw hunter data.

## Meowster display names (v0.6.2)

The Meowster field is a creator/hunter credit (not the Palico's nickname). Because English localization is specifically requested for selected downloadable Palicoes, Japanese-script names in this field can be romanized; already-Latin fullwidth names are kept exactly. The program changes no other credit/identity fields. A custom creator name is never guessed or overwritten.

| Original Meowster | Display after localization | Editorial status |
|---|---|---|
| `ｉｎｏ．` | `ｉｎｏ．` | Exact original fullwidth lowercase and fullwidth period preserved |
| `ＭＡＫＩ` | `ＭＡＫＩ` | Exact original fullwidth uppercase preserved |
| `ピエールたき` | `Pierre Taki` | Romanized name of Pierre Taki; readable English form |
| `ハギー` | `Haggy` | Editorial phonetic nickname for Capcom presenter Hagi (萩原良輔) |
| `ＳＥＡＭＯ` | `ＳＥＡＭＯ` | Exact original fullwidth uppercase preserved |

The `Haggy` spelling is an editorial choice rather than a proven official English-stage rendering. `ｉｎｏ．`, `ＭＡＫＩ` and `ＳＥＡＭＯ` retain the exact original typography. The v0.6.1 ASCII Meowster spellings `ino.`, `MAKI`, `SEAMO` remain recognized *legacy input* spellings and will be restored to fullwidth only for positively identified records.
