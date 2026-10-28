"""v0.6.2 fullwidth name policy, legacy repair and non-destructive fixture checks."""
from __future__ import annotations
import argparse,copy,hashlib,tempfile,zipfile
from pathlib import Path
import analyze_dlc as a
from patch_dlc import patch_palico_container,game_checksum,execute,assert_allowed_diff

catalog,_=a.load_catalog()
cat=catalog['palicoes']
refs={p['id']:p for p in cat}
IDS=set(refs)

def synthetic(style='ja'):
    data=bytearray(4000)
    for i,p in enumerate(cat):
        for fld,(offset,units) in a.PALICO_FIELDS.items():
            value=p['ja'][fld] if style=='ja' else p['en'][fld]
            if style=='legacy':value=p.get('legacy_en',{}).get(fld,value)
            b=value.encode('utf-16le')+b'\0\0'
            assert len(b)<=units*2,(p['id'],fld,value)
            data[i*160+offset:i*160+offset+units*2]=b.ljust(units*2,b'\0')
    data[-24:-4]=game_checksum(bytes(data))
    return bytes(data)

def fast_checks():
    assert not a.audit_catalog(catalog)['errors']
    for id in ('ue','maki','koshiimo'):
        assert refs[id]['en']['owner']==refs[id]['ja']['owner']
        assert refs[id]['en']['owner'].isascii() is False
    for id in ('ue','maki'):
        assert refs[id]['en']['name']==refs[id]['ja']['name']
    bad=copy.deepcopy(catalog)
    next(p for p in bad['palicoes'] if p['id']=='ue')['en']['owner']='ino.'
    assert any(e['record']=='ue' and e['field']=='owner' for e in a.audit_catalog(bad)['errors'])
    print('PASS catalog fullwidth policy and future-regression validation',flush=True)
    for source in ('ja','legacy'):
        before=synthetic(source)
        report=a.inspect_palicoes(before,cat,IDS)
        statuses=[r['status'] for r in report['records']]
        assert all(s in ('eligible_translation','eligible_editorial_repair','already_localized') for s in statuses),(source,statuses)
        result,edits=patch_palico_container(before,report['records'],cat)
        assert len(edits)==(5 if source=='ja' else 4),(source,edits)
        allowed=[]
        for i,p in enumerate(cat):
            assert a.read_palico_text(result,i)==p['en'],(source,i)
            for fld,(offset,units) in a.PALICO_FIELDS.items():
                allowed.append((i*160+offset,i*160+offset+units*2))
        allowed.append((len(before)-24,len(before)-4))
        assert_allowed_diff(before,result,allowed,'synthetic main')
        recheck=a.inspect_palicoes(result,cat,IDS)
        assert all(r['status']=='already_localized' for r in recheck['records'])
        print('PASS',source,'5 original/legacy records localized; reanalysis already localized',flush=True)
    # Legacy v0.6.1 already used ASCII creator names. Confirm those become fullwidth,
    # with no changes to comments and already-correct Japanese-origin Meowsters.
    before=synthetic('legacy')
    result,_=patch_palico_container(before,a.inspect_palicoes(before,cat,IDS)['records'],cat)
    for i,p in enumerate(cat):
        old=a.read_palico_text(before,i)
        new=a.read_palico_text(result,i)
        if p['id'] in ('ue','maki','koshiimo'):
            assert old['owner']!=new['owner'] and new['owner']==p['ja']['owner']
        else:assert old['owner']==new['owner']
    print('PASS v0.6.1 ASCII owner repair with Japanese-script owner credits left intact',flush=True)
    custom=bytearray(synthetic('ja'))
    pos=a.PALICO_FIELDS['owner'][0]
    units=a.PALICO_FIELDS['owner'][1]
    custom[pos:pos+units*2]=('CustomOwner'.encode('utf-16le')+b'\0\0').ljust(units*2,b'\0')
    rows=a.inspect_palicoes(bytes(custom),cat,IDS)['records']
    assert rows[0]['status']=='protected_custom_text',rows[0]
    assert len([r for r in rows if r['status']=='eligible_translation'])==4
    print('PASS custom Meowster protection',flush=True)

def live_checks(path:Path,expected_mode:int):
    source_sha=hashlib.sha256(path.read_bytes()).hexdigest()
    plan=a.analyze(path,False,IDS,True)
    container=plan['save_sets'][0]['containers']['ULJM05800']
    assert container['encryption']==('unencrypted' if expected_mode==0 else f'PSP mode {expected_mode}')
    expected=container['palico_inventory']['records']+container['hired_palico_inventory']['records']
    assert len(expected)==15,(len(expected),path)
    assert all(r['status'] in ('eligible_translation','eligible_editorial_repair','already_localized') for r in expected)
    files=a.read_members(path)
    mode,base=a.detect_psp(files['ULJM05800/MHP3RD.BIN'],files['ULJM05800/PARAM.SFO'],'ULJM05800')
    assert mode==expected_mode
    with tempfile.TemporaryDirectory() as d:
        out=Path(d)/'localized.zip'
        outcome=execute(path,out,plan)
        assert len(outcome['edited_containers'])==1
        assert outcome['edited_containers'][0]['folder']=='ULJM05800'
        with zipfile.ZipFile(out) as z:
            assert 'ULJM05800/MHP3RD.BIN' in z.namelist()
            assert 'ULJM05800QST/MHP3RD.BIN' not in z.namelist()
            nowmode,now=a.detect_psp(z.read('ULJM05800/MHP3RD.BIN'),z.read('ULJM05800/PARAM.SFO'),'ULJM05800')
            assert nowmode==mode
        spans=[]
        for r in expected:
            begin=r['slot']*0xA0 if 'hunter_slot' not in r else a.hired_record_offset(r['hunter_slot'],r['slot'])
            actual=a.read_palico_text(now[begin:begin+0xA0],0)
            ref=refs[r['id']]
            assert actual==ref['en'],(r['id'],actual,ref['en'])
            for offset,units in a.PALICO_FIELDS.values():
                spans.append((begin+offset,begin+offset+units*2))
        spans.append((len(base)-24,len(base)-4))
        assert_allowed_diff(base,now,spans,'main save')
        followup=a.analyze(out,False,IDS,True)
        records=followup['save_sets'][0]['containers']['ULJM05800']
        assert all(r['status']=='already_localized' for r in records['palico_inventory']['records']+records['hired_palico_inventory']['records'])
        assert hashlib.sha256(path.read_bytes()).hexdigest()==source_sha
        print('PASS real backup',path.name,'mode',mode,'15 Palico records, original byte allowlist and output reanalysis',flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--encrypted',type=Path);p.add_argument('--mixed',type=Path)
    args=p.parse_args()
    fast_checks()
    if args.encrypted:live_checks(args.encrypted,5)
    if args.mixed:live_checks(args.mixed,0)
