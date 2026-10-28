#!/usr/bin/env python3
"""Conservative backed-up application of an independently verified DLC output ZIP.

This module is NOT called by the binary patcher. It is an optional, explicitly
approved installer for local PPSSPP filesystem save folders. Backup creation,
per-file source hashes, staging, rollback and final byte verification are required.
"""
from __future__ import annotations
import hashlib
import json
import os
import shutil
import recovery
from pathlib import Path, PurePosixPath
import subprocess
import tempfile
import zipfile
import analyze_dlc as a


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def _member_path(source:Path, relative:str)->Path:
    bits=PurePosixPath(relative).parts
    if len(bits)<2 or bits[-2] not in a.FOLDERS or bits[-1] not in ('MHP3RD.BIN','PARAM.SFO'):
        raise ValueError('Installer refused unexpected DLC path: '+relative)
    root=source.parent if source.name in a.FOLDERS else source
    target=root.joinpath(*bits)
    if root.resolve() not in target.resolve().parents:
        raise ValueError('Installer refused a path outside selected saves')
    if target.is_symlink() or not target.is_file() or target.parent.is_symlink():
        raise ValueError('Installer refused missing or linked save file: '+str(target))
    return target


def _game_is_running()->bool:
    if os.name!='nt':return False
    result=subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True,timeout=15)
    if result.returncode!=0:raise ValueError('Unable to confirm PPSSPP is closed. Close PPSSPP and retry.')
    import csv, io
    for row in csv.reader(io.StringIO(result.stdout)):
        if row and 'ppsspp' in row[0].casefold():return True
    return False


