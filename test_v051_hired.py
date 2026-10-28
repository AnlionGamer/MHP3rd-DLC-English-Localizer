"""v0.5.1 hired promotional Palico regression checks (no private fixtures bundled).

Use: python test_v051_hired.py --encrypted <private_backup.zip>
Optionally: --mixed <unencrypted-main_encrypted-quest_backup.zip>
"""
from __future__ import annotations
import argparse, hashlib, tempfile, zipfile
from pathlib import Path
import analyze_dlc as a
from patch_dlc import execute, assert_allowed_diff, patch_palico_container


def _source_inner(path):
    files=a.read_members(path)
    return a.detect_psp(files['ULJM05800/MHP3RD.BIN'],files['ULJM05800/PARAM.SFO'],'ULJM05800')


def check_catalog_layout():
    catalog,_=a.load_catalog()
    assert a.audit_catalog(catalog)['patch_ready']
    assert len(catalog['palicoes'])==5
    assert a.hired_record_offset(0,0)==0x5DA68
    assert a.hired_record_offset(1,0)==0xBDA68
    assert a.hired_record_offset(2,0)==0x11DA68
    assert a.hired_record_offset(2,24)+0xA0 < a.EXPECTED['ULJM05800']-24
    assert catalog['palicoes'][0]['en']['name']=='ｕｅ．' or any(p['en']['name']=='ｕｅ．' for p in catalog['palicoes'])
    print('PASS catalog, limits and three documented hunter offsets',flush=True)
    return catalog


def check_original_fixture(src:Path,expected_mode:int):
    catalog,_=a.load_catalog()
    ids={p['id'] for p in catalog['palicoes']}
    mode,before=_source_inner(src)
    assert mode==expected_mode
    original_sha=hashlib.sha256(src.read_bytes()).hexdigest()
    plan_disabled=a.analyze(src,False,ids)
    assert 'hired_palico_inventory' not in plan_disabled['save_sets'][0]['containers']['ULJM05800']
    plan=a.analyze(src,False,ids,True)
    main=plan['save_sets'][0]['containers']['ULJM05800']
    recs=main['hired_palico_inventory']['records']
    assert len(recs)==10 and len([r for r in recs if r['status']=='eligible_translation'])==10,recs
    assert set(r['hunter_slot'] for r in recs)=={0,1}
    print('PASS source:',src.name,'mode',mode,'10 recognized recruited Palicoes',flush=True)
    with tempfile.TemporaryDirectory() as d:
        dest=Path(d)/'recruited_test.zip'
        outcome=execute(src,dest,plan)
        assert len(outcome['edited_containers'])==1
        assert outcome['edited_containers'][0]['folder']=='ULJM05800'
        with zipfile.ZipFile(dest) as z:
            names=z.namelist()
            assert 'ULJM05800/MHP3RD.BIN' in names
            assert not any('ULJM05800QST/' in x for x in names)
            newmode,inner=a.detect_psp(z.read('ULJM05800/MHP3RD.BIN'),z.read('ULJM05800/PARAM.SFO'),'ULJM05800')
            assert mode==newmode
        allowed=[]
        for i in range(5):
            for f in a.PALICO_LOCALIZED_FIELDS:
                ofs,units=a.PALICO_FIELDS[f]
                allowed.append((i*0xA0+ofs,i*0xA0+ofs+units*2))
        for rec in recs:
            start=a.hired_record_offset(rec['hunter_slot'],rec['slot'])
            for f in a.PALICO_LOCALIZED_FIELDS:
                ofs,units=a.PALICO_FIELDS[f]
                allowed.append((start+ofs,start+ofs+units*2))
            actual=a.read_palico_text(inner[start:start+0xA0],0)
            ref=next(cat for cat in catalog['palicoes'] if cat['id']==rec['id'])
            assert actual['name']==ref['en']['name']
            assert actual['comment']==ref['en']['comment']
            assert actual['owner']==ref['ja']['owner']
        allowed.append((len(before)-24,len(before)-4))
        assert_allowed_diff(before,inner,allowed,'main savedata')
        fresh=a.analyze(dest,False,ids,True)
        newrecs=fresh['save_sets'][0]['containers']['ULJM05800']['hired_palico_inventory']['records']
        assert all(x['status']=='already_localized' for x in newrecs),newrecs
    assert hashlib.sha256(src.read_bytes()).hexdigest()==original_sha
    print('PASS output only, unchanged source, individual name/comment verification, unmodified gameplay data',flush=True)


def check_custom_protection(src:Path):
    _,data=_source_inner(src)
    catalog,_=a.load_catalog()
    raw=bytearray(data)
    first=next(x for x in a.inspect_hired_palicoes(data,catalog['palicoes'],{'pieru'})['records'] if x['id']=='pieru' and x['hunter_slot']==0)
    pos=a.hired_record_offset(first['hunter_slot'],first['slot'])+a.PALICO_FIELDS['name'][0]
    text='MyCustomCat'.encode('utf-16le')
    raw[pos:pos+26]=text.ljust(26,b'\0')
    recs=a.inspect_hired_palicoes(bytes(raw),catalog['palicoes'],{'pieru'})['records']
    customized=next(x for x in recs if x['hunter_slot']==0 and x['id']=='pieru')
    assert customized['status']=='protected_custom_text'
    other=next(x for x in recs if x['hunter_slot']==1 and x['id']=='pieru')
    assert other['status']=='eligible_translation'
    changed,edits=patch_palico_container(bytes(raw),[],catalog['palicoes'],recs)
    assert changed[pos:pos+26]==raw[pos:pos+26]
    assert len(edits)==1 and edits[0]['hunter_slot']==1
    print('PASS custom nickname protected and other hunter can be localized independently',flush=True)


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--encrypted',type=Path)
    ap.add_argument('--mixed',type=Path)
    args=ap.parse_args()
    check_catalog_layout()
    if args.encrypted:
        check_original_fixture(args.encrypted,5)
        check_custom_protection(args.encrypted)
    else:print('SKIP encrypted fixture-dependent tests (no private source specified)')
    if args.mixed:check_original_fixture(args.mixed,0)
    else:print('SKIP mixed fixture-dependent tests (no private source specified)')


if __name__=='__main__':main()
