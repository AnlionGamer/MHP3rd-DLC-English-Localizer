"""Offline, fail-closed recovery of interrupted MHP3rd DLC installations.

No catalog, game decoder, prior analysis, or user character data is required.
Pending journals reside in the SAVEDATA folder beside ULJM05800 / ULJM05800QST.
The verified backup ZIP lives separately, outside the game save tree.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import tempfile
import zipfile

JOURNAL = '.mhp3rd_localizer_pending.json'
FOLDERS = {'ULJM05800','ULJM05800QST'}
FILENAMES = {'MHP3RD.BIN','PARAM.SFO'}


def sha(blob:bytes)->str:
    return hashlib.sha256(blob).hexdigest()


def _fsync_folder(folder:Path):
    if os.name!='nt':
        fd=os.open(folder,os.O_RDONLY)
        try:os.fsync(fd)
        finally:os.close(fd)


def _allowed_relative(value:str)->bool:
    p=PurePosixPath(value)
    return (not p.is_absolute() and not any(t in ('.','..') for t in p.parts)
            and len(p.parts)==2 and p.parts[0] in FOLDERS and p.parts[1] in FILENAMES
            and '\\' not in value and ':' not in value)


def _allowed_backup_member(key:str)->bool:
    if not isinstance(key,str) or '\\' in key or ':' in key:return False
    bits=PurePosixPath(key).parts
    return (len(bits)>=2 and not PurePosixPath(key).is_absolute()
            and all(p not in ('.','..') for p in bits)
            and bits[-2] in FOLDERS and bool(bits[-1]) and len(key)<1024)


def _safe_target(savedata:Path,name:str)->Path:
    if not _allowed_relative(name):
        raise ValueError('Invalid recovery target name: '+repr(name))
    target=savedata.joinpath(*PurePosixPath(name).parts)
    if target.is_symlink() or target.parent.is_symlink() or not target.is_file():
        raise ValueError('Missing or linked recovery target: '+name)
    if savedata.resolve() not in target.resolve().parents:
        raise ValueError('Recovery target escapes selected SAVEDATA folder')
    return target


def pending_for_source(source:Path)->list[Path]:
    """Find pending journals near recognised save folders, without scanning other games."""
    source=Path(source).resolve()
    if not source.is_dir():return []
    import analyze_dlc as a
    result=[]
    for folder in a._find_save_folders(source):
        journal=folder.parent/JOURNAL
        if journal.exists() and journal not in result:result.append(journal)
    return result


def create_journal(savedata:Path,backup:Path,patches:dict[str,bytes],originals:dict[str,bytes],backup_members:dict[str,str]):
    savedata=Path(savedata).resolve()
    backup=Path(backup).resolve()
    if not savedata.is_dir():raise ValueError('SAVEDATA root is missing')
    if set(patches)!=set(originals) or set(patches)!=set(backup_members) or not patches:
        raise ValueError('Recovery journal requires matching original and changed files')
    for name in patches:_safe_target(savedata,name)
    if not backup.is_file():raise ValueError('Verified recovery backup must exist first')
    journal=savedata/JOURNAL
    if journal.exists():raise ValueError('An interrupted localization needs recovery first: '+str(journal))
    document={'schema':1,'purpose':'MHP3rd localizer interrupted-install recovery',
              'savedata_root':str(savedata),'backup_path':str(backup),
              'backup_sha256':sha(backup.read_bytes()),
              'targets':{name:{'before':sha(originals[name]),'after':sha(patches[name]),'backup_member':backup_members[name]}
                         for name in sorted(patches)}}
    fd,tmp=tempfile.mkstemp(prefix='.mhp3rd_journal_',suffix='.tmp',dir=savedata)
    try:
        with os.fdopen(fd,'w',encoding='utf-8') as f:
            json.dump(document,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
        os.link(tmp,journal)  # creation without overwriting a preexisting recovery record
        _fsync_folder(savedata)
    finally:
        if os.path.exists(tmp):os.unlink(tmp)
    return journal


def clear_journal(journal:Path):
    journal=Path(journal)
    journal.unlink()
    _fsync_folder(journal.parent)


def inspect_journal(journal:Path):
    journal=Path(journal).resolve()
    if journal.name!=JOURNAL or not journal.is_file() or journal.is_symlink():
        raise ValueError('No valid pending localizer journal at: '+str(journal))
    if journal.stat().st_size>65536:raise ValueError('Oversized recovery journal')
    data=json.loads(journal.read_text('utf-8'))
    if data.get('schema')!=1 or Path(data.get('savedata_root','')).resolve()!=journal.parent:
        raise ValueError('Recovery record location/schema mismatch')
    targets=data.get('targets')
    if not isinstance(targets,dict) or not targets or len(targets)>4:
        raise ValueError('Invalid recovery record file list')
    for name, hashes in targets.items():
        _safe_target(journal.parent,name)
        if not isinstance(hashes,dict) or set(hashes)!={'before','after','backup_member'}:
            raise ValueError('Invalid recovery hashes')
        if not _allowed_backup_member(hashes['backup_member']) or PurePosixPath(hashes['backup_member']).parts[-2:]!=PurePosixPath(name).parts:
            raise ValueError('Invalid backup member target mapping')
        for value in (hashes['before'],hashes['after']):
            if not isinstance(value,str) or len(value)!=64 or any(c not in '0123456789abcdef' for c in value):
                raise ValueError('Invalid SHA-256 in recovery journal')
    backup=Path(data['backup_path']).resolve()
    if not backup.is_file() or sha(backup.read_bytes())!=data['backup_sha256']:
        raise ValueError('Recovery backup is missing or has changed; do not open PPSSPP')
    return data


def restore_pending(journal:Path)->dict:
    """Restore all edited original BIN/SFO bytes. Never overwrite unexpected edits.

    This function is idempotent after a crash: files already restored count as
    acceptable states; after-modification bytes also count. Other bytes refuse.
    """
    journal=Path(journal).resolve()
    data=inspect_journal(journal)
    from safe_install import _atomic_replace_bytes, _game_is_running
    if _game_is_running():raise ValueError('Close PPSSPP before restoring a backup')
    backup=Path(data['backup_path'])
    originals={}
    with zipfile.ZipFile(backup,'r') as z:
        if z.testzip() is not None:raise ValueError('Recovery backup ZIP checksum failure')
        manifest=json.loads(z.read('BACKUP_MANIFEST.json'))
        hashes=manifest.get('sha256',{})
        if not isinstance(hashes,dict) or set(hashes)!=set(z.namelist())-{'BACKUP_MANIFEST.json'}:
            raise ValueError('Recovery backup manifest does not cover all files')
        for key,want in hashes.items():
            if not _allowed_backup_member(key):
                raise ValueError('Unsafe or unknown recovery backup member: '+str(key))
            if sha(z.read(key))!=want:
                raise ValueError('Recovery backup integrity mismatch: '+key)
        for name,wants in data['targets'].items():
            member=wants['backup_member']
            if member not in hashes:raise ValueError('Required original missing from backup: '+member)
            originals[name]=z.read(member)
            if sha(originals[name])!=wants['before']:
                raise ValueError('Backup does not match the original journal: '+name)
    targets={key:_safe_target(journal.parent,key) for key in originals}
    # Validate EVERY file before writing ANY of them (including partially restored states).
    for key,target in targets.items():
        current=sha(target.read_bytes())
        if current not in (data['targets'][key]['before'],data['targets'][key]['after']):
            raise ValueError('Recovery refused an independently modified file: '+str(target))
    for name,target in targets.items():
        if sha(target.read_bytes())==data['targets'][name]['before']:continue
        _atomic_replace_bytes(target,originals[name])
    if any(sha(path.read_bytes())!=data['targets'][key]['before'] for key,path in targets.items()):
        raise ValueError('Recovery verification failed; keep journal and recovery backup')
    clear_journal(journal)
    return {'result':'restored','restored_files':len(targets),'backup':str(backup),'savedata':str(journal.parent)}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Restore a pending MHP3rd localization from its verified original save backup.')
    parser.add_argument('--savedata',type=Path,required=True,help='SAVEDATA folder containing ULJM05800 and/or ULJM05800QST')
    parser.add_argument('--check',action='store_true',help='Check for an interrupted operation without restoring')
    args=parser.parse_args(argv)
    root=args.savedata.resolve()
    journal=root/JOURNAL
    if not journal.exists():
        parser.error('No interrupted localizer install found in this SAVEDATA directory')
    if args.check:
        info=inspect_journal(journal)
        print('Verified pending recovery backup:',info['backup_path'])
        print('Affected files:',', '.join(info['targets']))
    else:
        outcome=restore_pending(journal)
        print('RECOVERY SUCCESSFUL — original save bytes restored:',outcome['restored_files'],'files')
        print('Original backup retained:',outcome['backup'])

if __name__=='__main__':main()
