#!/usr/bin/env python3
"""MHP3rd HD targeted DLC localization on NEW output ZIPs only, v0.4.

Source files are read-only. This code requires a precise analyze fingerprint and
verifies the decoded data has changed only inside explicitly permitted DLC text
fields, pointer tables and integrity fields. No PPSSPP in-game test is implied.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import struct
import tempfile
import zipfile

from mh_inner_cipher import dec, enc
from stage2_extract import KEY, QUEST_SIZE, mh_decrypt_slot, psp_stream, file_hash
import analyze_dlc as a


def game_checksum(clear: bytes) -> bytes:
    data=bytearray(clear)
    data[-36:-16]=a.GAME_SHA_KEY
    return hashlib.sha1(data[:-16]).digest()


def assert_allowed_diff(before: bytes, after: bytes, spans: list[tuple[int,int]], scope: str) -> int:
    if len(before)!=len(after):raise ValueError(f'{scope}: size changed')
    changed=0
    for index, (x,y) in enumerate(zip(before,after)):
        if x!=y:
            changed+=1
            if not any(begin<=index<end for begin,end in spans):
                raise ValueError(f'{scope}: prohibited change at offset 0x{index:X}')
    return changed


def field_bytes(text: str, units: int) -> bytes:
    if '\x00' in text:raise ValueError('Unexpected embedded NUL in Palico translation')
    b=text.encode('utf-16le','strict')
    if len(b)+2>units*2:raise ValueError('English Palico text exceeds original field allocation')
    return b.ljust(units*2,b'\0')


def valid_quest_slot(slot: bytes, quest_id: str):
    parsed=mh_decrypt_slot(slot)
    if parsed is None:raise ValueError('Missing selected quest '+quest_id)
    decoded,valid,_,full=parsed
    if not valid or full>QUEST_SIZE:raise ValueError('Invalid length '+quest_id)
    if hashlib.sha1(decoded[32:full]+a.QUEST_SHA_KEY).digest()!=decoded[12:32]:
        raise ValueError('Failed quest checksum '+quest_id)
    if bytes(mh_decrypt_slot(bytes(decoded))[0])!=slot:
        raise ValueError('Failed quest cipher verification '+quest_id)
    ident=slot[-16:].split(b'\0',1)[0].decode('ascii','strict')
    if ident!=quest_id:raise ValueError('Selected quest ID changed unexpectedly')
    return bytes(decoded),full


def repack_quest(slot: bytes, quest_id: str, reference: dict) -> tuple[bytes,dict]:
    old,full=valid_quest_slot(slot,quest_id)
    pointer, originals=a.quest_fields(old,full)
    if pointer+24>full or pointer>QUEST_SIZE:raise ValueError('Invalid quest pointer region')
    if tuple(a.FIELDS)!=tuple(reference['fields']):raise ValueError('Catalog field mismatch')
    english=[reference['fields'][f]['en'] for f in a.FIELDS]
    for f,actual in zip(a.FIELDS, originals):
        ref=reference['fields'][f]
        if actual not in (ref['ja'],ref['en'],ref.get('legacy_en')):
            raise ValueError(f'Customized {quest_id}/{f}; cannot automatically localize')
    if originals==english:return slot,{'id':quest_id,'action':'already_localized','changed_bytes':0}
    b=bytearray(old)
    # The entire approved *existing* text allocation is rewritten. Never relocate
    # mission settings, reward tables, monster stats, or quest record padding.
    b[0xfc:pointer]=b'\0'*(pointer-0xfc)
    cursor=0xfc
    positions=[]
    for f,txt in zip(a.FIELDS,english):
        cursor=(cursor+3)&~3
        encoded=txt.encode('utf-8','strict')
        if b'\0' in encoded or cursor+len(encoded)+1>pointer:
            raise ValueError(f'{quest_id}/{f}: translation does not fit existing quest text area')
        b[cursor:cursor+len(encoded)]=encoded
        b[cursor+len(encoded)]=0
        positions.append(cursor)
        cursor+=len(encoded)+1
    for idx,position in enumerate(positions):
        struct.pack_into('<I',b,pointer+4*idx,position-0x20)
    b[12:32]=hashlib.sha1(b[32:full]+a.QUEST_SHA_KEY).digest()
    changes=assert_allowed_diff(old,b,[(12,32),(0xfc,pointer),(pointer,pointer+24)],quest_id)
    encoded=bytes(mh_decrypt_slot(bytes(b))[0])
    new,full2=valid_quest_slot(encoded,quest_id)
    if new!=bytes(b) or full2!=full:raise ValueError('Quest roundtrip changed decoded data')
    pointer2, fields2=a.quest_fields(new,full2)
    if pointer2!=pointer or fields2!=english:
        raise ValueError('Quest text did not survive byte-for-byte roundtrip')
    # The original in-record data outside text, pointers and checksum is exact.
    assert_allowed_diff(old,new,[(12,32),(0xfc,pointer),(pointer,pointer+24)],quest_id)
    return encoded,{'id':quest_id,'action':'localized_text','changed_bytes':changes,
                    'pointer_table_offset':pointer,'unused_text_bytes':pointer-((cursor+3)&~3),
                    'all_6_fields_verified':True}


def patch_quest_container(inner: bytes, records: list[dict], catalog: dict) -> tuple[bytes,list[dict]]:
    changed=bytearray(inner); edits=[]; protected_slots=set()
    for row in records:
        slot_idx=row['slot']; key=row.get('id');status=row['status']
        pos=slot_idx*QUEST_SIZE
        if status not in ('eligible_translation','eligible_partial_text','eligible_editorial_repair'):
            protected_slots.add(slot_idx)
            continue
        if key not in catalog:raise ValueError('Approved quest missing catalog: '+str(key))
        original=inner[pos:pos+QUEST_SIZE]
        new,detail=repack_quest(original,key,catalog[key])
        if detail['action']!='localized_text':
            raise ValueError('Analysis promised translation, but data already matched: '+str(key))
        changed[pos:pos+QUEST_SIZE]=new
        detail['slot']=slot_idx
        edits.append(detail)
    if not edits:return inner,[]
    for i in range(100):
        start=i*QUEST_SIZE
        if i in protected_slots or inner[start:start+16]==bytes(16):
            if changed[start:start+QUEST_SIZE]!=inner[start:start+QUEST_SIZE]:
                raise ValueError('Untargeted or empty quest slot was modified')
    footer_offset=len(inner)-24
    changed[footer_offset:-4]=game_checksum(bytes(changed))
    all_spans=[(r['slot']*QUEST_SIZE,(r['slot']+1)*QUEST_SIZE) for r in records if r['status'].startswith('eligible_')]
    assert_allowed_diff(inner,bytes(changed),all_spans+[(footer_offset,len(inner)-4)],'quest container')
    for r in records:
        if r['status'].startswith('eligible_'):
            pos=r['slot']*QUEST_SIZE
            now=bytes(changed[pos:pos+QUEST_SIZE])
            valid_quest_slot(now,r['id'])
    return bytes(changed),edits


def patch_palico_container(inner: bytes, records: list[dict], catalog: list[dict], hired_records: list[dict]|None=None) -> tuple[bytes,list[dict]]:
    index={p['id']:p for p in catalog}
    changed=bytearray(inner);edits=[];allow=[]
    tasks=[(rec,rec['slot']*a.PALICO_RECORD_BYTES,'downloaded',None) for rec in records]
    tasks.extend((rec,a.hired_record_offset(rec['hunter_slot'],rec['slot']),'recruited',rec['hunter_slot']) for rec in (hired_records or []))
    for record,start_record,scope,hunter in tasks:
        if record['status'] not in ('eligible_translation','eligible_editorial_repair'):continue
        pid=record['id'];slot=record['slot']; ref=index[pid]
        if start_record+0xA0>len(inner)-24:raise ValueError('Record exceeds supported Palico region')
        original=a.read_palico_text(inner[start_record:start_record+0xA0],0)
        # Verified original creator credit may be romanized, never replaced by an unrelated identity.
        if original['owner'] not in (ref['ja']['owner'],ref['en']['owner'],ref.get('legacy_en',{}).get('owner')):
            raise ValueError('Creator attribution differs; skipping unsafe edit')
        spans=[];names=[]
        for field in a.PALICO_LOCALIZED_FIELDS:
            if original[field] not in (ref['ja'][field],ref['en'][field],ref.get('legacy_en',{}).get(field)):
                raise ValueError('Customized Palico text cannot be overwritten')
            if original[field]==ref['en'][field]:continue
            offset,units=a.PALICO_FIELDS[field]
            start=start_record+offset
            changed[start:start+units*2]=field_bytes(ref['en'][field],units)
            spans.append((start,start+units*2));names.append(field)
        if not spans:raise ValueError('Palico analysis predicted changes but none needed')
        allow.extend(spans)
        edits.append({'id':pid,'slot':slot,'scope':scope,'hunter_slot':hunter,'record_offset':start_record,'action':'localized_palico_text',
                      'fields_modified':names,'creator_identity_preserved':True})
    if not edits:return inner,[]
    changed[-24:-4]=game_checksum(bytes(changed))
    assert_allowed_diff(inner,bytes(changed),allow+[(len(inner)-24,len(inner)-4)],'main save')
    for rec in edits:
        record_offset=rec['record_offset']
        original=a.read_palico_text(inner[record_offset:record_offset+0xA0],0)
        actual=a.read_palico_text(bytes(changed)[record_offset:record_offset+0xA0],0)
        ref=index[rec['id']]
        for fld in a.PALICO_LOCALIZED_FIELDS:
            want=ref['en'][fld] if fld in rec['fields_modified'] else original[fld]
            if actual[fld]!=want:raise ValueError('Palico text roundtrip failed')
        if actual['owner']!=ref['en']['owner']:
            raise ValueError('Meowster display text roundtrip failed')
    return bytes(changed),edits


def rewrite_sfo(sfo: bytes, updated_bin: bytes, mode: int) -> bytes:
    if mode==0:return sfo
    meta=a.parse_sfo_strict(sfo)
    pb=meta['SAVEDATA_PARAMS'];fl=meta['SAVEDATA_FILE_LIST']
    if len(pb['data'])<0x80 or len(fl['data'])<29:
        raise ValueError('SFO integrity metadata missing or truncated')
    result=bytearray(sfo)
    po=pb['offset'];fo=fl['offset']
    result[fo+13:fo+29]=file_hash(updated_bin,mode,KEY)
    result[po+0x10:po+0x20]=b'\0'*16
    if mode>1:
        result[po+0x70:po+0x80]=b'\0'*16
        result[po+0x70:po+0x80]=a.sfo_hash(bytes(result),mode)
    result[po+0x10:po+0x20]=a.sfo_hash(bytes(result),1)
    return bytes(result)


def rebuild_container(bin_blob: bytes,sfo_blob: bytes,folder: str,expected_inner: bytes):
    original_mode, old_inner=a.detect_psp(bin_blob,sfo_blob,folder)
    if len(expected_inner)!=len(old_inner):raise ValueError('Save size changed')
    if original_mode:
        old_clear=enc(old_inner)
        new_clear=enc(expected_inner)
        if len(old_clear)!=len(new_clear):raise ValueError('Unexpected inner cipher size change')
        # Retain original PSP encrypted-file IV, cryptographic mode, and all
        # ciphertext bytes whose *inner encrypted* counterparts did not change.
        newbin=bin_blob[:16]+bytes(x^y^z for x,y,z in zip(bin_blob[16:],old_clear,new_clear))
        if psp_stream(newbin,original_mode,KEY)!=new_clear:
            raise ValueError('PSP encryption output did not decode correctly')
    else:
        newbin=enc(expected_inner)
    newsfo=rewrite_sfo(sfo_blob,newbin,original_mode)
    new_mode,new_inner=a.detect_psp(newbin,newsfo,folder)
    if new_mode!=original_mode or new_inner!=expected_inner:
        raise ValueError('Encrypted output or integrity verification failed')
    return newbin,newsfo,original_mode


def _expected_plan(plan:dict, live:dict):
    if plan.get('analyzer_version') not in ('0.6.2','0.6.3'):
        raise ValueError('Plan generated by unsupported analyzer version')
    if plan.get('operation')!='READ_ONLY_ANALYZE':
        raise ValueError('Must provide full *technical* JSON Analyze report, not shareable report')
    if not plan.get('plan_fingerprint') or not live.get('plan_fingerprint'):
        raise ValueError('Missing fingerprint')
    if plan['plan_fingerprint']!=live['plan_fingerprint']:
        raise ValueError('Source files, selections or translation catalog changed since Analyze. Re-run Analyze before patching.')
    if plan.get('options')!=live['options']:
        raise ValueError('Selected options changed since Analyze')
    if plan.get('catalog_sha256')!=live['catalog_sha256']:
        raise ValueError('Localization catalog changed since Analyze')


def _approved_statuses(plan, allow_partial):
    """Only an explicitly selected category can require partial approval.

    Missing/unrecognized promotional Palicoes which the user never selected
    are informational inventory records, not omissions from an approved plan.
    """
    omissions=[];faults=[]
    opts=plan.get('options',{})
    quest_requested=bool(opts.get('quests',False))
    palico_ids=set(opts.get('palico_ids',[]))
    hired_requested=bool(opts.get('hired_palicoes',False))
    for s in plan['save_sets']:
        for folder,c in s['containers'].items():
            editing_this_container=(folder=='ULJM05800QST' and quest_requested or
                                    folder=='ULJM05800' and bool(palico_ids))
            if editing_this_container and c.get('status') not in ('validated','partially_recognized'):
                faults.append(f"{s['save_set']}/{folder}: invalid or missing selected save container")
            for key in ('quest_inventory','palico_inventory','hired_palico_inventory'):
                for rec in c.get(key,{}).get('records',[]):
                    selected=(quest_requested if key=='quest_inventory' else
                              bool(rec.get('id') in palico_ids and (key!='hired_palico_inventory' or hired_requested)))
                    if not selected:continue
                    stat=rec['status']
                    if stat.startswith(('skipped','blocked','protected')):
                        omissions.append({'set':s['save_set'],'folder':folder,'id':rec.get('id'),
                                          'slot':rec.get('slot'),'reason':rec.get('reason'),'status':stat})
                    if stat=='skipped_invalid_record':
                        faults.append(f"Cannot safely reconstruct container with corrupt quest slot {rec['slot']}")
    if plan['catalog_quality']['errors']:
        faults.append('Translation catalog has unresolved blocking errors')
    if faults:raise ValueError('; '.join(faults))
    if omissions and not allow_partial:
        raise ValueError(f'{len(omissions)} selected unsupported/custom records would be omitted; explicit --approve-partial required')
    return omissions


def _auxiliary_members(source:Path, needed_dirs:set[str], members:dict[str,bytes]):
    """Copy unmodified sidecar files only for folders with actual output edits.

    The full original hunter directory is NOT copied to quest-only outputs.
    Strict ZIP path checks, symlink checks and size caps apply to extras.
    """
    result={key:blob for key,blob in members.items() if key.rsplit('/',1)[0] in needed_dirs}
    total=sum(map(len,result.values()))
    if source.is_file():
        with zipfile.ZipFile(source) as z:
            names=set()
            for info in z.infolist():
                if info.is_dir():continue
                name=info.filename
                bits=PurePosixPath(name).parts
                if (name in names or name.startswith('/') or '\\' in name or '\0' in name
                   or any(p in ('.','..') for p in bits) or re.match(r'^[A-Za-z]:',name)):
                    raise ValueError('Unsafe/duplicate source ZIP member: '+repr(name))
                names.add(name)
                if name.rsplit('/',1)[0] not in needed_dirs:continue
                if (info.external_attr>>16)&0o170000 == 0o120000:
                    raise ValueError('ZIP symlink refused')
                if info.file_size>a.MAX_MEMBER_BYTES:raise ValueError('Oversized MHP3rd companion file')
                if name not in result:
                    data=z.read(info);total+=len(data);result[name]=data
    else:
        for folder in a._find_save_folders(source):
            if source.name in a.FOLDERS and folder==source:
                keyprefix=folder.name
            else:keyprefix=folder.relative_to(source).as_posix()
            if keyprefix not in needed_dirs:continue
            for file in folder.iterdir():
                if file.is_symlink() or not file.is_file():
                    raise ValueError('Unsupported auxiliary MHP3rd filesystem entry: '+str(file))
                if file.stat().st_size>a.MAX_MEMBER_BYTES:
                    raise ValueError('Oversized auxiliary MHP3rd save file')
                key=f'{keyprefix}/{file.name}'
                if key not in result:
                    blob=file.read_bytes();result[key]=blob;total+=len(blob)
    if total>a.MAX_UNCOMPRESSED_BYTES:raise ValueError('Too many companion bytes')
    return result


def execute(input_path:Path, output_path:Path, plan:dict, allow_partial:bool=False):
    src=input_path.resolve();out=output_path.resolve()
    if not src.exists():raise ValueError('Input source missing')
    if out.exists():raise ValueError('Output already exists; overwrite forbidden')
    if src.is_dir() and (src==out or src in out.parents):
        raise ValueError('Output must be OUTSIDE the source save directory')
    if src.is_file() and src==out:raise ValueError('Output cannot equal source archive')
    if out.suffix.lower()!='.zip':raise ValueError('Output must be a new ZIP')
    # Re-run exactly the same decoder/validator as Analyze; the plan is a
    # human-facing preview, never an unchecked edit authorization.
    opts=plan.get('options',{})
    live=a.analyze(src,opts.get('quests',True),set(opts.get('palico_ids',[])),opts.get('hired_palicoes',False))
    _expected_plan(plan,live)
    omissions=_approved_statuses(live,allow_partial)
    members=a.read_members(src)
    if a.sha(json.dumps({'catalog':live['catalog_sha256'],'options':live['options'],
        'members':sorted((key,a.sha(v)) for key,v in members.items())},sort_keys=True).encode())!=live['plan_fingerprint']:
        raise ValueError('Source changed after its second analysis')
    savedata=a.group_sets(members)
    catalog,_=a.load_catalog()
    updated={};summary=[];needed=set()
    for analyzed in live['save_sets']:
        prefix=analyzed['save_set'];folders=savedata[prefix]
        for folder,field in (('ULJM05800QST','quest_inventory'),('ULJM05800','palico_inventory')):
            # Do not even decode a container which has no selected write targets.
            if folder=='ULJM05800QST' and not opts.get('quests',False):continue
            if folder=='ULJM05800' and not opts.get('palico_ids',[]):continue
            if folder not in analyzed['containers']:continue
            c=analyzed['containers'][folder]
            inv=c.get(field,{}).get('records',[])
            b=folders[folder].get('MHP3RD.BIN'); sfo=folders[folder].get('PARAM.SFO')
            if b is None or sfo is None:continue
            mode,old_inner=a.detect_psp(b,sfo,folder)
            if folder=='ULJM05800QST':
                new_inner,edits=patch_quest_container(old_inner,inv,catalog['quests'])
            else:
                new_inner,edits=patch_palico_container(old_inner,inv,catalog['palicoes'],c.get('hired_palico_inventory',{}).get('records',[]))
            if not edits:continue
            newbin,newsfo,newmode=rebuild_container(b,sfo,folder,new_inner)
            name=(prefix+'/' if prefix!='.' else '')+folder
            needed.add(name)
            updated[name+'/MHP3RD.BIN']=newbin
            updated[name+'/PARAM.SFO']=newsfo
            summary.append({'save_set':prefix,'folder':folder,'original_mode':mode,
                            'result_mode':newmode,'edited_records':edits,
                            'source_bin_sha256':a.sha(b),'output_bin_sha256':a.sha(newbin),
                            'original_psp_state_preserved':True,
                            'non_localization_decoded_bytes_unchanged':True})
    if not summary:raise ValueError('No eligible localization modifications; no output produced')
    # Source unchanged: check the exact original MHP3rd BIN/SFO bytes AGAIN.
    current=a.read_members(src)
    if {k:a.sha(v) for k,v in current.items()}!={k:a.sha(v) for k,v in members.items()}:
        raise ValueError('Save source changed while preparing output')
    content=_auxiliary_members(src,needed,members)
    content.update(updated)
    # Check one last time before creating any output file.
    check=a.read_members(src)
    if {k:a.sha(v) for k,v in check.items()}!={k:a.sha(v) for k,v in members.items()}:
        raise ValueError('Save source changed while preparing ZIP output')
    report={'patcher_version':'1.0.0','status':'PATCH_OUTPUT_VERIFIED',
            'source_plan_fingerprint':live['plan_fingerprint'],'catalog_sha256':live['catalog_sha256'],
            'selected_options':live['options'],'edited_containers':summary,'omissions':omissions,
            'original_source_files_untouched':True,
            'note':'Quest-only output omits general character saves. If downloaded or recruited Palicoes are changed, the main save is included: keep private.'}
    note=("MHP3rd DLC localization v1.0.0\n"
          "Output verified against selected text changes, record constraints, and save encryption state.\n"
          "Contains only selected DLC save folders. Direct installation is a separate, explicitly approved, backup-first action.\n"
          "NEVER overwrite your only original save copies.\n"
          "If this ZIP contains ULJM05800/MHP3RD.BIN, it includes private hunter data; do not share publicly.\n")
    content['DLC_PATCH_REPORT.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    content['README_LOCALIZED_DLC.txt']=note.encode('utf-8')
    out.parent.mkdir(parents=True,exist_ok=True)
    fd,temp=tempfile.mkstemp(prefix='.mhp3rd_patch_',suffix='.tmp',dir=out.parent)
    try:
        with os.fdopen(fd,'wb') as handle:
            with zipfile.ZipFile(handle,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
                for key,blob in sorted(content.items()):z.writestr(key,blob)
        with zipfile.ZipFile(temp) as z:
            if z.testzip() is not None:raise ValueError('Written ZIP CRC verification failed')
            if set(z.namelist())!=set(content):raise ValueError('Written ZIP file list mismatch')
            for name,blob in content.items():
                if z.read(name)!=blob:raise ValueError('Written ZIP byte verification failed')
        # Detect PPSSPP autosaves that occurred while the ZIP was being built.
        final_snapshot=a.read_members(src)
        if {k:a.sha(v) for k,v in final_snapshot.items()}!={k:a.sha(v) for k,v in members.items()}:
            raise ValueError('Save source changed while creating ZIP; output discarded')
        # Atomic no-clobber destination creation (same filesystem). Never replace.
        os.link(temp,out)
    finally:
        if os.path.exists(temp):os.unlink(temp)
    report['output']=str(out)
    report['output_sha256']=a.sha(out.read_bytes())
    return report


def main():
    parser=argparse.ArgumentParser(description='MHP3rd DLC localization TEST patcher (output ZIP only)')
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--plan',required=True,type=Path,help='Full technical JSON report from Analyze v0.3/v0.4')
    parser.add_argument('--output',required=True,type=Path,help='New output ZIP path; must not exist')
    parser.add_argument('--approve',action='store_true',help='Explicitly authorize the previewed operation')
    parser.add_argument('--approve-partial',action='store_true',help='Explicitly authorize omissions when safe')
    args=parser.parse_args()
    if not args.approve:parser.error('Run Analyze and review the plan first; then supply --approve')
    try:
        plan=json.loads(args.plan.read_text(encoding='utf-8'))
        info=execute(args.input,args.output,plan,args.approve_partial)
    except (ValueError,FileNotFoundError,PermissionError,zipfile.BadZipFile,OSError) as e:
        parser.exit(2,'PATCH REFUSED (source left untouched): '+str(e)+'\n')
    print(json.dumps(info,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
