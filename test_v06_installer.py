"""v0.6 backed-up direct install and rollback regression tests.

Requires a privately supplied existing encrypted MHP3rd save ZIP; no private
save data is bundled with the public application.
"""
import argparse
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile
import sys
import analyze_dlc as a
from patch_dlc import execute
import safe_install as installer


def run_fixture(fixture:Path):
    with TemporaryDirectory(prefix='MHP3rd_v06_') as td:
        tmp=Path(td);savedata=tmp/'Portable'/'PSP'/'SAVEDATA';savedata.mkdir(parents=True)
        with zipfile.ZipFile(fixture) as z:
            for member in z.namelist():
                if member.endswith('/'):continue
                assert member.startswith(('ULJM05800/','ULJM05800QST/'))
                dest=savedata/member;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(z.read(member))
        sourcehash=installer.sha(fixture.read_bytes())
        old=a.read_members(savedata)
        plan=a.analyze(savedata,True,{'maki'},True)
        package=tmp/'Results'/'localized.zip'
        report=execute(savedata,package,plan)
        assert report['edited_containers']
        assert a.read_members(savedata)==old
        print('PASS staged 66-quest + selected Palico output, source untouched',flush=True)
        orig=installer._atomic_replace_bytes
        fired=[False];num=[0]
        def raise_once(target,content):
            num[0]+=1
            if num[0]==2 and not fired[0]:
                fired[0]=True
                raise PermissionError('synthetic filesystem write failure')
            return orig(target,content)
        installer._atomic_replace_bytes=raise_once
        try:
            try:installer.install_verified_zip(savedata,package,plan,tmp/'Backups'/'rollback_fixture.zip')
            except ValueError as exc:assert 'restored' in str(exc),str(exc)
            else:raise AssertionError('Injected installation error was not refused')
        finally:installer._atomic_replace_bytes=orig
        assert fired[0]
        assert a.read_members(savedata)==old, 'Rollback did not restore original savedata bytes'
        assert (tmp/'Backups'/'rollback_fixture.zip').exists()
        print('PASS artificial mid-install failure restored exact original save bytes',flush=True)
        result=installer.install_verified_zip(savedata,package,plan,tmp/'Backups'/'originals.zip')
        assert result['result']=='installed'
        assert a.read_members(savedata)!=old
        assert (tmp/'Backups'/'originals.zip').exists()
        after=a.analyze(savedata,True,{'maki'},True)
        assert after['catalog_quality']['errors']==[]
        selected=[]
        for group in after['save_sets']:
            for container in group['containers'].values():
                for inventory in ('quest_inventory','palico_inventory','hired_palico_inventory'):
                    selected.extend(row for row in container.get(inventory,{}).get('records',[]) if row.get('id')=='maki')
        assert selected and all(row['status']=='already_localized' for row in selected)
        with zipfile.ZipFile(result['backup']) as backup:
            assert backup.testzip() is None
            for name,data in old.items():
                if name in backup.namelist():assert backup.read(name)==data
        assert installer.sha(fixture.read_bytes())==sourcehash
        print('PASS installed files re-analyze as localized; verified backups reproduce original bytes',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);v=p.parse_args()
    run_fixture(v.fixture)
