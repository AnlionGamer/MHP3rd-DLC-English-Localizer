"""Focused offline v0.5 migration and preservation regression tests.

Fixtures intentionally NOT included with shared program (contain real hunter saves).
Pass known fixture ZIP path(s) as arguments or run in this project environment.
"""
from __future__ import annotations
from pathlib import Path
from tempfile import TemporaryDirectory
import zipfile

import analyze_dlc as a
from patch_dlc import execute
from desktop_app import omissions_in_plan, summary_of



def palico_rec(plan,pid):
    return next(r for s in plan['save_sets'] for folder,c in s['containers'].items()
      for r in c.get('palico_inventory',{}).get('records',[]) if r.get('id')==pid)


def test_catalog():
    catalog,_=a.load_catalog()
    assert a.audit_catalog(catalog)=={'errors':[],'warnings':[],'blocked_records':[],'patch_ready':True}
    pal={p['id']:p for p in catalog['palicoes']}
    assert pal['ue']['en']['name']=='ｕｅ．'
    assert pal['maki']['en']['name']=='ｍａｋｉ'
    assert pal['hagitokoroo']['en']['comment']=='HagiToko! Go!'
    assert len(pal['hagitokoroo']['en']['comment'].encode('utf-16-le'))<=28
    assert pal['pieru']['editorial']['confidence'].startswith('Romanization unverified')
    print('PASS catalog quality, punctuation, editorial disclosures')


def test_gui_helpers():
    plan={'save_sets':[{'containers':{'ULJM05800':{'status':'validated','encryption':'PSP mode 5','palico_inventory':{'records':[{'status':'eligible_editorial_repair','id':'maki'}, {'status':'protected_custom_text','id':'foo'}]}}}}]}
    s=summary_of(plan)
    assert s['counts']=={'eligible_editorial_repair':1,'protected_custom_text':1}
    assert len(omissions_in_plan(plan))==1
    print('PASS GUI status summaries and explicit partial detection')


def test_previous_english_migration(src:Path):
    opts={'maki','hagitokoroo'}
    plan=a.analyze(src,False,opts)
    assert palico_rec(plan,'maki')['status']=='eligible_editorial_repair', palico_rec(plan,'maki')
    assert palico_rec(plan,'hagitokoroo')['status']=='eligible_editorial_repair',palico_rec(plan,'hagitokoroo')
    assert palico_rec(plan,'ue')['status']=='already_localized',palico_rec(plan,'ue')
    with TemporaryDirectory() as d:
        target=Path(d)/'migration_new.zip'
        output=execute(src,target,plan)
        assert len(output['edited_containers'])==1
        assert output['edited_containers'][0]['folder']=='ULJM05800'
        with zipfile.ZipFile(target) as z:
            names=z.namelist()
            assert not any('ULJM05800QST/' in n for n in names),names
            mode,inner=a.detect_psp(z.read('ULJM05800/MHP3RD.BIN'),z.read('ULJM05800/PARAM.SFO'),'ULJM05800')
            assert mode==5
            source=a.read_members(src)
            old=a.detect_psp(source['ULJM05800/MHP3RD.BIN'],source['ULJM05800/PARAM.SFO'],'ULJM05800')[1]
            before=[a.read_palico_text(old,i) for i in range(5)]
            after=[a.read_palico_text(inner,i) for i in range(5)]
            for i in range(5):assert before[i]['owner']==after[i]['owner']
            assert after[1]['name']=='ｍａｋｉ' and before[1]['name']=='maki'
            assert after[3]['comment']=='HagiToko! Go!' and before[3]['comment']=='Go all out!'
            assert after[0]['name']=='ｕｅ．' and after[0]==before[0]
            assert inner[5*0xa0:-24]==old[5*0xa0:-24], 'A non-Palico byte changed!'
            assert inner[-4:]==old[-4:]
        again=a.analyze(target,False,opts)
        assert palico_rec(again,'maki')['status']=='already_localized'
        assert palico_rec(again,'hagitokoroo')['status']=='already_localized'
        # File creation is output-only, NEVER replace the original zip.
        assert src.exists()
        print('PASS previous v0.4.1 English migration, encrypted mode-5, original data, source unchanged')


def test_original_japanese(src:Path):
    plan=a.analyze(src,False,{'maki','ue','hagitokoroo'})
    for pid in ['maki','ue','hagitokoroo']:
        assert palico_rec(plan,pid)['status']=='eligible_translation',(pid,palico_rec(plan,pid)['status'])
    with TemporaryDirectory() as d:
        target=Path(d)/'original_names.zip'
        result=execute(src,target,plan)
        assert len(result['edited_containers'])==1
        with zipfile.ZipFile(target) as z:
            mode,inner=a.detect_psp(z.read('ULJM05800/MHP3RD.BIN'),z.read('ULJM05800/PARAM.SFO'),'ULJM05800')
            assert mode==5
            by={a.read_palico_text(inner,i)['name']:a.read_palico_text(inner,i) for i in range(5)}
            assert by['ｍａｋｉ']['comment']=='Love me lots!'
            assert by['ｕｅ．']['comment']=='Count on ino.!'
            assert by['HagiTokoRoo']['comment']=='HagiToko! Go!'
    print('PASS original fullwidth nicknames preserved on encrypted save')


def run():
    import argparse
    parser=argparse.ArgumentParser(description='Offline regression tests; private saves are optional and never redistributed')
    parser.add_argument('--legacy',type=Path,help='Optional known v0.4.1 output ZIP for editorial migration')
    parser.add_argument('--original',type=Path,help='Optional original encrypted MHP3rd DLC ZIP for fullwidth fidelity')
    args=parser.parse_args()
    test_catalog()
    test_gui_helpers()
    if args.legacy:test_previous_english_migration(args.legacy)
    else:print('SKIP private prior-output migration test (pass --legacy ZIP)')
    if args.original:test_original_japanese(args.original)
    else:print('SKIP private encrypted-input test (pass --original ZIP)')

if __name__=='__main__':run()
