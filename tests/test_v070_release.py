"""Release-candidate safety regressions; fixtures private and never packaged."""
from __future__ import annotations
import argparse
from pathlib import Path
import json
import os
import subprocess
import sys
import tempfile
import zipfile
import hashlib
import analyze_dlc as a
from patch_dlc import execute
import safe_install
import recovery
from report_privacy import redact_report
from html_report import render_html


def privacy():
    sample={'catalog_sha256':'PUBLIC_CATALOG_CHECKSUM','catalog_quality':{'errors':[],'warnings':[]},
        'analyzer_version':'0.6.3','options':{'quests':True,'palico_ids':[],'hired_palicoes':True},
        'source_path':'C:/PRIVATE/ACCOUNT/secret','source_archive_sha256':'PRIVATEHASH',
       'plan_fingerprint':'PRIVATEGAMEHASH','limitations':['PRIVATE_TEXT'],
       'save_sets':[{'save_set':'PRIVATE_SET','preview':{'record_status_counts':{},'partial_approval_required':False},
         'containers':{'ULJM05800':{'status':'validated','errors':['PERSONAL_INFORMATION'],
           'source_hashes':{'MHP3RD.BIN':'PRIVATEHASH'},'inner_sha256':'PRIVATEHASH',
           'downloaded_palico_references':['PERSONAL_INFORMATION.dlo'],
           'palico_inventory':{'records':[{'id':'maki','name':'PLAYER_GIVEN_NAME','original_creator':'PRIVATE_CREATOR','status':'protected_custom_text','planned_action':'preserve_unchanged'}]},
           'hired_palico_inventory':{'records':[{'id':'maki','name':'PRIVATE_HIRED_NAME','original_comment':'PRIVATE_COMMENT','owner':'PRIVATE_MEOWSTER',
                                               'proposed_english_name':'known','status':'protected_custom_text','planned_action':'preserve_unchanged'}]}}}}]}
    clean=redact_report(sample)
    serialized=json.dumps(clean,ensure_ascii=False)+render_html(clean)
    for needle in ('PRIVATEHASH','PRIVATE_HIRED_NAME','PRIVATE_MEOWSTER','PRIVATE_CREATOR','PRIVATE_COMMENT','PRIVATE_SET','PLAYER_GIVEN_NAME','PERSONAL_INFORMATION'):
        assert needle not in serialized,needle
    assert clean['save_sets'][0]['containers']['ULJM05800']['hired_palico_inventory']['records'][0]['id']=='maki'
    assert sample['save_sets'][0]['containers']['ULJM05800']['hired_palico_inventory']['records'][0]['name']=='PRIVATE_HIRED_NAME'
    print('PASS shareable HTML/JSON redacts recruited, downloaded, other private text',flush=True)


def synthetic():
    with tempfile.TemporaryDirectory() as td:
        root=Path(td);savedata=root/'SAVEDATA';savedata.mkdir()
        before={};after={}
        for fold in ('ULJM05800','ULJM05800QST'):
            folder=savedata/fold;folder.mkdir()
            (folder/'ICON0.PNG').write_bytes(b'icon')
            for filename in ('MHP3RD.BIN','PARAM.SFO'):
                key=f'{fold}/{filename}';before[key]=(key+' ORIGINAL').encode();after[key]=(key+' PATCHED').encode()
                (folder/filename).write_bytes(before[key])
        backup_items={**before,**{f'{p}/ICON0.PNG':b'icon' for p in ('ULJM05800','ULJM05800QST')}}
        backup_items['BACKUP_MANIFEST.json']=json.dumps({'sha256':{name:recovery.sha(blob) for name,blob in backup_items.items()}}).encode()
        backup=root/'Backups'/'recovery.zip';safe_install._atomic_new_zip(backup,backup_items)
        journal=recovery.create_journal(savedata,backup,after,before,{k:k for k in before})
        safe_install._atomic_replace_bytes(savedata/'ULJM05800'/'MHP3RD.BIN',after['ULJM05800/MHP3RD.BIN'])
        assert recovery.pending_for_source(savedata)==[journal]
        out=recovery.restore_pending(journal)
        assert out['result']=='restored'
        assert not journal.exists()
        assert all((savedata/key).read_bytes()==old for key,old in before.items())
        assert backup.exists()
        print('PASS simulated interrupted multi-file write recovered exactly; backup retained',flush=True)
        journal=recovery.create_journal(savedata,backup,after,before,{k:k for k in before})
        (savedata/'ULJM05800'/'MHP3RD.BIN').write_bytes(b'UNRELATED NEW DATA')
        try:recovery.restore_pending(journal)
        except ValueError as exc:assert 'independently modified' in str(exc)
        else:raise AssertionError('Recovery overwrote independent edits')
        assert (savedata/'ULJM05800'/'MHP3RD.BIN').read_bytes()==b'UNRELATED NEW DATA'
        assert journal.exists()
        print('PASS recovery refuses to overwrite edits outside approved before/after hashes',flush=True)