def _atomic_new_zip(destination:Path,items:dict[str,bytes])->None:
    destination.parent.mkdir(parents=True,exist_ok=True)
    if destination.exists():raise ValueError('Backup already exists; nothing overwritten')
    fd,temp=tempfile.mkstemp(prefix='.mhp3rd_backup_',suffix='.tmp',dir=destination.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            with zipfile.ZipFile(stream,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for name,data in sorted(items.items()):z.writestr(name,data)
            stream.flush();os.fsync(stream.fileno())
        with zipfile.ZipFile(temp,'r') as z:
            if z.testzip() is not None or set(z.namelist())!=set(items):
                raise ValueError('Backup archive failed validation')
            for key,data in items.items():
                if z.read(key)!=data:raise ValueError('Backup contents differ from original')
        os.link(temp,destination) # no-clobber
        recovery._fsync_folder(destination.parent)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def _atomic_replace_bytes(target:Path,content:bytes)->None:
    fd,temp=tempfile.mkstemp(prefix='.mhp3rd_staged_',suffix='.tmp',dir=target.parent)
    try:
        with os.fdopen(fd,'wb') as stream:
            stream.write(content);stream.flush();os.fsync(stream.fileno())
        if sha(Path(temp).read_bytes())!=sha(content):raise ValueError('Staged file verification failed')
        os.replace(temp,target)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def install_verified_zip(source:Path, package:Path, plan:dict, backup_path:Path)->dict:
    """Install approved ZIP into source folder after creating a VERIFIED recovery backup.

    The source must be a real save directory. Each original edited BIN/SFO is
    snapshotted, the entire changed save folder is archived (including icons),
    and only the recognized BIN/SFO pairs are replaced. Rollback tries to restore
    every previously replaced file if an error occurs. The recovery backup is
    retained even after success. Never call this without explicit GUI approval.
    """
    source=Path(source).resolve();package=Path(package).resolve();backup_path=Path(backup_path).resolve()
    if not source.is_dir():raise ValueError('Direct installation requires a PPSSPP save folder, not a ZIP')
    if _game_is_running():raise ValueError('PPSSPP is running. Close the emulator completely before installing.')
    pending=recovery.pending_for_source(source)
    if pending:
        raise ValueError('An interrupted installation must be restored before another install. Run the Recovery tool for: '+str(pending[0].parent))
    if source in package.parents or source in backup_path.parents or package==backup_path:
        raise ValueError('Output and backup must be outside the PPSSPP save tree')
    if not package.is_file() or not zipfile.is_zipfile(package):raise ValueError('Verified localization ZIP is missing')
    with zipfile.ZipFile(package) as z:
        if z.testzip() is not None:raise ValueError('Localization package CRC failure')
        report=json.loads(z.read('DLC_PATCH_REPORT.json'))
        if report.get('source_plan_fingerprint')!=plan.get('plan_fingerprint'):
            raise ValueError('Localization package does not match approved analysis')
        patches={}
        for edit in report['edited_containers']:
            prefix=edit['save_set'];folder=edit['folder']
            stem=(prefix+'/' if prefix!='.' else '')+folder
            if folder not in a.FOLDERS:raise ValueError('Unrecognized destination folder')
            for fname in ('MHP3RD.BIN','PARAM.SFO'):
                name=stem+'/'+fname
                if name in patches:raise ValueError('Duplicate install target')
                patches[name]=z.read(name)
            if sha(patches[stem+'/MHP3RD.BIN'])!=edit['output_bin_sha256']:
                raise ValueError('Localized BIN checksum disagrees with patch report')
        if not patches:raise ValueError('Nothing was localized; install refused')
    before=a.read_members(source)
    container_hashes={}
    for save_set in plan['save_sets']:
        prefix=save_set['save_set']
        for folder,details in save_set['containers'].items():
            stem=(prefix+'/' if prefix!='.' else '')+folder
            for fname,want in details.get('source_hashes',{}).items():
                container_hashes[stem+'/'+fname]=want
    for key,expected in container_hashes.items():
        if key not in before or sha(before[key])!=expected:
            raise ValueError('Source changed after Analyze; no files installed')
    targets={name:_member_path(source,name) for name in patches}
    originals={name:before[name] for name in patches}
    savedata_roots={target.parent.parent.resolve() for target in targets.values()}
    if len(savedata_roots)!=1:
        raise ValueError('Direct installation across multiple SAVEDATA roots is not supported. Select one SAVEDATA location.')
    savedata=next(iter(savedata_roots))
    # Make sure the original saves and the replacement can fit side-by-side on disk.
    total_bytes=sum(len(v) for v in patches.values())
    for root in {savedata,backup_path.parent,package.parent}:
        root.mkdir(parents=True,exist_ok=True) if root!=savedata else None
        if shutil.disk_usage(root).free < max(8*1024*1024,3*total_bytes):
            raise ValueError('Insufficient free disk space for safely staging localization and recovery at: '+str(root))
    if backup_path.exists():raise ValueError('Recovery backup path already exists; no files installed')
    for name,old in originals.items():
        if sha(targets[name].read_bytes())!=sha(old):
            raise ValueError('Source changed before backup; no files installed')
    backup_items={}
    for folder in sorted({target.parent for target in targets.values()},key=str):
        for entry in folder.iterdir():
            if entry.is_symlink() or not entry.is_file() or entry.stat().st_size>a.MAX_MEMBER_BYTES:
                raise ValueError('Unsupported companion file in backup: '+str(entry))
            key=entry.relative_to(source.parent if source.name in a.FOLDERS else source).as_posix()
            backup_items[key]=entry.read_bytes()
    manifest={'type':'MHP3rd pre-localization recovery backup','approved_plan_fingerprint':plan['plan_fingerprint'],
              'sha256':{key:sha(value) for key,value in sorted(backup_items.items())}}
    backup_items['BACKUP_MANIFEST.json']=(json.dumps(manifest,indent=2)+'\n').encode('utf-8')
    _atomic_new_zip(backup_path,backup_items)
    # Do not install if any source changed while backup was being created.
    if {k:sha(v) for k,v in a.read_members(source).items()}!={k:sha(v) for k,v in before.items()}:
        raise ValueError('Source changed while backing up; original files left untouched')
    if _game_is_running():raise ValueError('PPSSPP opened during backup; install refused')
    # This fsynced journal is written AFTER the complete verified backup and BEFORE
    # touching any save file. A forced shutdown leaves a recoverable operation.
    root_names={name:targets[name].relative_to(savedata).as_posix() for name in patches}
    journal=recovery.create_journal(
        savedata,backup_path,{root_names[k]:v for k,v in patches.items()},
        {root_names[k]:v for k,v in originals.items()},root_names and {root_names[k]:k for k in patches})
    completed=[]
    try:
        for name,target in sorted(targets.items()):
            if sha(target.read_bytes())!=sha(originals[name]):
                raise ValueError('Save changed while installation was in progress')
            _atomic_replace_bytes(target,patches[name]);completed.append(name)
        for name,target in targets.items():
            if sha(target.read_bytes())!=sha(patches[name]):
                raise ValueError('Installed file differs from independently verified package')
        # Read the installed files through the original analyzer. It must recognize
        # every installed container and find no new structural defects.
        final=a.analyze(source,plan['options'].get('quests',True),
                        set(plan['options'].get('palico_ids',[])),plan['options'].get('hired_palicoes',False))
        if final['catalog_quality']['errors']:
            raise ValueError('Post-install catalog validation failed')
        final_sets={item['save_set']:item['containers'] for item in final['save_sets']}
        for item in final['save_sets']:
            for container in item['containers'].values():
                if container['status'] not in ('validated','partially_recognized'):
                    raise ValueError('Post-install save decoding failed')
        for edited in report['edited_containers']:
            container=final_sets.get(edited['save_set'],{}).get(edited['folder'])
            if container is None:raise ValueError('Post-install localized container missing')
            for row in edited['edited_records']:
                if edited['folder']=='ULJM05800QST':inventory='quest_inventory'
                elif row.get('scope')=='recruited':inventory='hired_palico_inventory'
                else:inventory='palico_inventory'
                matched=[item for item in container.get(inventory,{}).get('records',[])
                         if item.get('id')==row['id'] and item.get('slot')==row['slot']
                         and (inventory!='hired_palico_inventory' or item.get('hunter_slot')==row['hunter_slot'])]
                if len(matched)!=1 or matched[0]['status']!='already_localized':
                    raise ValueError('Post-install localized record did not re-analyze as localized: '+row['id'])
        recovery.clear_journal(journal)
        return {'result':'installed','backup':str(backup_path),'package':str(package),
                'installed_files':sorted(patches),'backup_files':len(backup_items)-1,
                'post_install_fingerprint':final['plan_fingerprint']}
    except BaseException as err:
        failure=[]
        for name in reversed(completed):
            try:_atomic_replace_bytes(targets[name],originals[name])
            except BaseException as restore_error:failure.append(f'{name}: {restore_error}')
        # Only clear pending recovery when EVERY edited file has its original bytes.
        for name,target in targets.items():
            try:
                if sha(target.read_bytes())!=sha(originals[name]):
                    failure.append(f'{name}: cannot verify restored original bytes')
            except OSError as check_error:failure.append(f'{name}: {check_error}')
        if not failure:
            try:recovery.clear_journal(journal)
            except Exception as clear_error:failure.append('Unable to clear recovery journal: '+str(clear_error))
        if failure:
            raise RuntimeError('INSTALL FAILED; AUTOMATIC RESTORE INCOMPLETE. Do not start PPSSPP. '+
                'Recovery backup: '+str(backup_path)+'; restore errors: '+'; '.join(failure)) from err
        raise ValueError(f'Installation failed and original edited files restored. Recovery backup: {backup_path}. Reason: {err}') from err
