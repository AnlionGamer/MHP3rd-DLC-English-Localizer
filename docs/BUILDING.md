# Building v1.0.0 on Windows

The repository's editable application source and build inputs live in the repository root. **No existing release ZIP, manual repackaging, or compiled EXE is needed to build.**

## Requirements

- Windows x64
- Python **3.15.2**, 64-bit, accessible through `py -3.15`
- PowerShell 7
- Internet access for the builder's first dependency installation

Run this command from the repository root:

```powershell
.\Build_Windows_EXE.ps1
```

The script creates or reuses `.build-venv`, checks its pinned Python packages, verifies the frozen `catalog.json` SHA-256, builds the localizer and recovery EXEs, and packages exactly seven end-user files.

The outputs are written under `Release/`:

- `MHP3rd_DLC_Localizer_v1.0.0_Windows_x64.zip`
- `MHP3rd_DLC_Localizer_v1.0.0_Windows_x64.zip.sha256`

The ZIP includes the two standalone EXEs and five essential user/legal documents. **It excludes** Python source, build tools, logs, tests, manifests, and developer-only files. Build intermediates remain under `.build/`.

For the original build acceptance notes, see [BUILD_AND_ACCEPTANCE.md](BUILD_AND_ACCEPTANCE.md). For developer tests, see [TESTING.md](TESTING.md).

**Release note:** Keep the source code available alongside distributed GPL-covered executables; consult [the translation-rights notice](../THIRD_PARTY_TRANSLATION_RIGHTS.md) before redistributing bundled translation text.
