# Developer tests

Run tests from the repository root with the root folder on `PYTHONPATH`.

```powershell
$env:PYTHONPATH = (Get-Location).Path
python tests/test_v1_release_metadata.py
```

See [docs/TESTING.md](../docs/TESTING.md) for further tests and private-fixture precautions.
