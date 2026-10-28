"""Package freshly built Windows binaries into the EXACT seven-file v1.0.0 user ZIP.

Build_Windows_EXE.ps1 invokes this automatically. No old ZIP or path discovery.
Only allowlisted end-user files may enter the archive. No source data, saves,
build records, Python, tests, cache directories, or internal metadata are copied.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import tempfile
import zipfile

ARCHIVE_NAME = 'MHP3rd_DLC_Localizer_v1.0.0_Windows_x64.zip'
# ZIP member -> source-relative file. Ordering is deliberate, and frozen.
RELEASE = {
    'MHP3rd_DLC_Localizer.exe': ('exe', 'MHP3rd_DLC_Localizer.exe'),
    'MHP3rd_Recovery.exe': ('exe', 'MHP3rd_Recovery.exe'),
    'README.md': ('source', 'END_USER_README.md'),
    'Documentation/Recovery_Guide.md': ('source', 'RECOVERY_MANUAL.md'),
    'Documentation/LICENSE_GPLv3.txt': ('source', 'LICENSE_GPLv3.txt'),
    'Documentation/THIRD_PARTY_TRANSLATION_RIGHTS.md': ('source', 'THIRD_PARTY_TRANSLATION_RIGHTS.md'),
    'Documentation/Release_Notes_v1.0.0.md': ('source', 'RELEASE_NOTES_v1.0.0.md'),
}


def digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def create_release(source_root: Path, exe_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    source_root = source_root.resolve(strict=True)
    exe_dir = exe_dir.resolve(strict=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_dir = output_dir.resolve(strict=True)
    package_path = output_dir / ARCHIVE_NAME
    checksum_path = output_dir / (ARCHIVE_NAME + '.sha256')
    data: dict[str, bytes] = {}
    for member, (source_type, source_name) in RELEASE.items():
        base = exe_dir if source_type == 'exe' else source_root
        path = base / source_name
        if not path.is_file():
            raise FileNotFoundError(f'Required release file missing: {path}')
        data[member] = path.read_bytes()
        if source_type == 'exe' and not data[member].startswith(b'MZ'):
            raise ValueError(f'Not a Windows executable: {path}')
    if len(data) != 7 or len(set(data)) != 7:
        raise AssertionError('Release allowlist must contain exactly seven distinct files')

    fd, temp_name = tempfile.mkstemp(prefix='.MHP3rd-release-', suffix='.zip', dir=output_dir)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        with zipfile.ZipFile(temporary, mode='w', compression=zipfile.ZIP_DEFLATED,
                             compresslevel=9, allowZip64=True) as out:
            for member, blob in data.items():
                out.writestr(member, blob)
        with zipfile.ZipFile(temporary, 'r') as check:
            if check.testzip() is not None:
                raise ValueError('Release ZIP failed CRC validation')
            found = [item.filename for item in check.infolist() if not item.is_dir()]
            if found != list(RELEASE):
                raise ValueError(f'Unexpected release ZIP members: {found!r}')
            for name, original in data.items():
                if digest(check.read(name)) != digest(original):
                    raise ValueError(f'Release ZIP differs from source: {name}')
        zip_hash = digest(temporary.read_bytes())
        # Publish the archive only AFTER all seven members pass bytewise verification.
        os.replace(temporary, package_path)
        checksum = f'{zip_hash} *{ARCHIVE_NAME}\n'
        fd, hash_tmp_name = tempfile.mkstemp(prefix='.MHP3rd-checksum-', suffix='.txt', dir=output_dir)
        os.close(fd)
        hash_tmp = Path(hash_tmp_name)
        try:
            hash_tmp.write_text(checksum, encoding='ascii')
            os.replace(hash_tmp, checksum_path)
        finally:
            hash_tmp.unlink(missing_ok=True)
    finally:
        temporary.unlink(missing_ok=True)
    print(f'RELEASE ZIP: {package_path}')
    print(f'SHA-256:     {zip_hash}')
    print('MEMBERS (exactly 7):')
    for item in RELEASE:
        print(f'  {item}')
    return package_path, checksum_path


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='MHP3rd v1.0.0 internal end-user release packager')
    parser.add_argument('--source-root', type=Path, required=True)
    parser.add_argument('--exe-dir', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    create_release(args.source_root, args.exe_dir, args.output_dir)