def crash_worker(args):
    src=Path(args.savedata);package=Path(args.package);backup=Path(args.backup)
    plan=json.loads(Path(args.plan).read_text('utf-8'))
    old=safe_install._atomic_replace_bytes
    def crash(target,data):
        old(target,data)
        os._exit(79)  # simulate power loss with no Python exception/rollback handlers
    safe_install._atomic_replace_bytes=crash
    safe_install.install_verified_zip(src,package,plan,backup)
    raise AssertionError('Expected forced termination')


def fixture_run(fixture:Path):
    with tempfile.TemporaryDirectory(prefix='MHP3rd_rc_') as td:
        root=Path(td);savedata=root/'Portable'/'PSP'/'SAVEDATA';savedata.mkdir(parents=True)
        with zipfile.ZipFile(fixture) as z:
            for key in z.namelist():
                if key.endswith('/'):continue
                if not key.startswith(('ULJM05800/','ULJM05800QST/')):continue
                path=savedata/key;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(z.read(key))
        original=a.read_members(savedata);digest=recovery.sha(fixture.read_bytes())
        plan=a.analyze(savedata,True,{'maki'},True)
        package=root/'Output'/'patched.zip';result=execute(savedata,package,plan)
        assert result['edited_containers']
        assert original==a.read_members(savedata)
        planfile=root/'plan.json';planfile.write_text(json.dumps(plan,ensure_ascii=False),encoding='utf-8')
        backup=root/'Backups'/'interrupted.zip'
        cmd=[sys.executable,str(Path(__file__).resolve()),'--crash-worker','--savedata',str(savedata),
             '--package',str(package),'--plan',str(planfile),'--backup',str(backup)]
        result=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
        assert result.returncode==79,(result.returncode,result.stdout,result.stderr)
        assert backup.exists() and (savedata/recovery.JOURNAL).exists()
        assert a.read_members(savedata)!=original
        try:safe_install.install_verified_zip(savedata,package,plan,root/'Backups'/'must_refuse.zip')
        except ValueError as e:assert 'interrupted' in str(e)
        else:raise AssertionError('Installer did not refuse an interrupted prior operation')
        recovery.restore_pending(savedata/recovery.JOURNAL)
        assert a.read_members(savedata)==original
        assert not (savedata/recovery.JOURNAL).exists()
        print('PASS real encrypted save interrupted at process exit recovered exact original BIN/SFO bytes',flush=True)
        installed=safe_install.install_verified_zip(savedata,package,plan,root/'Backups'/'clean_install.zip')
        assert installed['result']=='installed' and not (savedata/recovery.JOURNAL).exists()
        assert a.read_members(savedata)!=original
        assert recovery.sha(fixture.read_bytes())==digest
        print('PASS clean install reanalysis and committed journal removal; private fixture untouched',flush=True)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--fixture',type=Path)
    ap.add_argument('--crash-worker',action='store_true')
    ap.add_argument('--savedata');ap.add_argument('--package');ap.add_argument('--plan');ap.add_argument('--backup')
    args=ap.parse_args()
    if args.crash_worker:crash_worker(args)
    else:
        privacy();synthetic()
        if args.fixture:fixture_run(args.fixture)
