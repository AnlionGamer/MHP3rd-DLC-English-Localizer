"""No-save-data v1.0.0 builder source invariants, with direct packager tests."""
from pathlib import Path
import hashlib
import zipfile
import tempfile

import desktop_app
import analyze_dlc
from release_packager import RELEASE, create_release, ARCHIVE_NAME

root = Path(__file__).resolve().parent.parent
assert hashlib.sha256((root/'catalog.json').read_bytes()).hexdigest() == (root/'CATALOG_SHA256.expected').read_text().strip()
assert desktop_app.VERSION == '1.0.0'
assert not analyze_dlc.audit_catalog(analyze_dlc.load_catalog()[0])['errors']
for version_resource in ('WindowsVersion_localizer.txt','WindowsVersion_recovery.txt'):
    assert (root/version_resource).read_text().count('1.0.0.0') >= 2
ps = (root/'Build_Windows_EXE.ps1').read_text()
for term in ('--version-file','--add-data','CATALOG_SHA256.expected', 'MHP3rd_Recovery.exe',
             'release_packager.py','--exe-dir', '--output-dir', 'Release'):
    assert term in ps,term
assert 'Package_Windows_Release.ps1' not in ps
assert not (root/'Package_Windows_Release.ps1').exists()
assert len(RELEASE) == 7
assert list(RELEASE) == [
    'MHP3rd_DLC_Localizer.exe', 'MHP3rd_Recovery.exe', 'README.md',
    'Documentation/Recovery_Guide.md', 'Documentation/LICENSE_GPLv3.txt',
    'Documentation/THIRD_PARTY_TRANSLATION_RIGHTS.md', 'Documentation/Release_Notes_v1.0.0.md'
]
with tempfile.TemporaryDirectory() as folder:
    work = Path(folder)
    exes=work/'exes';exes.mkdir()
    for name in ('MHP3rd_DLC_Localizer.exe','MHP3rd_Recovery.exe'):
        (exes/name).write_bytes(b'MZ'+bytes(range(256))*32 + name.encode())
    archive, hash_file = create_release(root,exes,work/'Release')
    assert archive.name == ARCHIVE_NAME
    assert hash_file.read_text().startswith(hashlib.sha256(archive.read_bytes()).hexdigest()+' *')
    assert sorted(f.name for f in (work/'Release').iterdir()) == sorted([ARCHIVE_NAME,ARCHIVE_NAME+'.sha256'])
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.namelist() == list(RELEASE)
        assert zipped.testzip() is None
        for name in ('MHP3rd_DLC_Localizer.exe','MHP3rd_Recovery.exe'):
            assert zipped.read(name)==(exes/name).read_bytes()
        assert not any('BUILD_' in n or 'CATALOG' in n or '.py' in n for n in zipped.namelist())
    # Simulate re-running a clean build over an existing release ZIP.
    archive2, hash2 = create_release(root,exes,work/'Release')
    assert archive2==archive and hash2==hash_file
    # Missing recovery executable must fail without corrupting prior release.
    original = archive.read_bytes()
    (exes/'MHP3rd_Recovery.exe').unlink()
    try: create_release(root,exes,work/'Release')
    except FileNotFoundError: pass
    else: raise AssertionError('Expected missing exe refusal')
    assert archive.read_bytes()==original
print('PASS v1.0.0 frozen catalog, build metadata, seven-file end-user package, atomic repackaging')
