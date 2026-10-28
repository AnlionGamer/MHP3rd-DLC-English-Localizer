# Tests and validation

The Python regression scripts are retained in [`tests/`](../tests/). They do not ship inside the end-user Windows ZIP.

From the **repository root**, with the application's Python dependencies installed, run:

```powershell
$env:PYTHONPATH = (Get-Location).Path
python tests/test_v1_release_metadata.py
python tests/test_v062_fullwidth.py
python tests/test_v063_selection.py
python tests/test_v070_release.py
```

Some GUI tests require a graphical desktop/Tkinter. Tests requiring an actual save fixture **must receive a separately supplied private path**; the repository does not include private saves or copyrighted DLC binaries. Example:

```powershell
python tests/test_v06_installer.py --fixture "C:\path\to\your\private\save-backup.zip"
```

Do not upload private saves, analysis reports containing hunter/Palico names, or PPSSPP memory-stick folders to public issues. Provide the program version, error message (redacted if necessary), and reproducible steps instead.

Prior-version audit results are archived under [`docs/history/`](history/). Historical reports record what was tested at the time; they are not a substitute for testing newly changed code.
