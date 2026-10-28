# Monster Hunter Portable 3rd — DLC English Localizer

**An unofficial, offline English-localization utility for downloaded Monster Hunter Portable 3rd DLC in PPSSPP.** The Windows x64 application does not require Python.

**[Download v1.0.0 for Windows](https://github.com/AnlionGamer/MHP3rd-DLC-English-Localizer/releases/tag/v1.0.0)**

## What it does

- Translates text in **up to 66 recognized, already-downloaded Event Quests**.
- Offers localization of **detected** promotional Palicoes (up to five), including names, comments, and Meowster credits. You do **not** need to have all five.
- Optionally updates recognized promotional Palicoes already recruited into your roster.
- Preserves original fullwidth Latin lettering and punctuation according to the documented [name policy](NAME_TRANSLATION_POLICY.md).
- Provides a preview, verified original backups, and an independent interrupted-installation recovery utility.
- Supports supported PPSSPP save containers with encrypted or unencrypted data.

The program **does not** download missing DLC, provide game files, or modify your ISO. It is intended to change eligible text only, not quest mechanics, rewards, equipment, or hunter progression.

## Install and use

1. Download **`MHP3rd_DLC_Localizer_v1.0.0_Windows_x64.zip`** from [Releases](https://github.com/AnlionGamer/MHP3rd-DLC-English-Localizer/releases/latest).
2. Extract the ZIP into its own folder, **outside PPSSPP's `SAVEDATA` directory**.
3. **Close PPSSPP completely**.
4. Run **`MHP3rd_DLC_Localizer.exe`**.
5. Follow **Find Saves → Choose DLC → Review & Apply**. Select only the content you want to localize.
6. Keep the backup created by the program. If an installation is interrupted, use the recovery option or **`MHP3rd_Recovery.exe`**.

Only DLC already present in the selected save can be localized. The preview shows the content actually detected rather than assuming all quests or promotional Palicoes are installed.

**Privacy:** backups and reports can contain character/save information; do not post them publicly when reporting an issue.

## Download, source, and support

| Resource | Link |
| --- | --- |
| Windows release | [v1.0.0 download and release notes](https://github.com/AnlionGamer/MHP3rd-DLC-English-Localizer/releases/tag/v1.0.0) |
| Problems or suggestions | [GitHub Issues](https://github.com/AnlionGamer/MHP3rd-DLC-English-Localizer/issues) |
| Build from source | [Windows building guide](docs/BUILDING.md) |
| Test and validation notes | [Testing guide](docs/TESTING.md) and [historical reports](docs/history/) |
| Contribution guidance | [CONTRIBUTING.md](CONTRIBUTING.md) |

The root of this repository contains the **editable source** and **one-command Windows builder**, not the files end users must run. The [GitHub Release](https://github.com/AnlionGamer/MHP3rd-DLC-English-Localizer/releases/tag/v1.0.0) contains the compiled application.

## Credits and licensing

This is an unofficial fan-made utility, not affiliated with or endorsed by Capcom, PPSSPP, or translation contributors.

The application **source code** is provided under [GPLv3](LICENSE_GPLv3.txt). The bundled English translation catalog involves **separate third-party rights considerations**: read [THIRD_PARTY_TRANSLATION_RIGHTS.md](THIRD_PARTY_TRANSLATION_RIGHTS.md) for provenance and redistribution status. The code license alone does not establish rights to third-party translated text.

For translation and naming decisions, see [catalog editorial notes](CATALOG_EDITORIAL_NOTES.md) and the [name translation policy](NAME_TRANSLATION_POLICY.md).
