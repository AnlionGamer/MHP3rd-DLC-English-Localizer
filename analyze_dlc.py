#!/usr/bin/env python3
"""MHP3rd DLC-only *read-only* analysis, v0.5. Never changes source files.

This program DOES NOT patch saves. It makes a conservative analysis plan for a
future patcher, never a guarantee that an edit can already be applied.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, stat, struct, sys, zipfile
from pathlib import Path, PurePosixPath

try:
    from cryptography.hazmat.primitives.ciphers import algorithms
    from cryptography.hazmat.primitives.cmac import CMAC
    from mh_inner_cipher import dec, enc
    from stage2_extract import (KIRK, KEY, PARAMS, QUEST_LAST, QUEST_SIZE,
                                file_hash, mask, mh_decrypt_slot, psp_stream)
except ImportError as exc:
    raise SystemExit('Missing dependency. Install: python -m pip install cryptography\n' + str(exc))

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / 'catalog.json'
GAME_SHA_KEY = b'VQ(DOdIO9?X3!2GmW#XF'
QUEST_SHA_KEY = b'sR2Tf4eLAj8b3TH7'
FOLDERS = ('ULJM05800', 'ULJM05800QST')
EXPECTED = {'ULJM05800':1183744,'ULJM05800QST':100*QUEST_SIZE+QUEST_LAST}
FIELDS=('title','objective','failure_conditions','request_description','monster_summary','requester')
PALICO_FIELDS = {'name':(0x30,13),'comment':(0x4a,15),'owner':(0x68,12)}
PALICO_LOCALIZED_FIELDS = ('name','comment','owner') # selected promotional Meowster labels are romanized; preserve attribution identity
MAX_FILES = 20000
MAX_MEMBER_BYTES = 12*1024*1024
MAX_UNCOMPRESSED_BYTES = 40*1024*1024
SAFE_QID = re.compile(r'^m[0-9]{5}\.mib$')


def sha(data:bytes)->str:
    return hashlib.sha256(data).hexdigest()


def load_catalog():
    b=CATALOG.read_bytes()
    c=json.loads(b)
    if c['schema_version']!=1 or len(c['quests'])!=66 or tuple(c['record_fields'])!=FIELDS:
        raise ValueError('Unsupported translation catalog')
    if len(c['palicoes'])!=5:
        raise ValueError('Incorrect Palico catalog')
    return c,sha(b)


def audit_catalog(catalog:dict)->dict:
    """Conservatively audit translation text; errors prohibit future patching.

    Reports can still be generated when a catalog has malformed text, but
    affected records MUST NOT be considered safely patchable.
    """
    errors=[]; warnings=[]; invalid_ids=set()
    if catalog.get('schema_version') != 1 or tuple(catalog.get('record_fields',[])) != FIELDS:
        errors.append({'record':'catalog', 'field':'schema', 'reason':'Unsupported catalog schema'})
    for qid, record in catalog.get('quests',{}).items():
        if not SAFE_QID.fullmatch(qid):
            errors.append({'record':qid,'field':'id','reason':'Invalid quest identifier'})
            invalid_ids.add(qid)
        fields=record.get('fields',{})
        for key in FIELDS:
            values=fields.get(key)
            if not isinstance(values,dict) or not all(isinstance(values.get(k),str) and values[k] for k in ('ja','en')):
                errors.append({'record':qid,'field':key,'reason':'Missing or empty source/English text'})
                invalid_ids.add(qid)
                continue
            for lang in ('ja','en'):
                value=values[lang]
                invalid=set()
                if '\ufffd' in value:invalid.add('U+FFFD replacement character')
                if any(0xD800<=ord(ch)<=0xDFFF for ch in value):invalid.add('Unpaired Unicode surrogate')
                if any(ord(ch)<32 and ch not in '\n\t' for ch in value):invalid.add('Unexpected control character')
                if '\x00' in value:invalid.add('NUL character')
                try:value.encode('utf-8','strict')
                except UnicodeError:invalid.add('Cannot encode UTF-8')
                for issue in sorted(invalid):
                    errors.append({'record':qid,'field':key,'language':lang,'reason':issue})
                    invalid_ids.add(qid)
            # U+FF01 and other Unicode punctuation in approved catalog text are intentional.
            # Never normalize, strip or warn about valid approved typography.
    for item in catalog.get('palicoes',[]):
        pid=item.get('id','<no ID>')
        for lang in ('ja','en'):
            for key in PALICO_FIELDS:
                val=item.get(lang,{}).get(key)
                if not isinstance(val,str) or '\ufffd' in val or '\x00' in val or any(0xD800<=ord(ch)<=0xDFFF for ch in val):
                    errors.append({'record':pid,'field':key,'language':lang,'reason':'Missing/invalid Palico text'})
                    invalid_ids.add(pid)
        # The source artist's intentional fullwidth Latin styling is part of the name.
        # Japanese-script creator credits may be romanized, but fullwidth Latin is
        # already readable English: its exact glyphs, case and punctuation stay.
        for fld in ('name','owner'):
            original=item.get('ja',{}).get(fld)
            proposed=item.get('en',{}).get(fld)
            if isinstance(original,str) and classify_script(original)=='Fullwidth Latin/symbols' and original!=proposed:
                errors.append({'record':pid,'field':fld,'reason':'Approved fullwidth Latin spelling/punctuation must remain unchanged'})
                invalid_ids.add(pid)
        # Palico fields reserve one UTF-16 code unit for the terminator.
        for fld in PALICO_LOCALIZED_FIELDS:
            value=item.get('en',{}).get(fld)
            if isinstance(value,str):
                try:
                    if len(value.encode('utf-16-le')) + 2 > PALICO_FIELDS[fld][1]*2:
                        errors.append({'record':pid,'field':fld,'reason':'English text exceeds Palico field allocation'})
                        invalid_ids.add(pid)
                except UnicodeError:
                    errors.append({'record':pid,'field':fld,'reason':'Invalid UTF-16 code points'})
                    invalid_ids.add(pid)
        for fld,value in item.get('legacy_en',{}).items():
            if fld not in PALICO_LOCALIZED_FIELDS or not isinstance(value,str) or not value or '\ufffd' in value:
                errors.append({'record':pid,'field':fld,'reason':'Invalid legacy localization alias'})
                invalid_ids.add(pid)
    return {'errors':errors,'warnings':warnings,'blocked_records':sorted(invalid_ids),
            'patch_ready':not errors}


def classify_script(text:str)->str:
    """Script description, not language inference: Latin names are not Japanese."""
    if any('\u3040'<=c<='\u30ff' or '\u3400'<=c<='\u9fff' for c in text):
        return 'Japanese script'
    if any('\uff01'<=c<='\uff5e' for c in text):
        return 'Fullwidth Latin/symbols'
    return 'Latin/other'


def _recognized_path(name:str)->bool:
    """Accept only the two MHP3rd BIN/SFO pairs, regardless of ZIP prefix."""
    bits=PurePosixPath(name).parts
    return (len(bits)>=2 and bits[-2] in FOLDERS and
            bits[-1] in ('MHP3RD.BIN','PARAM.SFO'))


def _find_save_folders(selected:Path):
    """Accept save directory, SAVEDATA/PSP/PPSSPP parent, or memstick root.

    Never walk arbitrary unrelated game/save folders. Limited search through
    familiar PPSSPP folder anchors only; custom paths can select SAVEDATA.
    """
    if selected.is_symlink():raise ValueError('Source directory symlink refused')
    allowed={'savedata','psp','ppsspp','memstick','memory stick','psp_memory_stick'}
    found=[]
    queue=[(selected,0)]
    checked=set()
    while queue:
        here,depth=queue.pop(0)
        if here in checked:continue
        checked.add(here)
        if here.is_symlink():raise ValueError('Source directory symlink refused: '+str(here))
        if here.name in FOLDERS:
            found.append(here)
            continue
        if depth>=5:continue
        # Non-anchor nesting is intentionally not scanned beyond the source.
        try:
            children=list(here.iterdir())
        except OSError as exc:
            raise ValueError('Unable to inspect selected directory: '+str(here)) from exc
        for child in children:
            if not child.is_dir() or child.is_symlink():continue
            if child.name in FOLDERS:
                found.append(child)
            elif child.name.casefold() in allowed:
                queue.append((child,depth+1))
    return sorted(set(found))


def read_members(path:Path):
    """Read only supported MHP3rd BIN/SFO pairs; no other games are read."""
    if not path.exists():raise ValueError('Input not found: '+str(path))
    out={}
    if path.is_file():
        if not zipfile.is_zipfile(path):raise ValueError('Input file must be a ZIP archive')
        with zipfile.ZipFile(path) as z:
            infos=z.infolist()
            if len(infos)>MAX_FILES:raise ValueError('ZIP contains too many entries')
            total=0
            for info in infos:
                if info.is_dir():continue
                name=info.filename
                bits=PurePosixPath(name).parts
                if ('\\' in name or '\x00' in name or name.startswith('/')
                    or not bits or any(x in ('.','..') for x in bits)
                    or re.match(r'^[A-Za-z]:',name)):
                    raise ValueError('Unsafe ZIP member path: '+repr(name))
                if (info.external_attr>>16)&0o170000 == 0o120000:
                    raise ValueError('ZIP symbolic link refused: '+name)
                if not _recognized_path(name):continue
                if info.file_size>MAX_MEMBER_BYTES:raise ValueError('Oversized MHP3rd ZIP member: '+name)
                total+=info.file_size
                if total>MAX_UNCOMPRESSED_BYTES:raise ValueError('MHP3rd ZIP budget exceeded')
                if info.compress_size and info.file_size/info.compress_size>1000:
                    raise ValueError('Extreme ZIP compression ratio: '+name)
                if name in out:raise ValueError('Duplicate MHP3rd ZIP member: '+name)
                out[name]=z.read(info)
    elif path.is_dir():
        save_dirs=_find_save_folders(path)
        if not save_dirs:raise ValueError('No MHP3rd save directory found beneath selected path. Select SAVEDATA, PSP, PPSSPP or a save ZIP.')
        total=0
        for folder in save_dirs:
            for name in ('MHP3RD.BIN','PARAM.SFO'):
                fp=folder/name
                if not fp.exists():continue
                if fp.is_symlink() or not fp.is_file():raise ValueError('Unsafe MHP3rd filesystem entry: '+str(fp))
                size=fp.stat().st_size
                if size>MAX_MEMBER_BYTES:raise ValueError('Oversized MHP3rd save file: '+str(fp))
                total+=size
                if total>MAX_UNCOMPRESSED_BYTES:raise ValueError('MHP3rd save budget exceeded')
                # Folder's parent is a unique set. Preserve the relative prefix.
                # If selecting ULJM05800 directly, still normalize its name.
                if path.name in FOLDERS and folder==path:
                    rel=Path(folder.name)/name
                else:
                    rel=fp.relative_to(path)
                key=rel.as_posix()
                if key in out:raise ValueError('Duplicate MHP3rd path: '+key)
                out[key]=fp.read_bytes()
    else:raise ValueError('Unsupported input type')
    return out


def group_sets(members:dict[str,bytes]):
    """Discover independent SAVE sets without ever merging directories."""
    sets={}
    for name,blob in members.items():
        bits=PurePosixPath(name).parts
        found=[i for i,p in enumerate(bits) if p in FOLDERS]
        for idx in found:
            if idx+2!=len(bits) or bits[-1] not in ('MHP3RD.BIN','PARAM.SFO'):
                continue
            prefix='/'.join(bits[:idx]) or '.'
            folder=bits[idx]
            group=sets.setdefault(prefix,{})
            group.setdefault(folder,{})[bits[-1]]=blob
    return sets


def parse_sfo_strict(data:bytes):
    if len(data)<20 or data[:4]!=b'\0PSF':raise ValueError('Invalid PARAM.SFO header')
    key_off,data_off,n=struct.unpack_from('<III',data,8)
    if n>256 or 20+n*16>len(data):raise ValueError('Invalid PARAM.SFO record count')
    result={}
    for i in range(n):
        ko,fmt,sz,cap,offset=struct.unpack_from('<HHIII',data,20+i*16)
        name_pos=key_off+ko
        if name_pos>=len(data):raise ValueError('SFO name outside file')
        stop=data.find(b'\0',name_pos)
        if stop<0:raise ValueError('SFO name missing terminator')
        name=data[name_pos:stop].decode('utf-8','strict')
        if name in result or data_off+offset+sz>len(data) or sz>cap:
            raise ValueError('Malformed/duplicate PARAM.SFO entry')
        result[name]={'offset':data_off+offset,'data':data[data_off+offset:data_off+offset+sz]}
    return result


def sfo_hash(sfo:bytes,mode:int)->bytes:
    seed,mask_key,*_=PARAMS[mode]
    cm=CMAC(algorithms.AES(bytes.fromhex(KIRK[seed])))
    cm.update(sfo)
    return mask(cm.finalize(),mask_key)


def detect_psp(bin_data:bytes,sfo:bytes,folder:str):
    """Authenticates encrypted input *before* exposing any inner payload."""
    entries=parse_sfo_strict(sfo)
    if not {'SAVEDATA_PARAMS','SAVEDATA_FILE_LIST'}<=entries.keys():
        raise ValueError('Missing PSP save-integrity fields')
    p=entries['SAVEDATA_PARAMS']['data']
    fl=entries['SAVEDATA_FILE_LIST']['data']
    if len(p)<0x80:raise ValueError('SAVEDATA_PARAMS is truncated')
    flag=p[0]
    mode={0:0,0x01:1,0x21:3,0x41:5}.get(flag)
    if mode is None:raise ValueError(f'Unsupported PSP encryption/hash flag 0x{flag:02X}')
    if len(bin_data)!=EXPECTED[folder]+(16 if mode else 0):
        raise ValueError('Unexpected container length for this game/format')
    if not fl.startswith(b'MHP3RD.BIN\0'):
        raise ValueError('Unknown SFO secure-file entry')
    if mode:
        if len(fl)<29 or fl[13:29]!=file_hash(bin_data,mode,KEY):
            raise ValueError('Encrypted file hash mismatch')
        off=entries['SAVEDATA_PARAMS']['offset']
        tmp=bytearray(sfo)
        tmp[off+0x10:off+0x20]=bytes(16)
        if sfo_hash(tmp,1)!=p[0x10:0x20]:
            raise ValueError('PARAM.SFO mode-1 hash mismatch')
        if mode>1:
            tmp[off+0x70:off+0x80]=bytes(16)
            if sfo_hash(tmp,mode)!=p[0x70:0x80]:
                raise ValueError(f'PARAM.SFO mode-{mode} hash mismatch')
        clear=psp_stream(bin_data,mode,KEY)
        # Rebuild independently with original IV/stream to check the transform.
        zeros=psp_stream(bin_data[:16]+bytes(len(clear)),mode,KEY)
        candidate=bin_data[:16]+bytes(x^y for x,y in zip(clear,zeros))
        if candidate!=bin_data:raise ValueError('PSP decryption roundtrip failed')
    else:
        if any(p[0x10:0x80]):raise ValueError('Plaintext flag disagrees with nonzero SFO hashes')
        clear=bin_data
    inner=dec(clear)
    if enc(inner)!=clear:raise ValueError('MH savedata cipher roundtrip failed')
    expected=bytearray(inner)
    expected[-36:-16]=GAME_SHA_KEY
    if inner[-24:-4]!=hashlib.sha1(expected[:-16]).digest():
        raise ValueError('Monster Hunter savedata checksum mismatch')
    return mode,inner


def quest_fields(payload:bytes,full_length:int):
    """Find six-pointer table from structure, not a fixed quest-specific offset."""
    possibilities=[]
    # Defined UTF-8 string region starts at 0xFC for this validated schema.
    for pt in range(0xfc,min(full_length-24,0x1200),4):
        pointers=[struct.unpack_from('<I',payload,pt+4*j)[0]+0x20 for j in range(6)]
        if pointers[0]!=0xfc or len(set(pointers))!=6 or pointers!=sorted(pointers):continue
        if any(not 0xfc<=addr<pt for addr in pointers):continue
        fields=[]
        for idx,addr in enumerate(pointers):
            limit=pointers[idx+1] if idx<5 else pt
            end=payload.find(b'\x00',addr,limit)
            if end<0 or end==addr:break
            try:txt=payload[addr:end].decode('utf-8','strict')
            except UnicodeDecodeError:break
            if any(ord(ch)<32 and ch!='\n' for ch in txt):break
            fields.append(txt)
        if len(fields)==6:possibilities.append((pt,fields))
    if len(possibilities)!=1:raise ValueError('No unique six-field text pointer table')
    return possibilities[0]


def inspect_quests(inner:bytes,catalog:dict,enabled:bool,blocked_ids:set[str]|None=None):
    blocked_ids=blocked_ids or set()
    records=[];seen=set();bad=False
    for i in range(100):
        slot=inner[i*QUEST_SIZE:(i+1)*QUEST_SIZE]
        if slot[:16]==bytes(16):continue
        entry={'slot':i,'id':None,'status':'skipped_invalid_record','reason':''}
        try:
            decoded=mh_decrypt_slot(slot)
            if decoded is None:raise ValueError('Nonzero slot wrongly appeared empty')
            decoded,ok,_,full=decoded
            if not ok or full>QUEST_SIZE:raise ValueError('Invalid quest length')
            if hashlib.sha1(decoded[32:full]+QUEST_SHA_KEY).digest()!=decoded[12:32]:
                raise ValueError('Quest record checksum failed')
            if bytes(mh_decrypt_slot(bytes(decoded))[0])!=slot:
                raise ValueError('Quest cipher roundtrip failed')
            tag=slot[-16:].split(b'\0',1)[0].decode('ascii','strict')
            if not SAFE_QID.fullmatch(tag):raise ValueError('Unknown/nonstandard quest identifier')
            entry['id']=tag
            if tag in seen:raise ValueError('Duplicate quest ID; collision')
            seen.add(tag)
            if tag not in catalog:
                entry.update(status='skipped_unknown_quest',reason='No approved localization for this ID')
            else:
                pointer,texts=quest_fields(bytes(decoded),full)
                pairs=catalog[tag]['fields'];langs=[];mismatch=[]
                for f,value in zip(FIELDS,texts):
                    if value==pairs[f]['ja']:langs.append('Japanese')
                    elif value==pairs[f]['en']:langs.append('English')
                    elif value==pairs[f].get('legacy_en'):langs.append('Legacy English (defective glyph)')
                    else:langs.append('custom');mismatch.append(f)
                entry['title']=texts[0]
                entry['translation_source']=catalog[tag]['provenance']
                entry['proposed_english_title']=pairs['title']['en']
                entry['proposed_english_fields']={f:pairs[f]['en'] for f in FIELDS}
                entry['pointer_table_offset']=pointer
                entry['language_fields']=dict(zip(FIELDS,langs))
                if tag in blocked_ids:
                    entry.update(status='blocked_invalid_catalog_text',reason='Translation catalog contains invalid text; changes prohibited for this record')
                elif mismatch:
                    entry.update(status='skipped_modified_text',reason='Unrecognized/custom text in: '+', '.join(mismatch))
                elif all(x=='English' for x in langs):
                    entry.update(status='already_localized',reason='All six text fields match translation catalog')
                elif not enabled:
                    entry.update(status='preserved_by_choice',reason='Quest translation not selected')
                elif any(x=='Legacy English (defective glyph)' for x in langs):
                    entry.update(status='eligible_editorial_repair',reason='Known older English translation with U+FFFD; only approved editorial correction is proposed')
                elif any(x=='English' for x in langs):
                    entry.update(status='eligible_partial_text',reason='Known Japanese/English mixture; patching not yet implemented')
                else:
                    entry.update(status='eligible_translation',reason='All six Japanese fields match approved source')
        except (ValueError,UnicodeError,struct.error,IndexError) as e:
            bad=True;entry['reason']=str(e)
        records.append(entry)
    # Even when no known quests exist, this isn't a failure unless unsupported.
    missing=sorted(set(catalog)-{r['id'] for r in records if r['id']})
    return {'occupied_slots':len(records),'empty_slots':100-len(records),
            'missing_known_quest_ids':missing,'records':records,'structural_errors':bad}


def read_palico_text(inner:bytes,index:int):
    out={}
    for name,(offset,units) in PALICO_FIELDS.items():
        p=index*0xa0+offset
        b=inner[p:p+units*2]
        if len(b)!=units*2:raise ValueError('Palico field truncated')
        txt=b.decode('utf-16le','strict')
        if '\0' not in txt:raise ValueError('Palico field lacks terminator')
        out[name]=txt.split('\0',1)[0]
    return out


def inspect_palicoes(inner:bytes,catalog:list[dict],selection:set[str],blocked_ids:set[str]|None=None):
    blocked_ids=blocked_ids or set()
    """Only inspect validated 0xA0 promotional positions; never scan hunter region."""
    records=[];seen=set()
    # These are catalog slots, not a general hired-Palico parser.
    for i in range(5):
        entry={'slot':i,'id':None}
        try:
            txt=read_palico_text(inner,i)
            if not any(txt.values()):continue
            match=[]
            for p in catalog:
                matches=sum(txt[f] in (p['ja'][f],p['en'][f],p.get('legacy_en',{}).get(f)) for f in PALICO_FIELDS)
                if matches>=2:
                    match.append(p)
            if len(match)!=1:
                entry.update(status='skipped_unrecognized_or_custom_palico',reason='Promotional identity or text cannot be proven')
            else:
                p=match[0];pid=p['id'];entry['id']=pid
                if pid in seen:entry.update(status='skipped_duplicate_palico',reason='Repeated promotional identity')
                else:
                    seen.add(pid)
                    fields={f:(('Original (fullwidth Latin)' if classify_script(txt[f])=='Fullwidth Latin/symbols' else 'Japanese') if txt[f]==p['ja'][f] else 'English' if txt[f]==p['en'][f] else 'Previous localized version' if txt[f]==p.get('legacy_en',{}).get(f) else 'custom') for f in PALICO_FIELDS}
                    entry['language_fields']=fields
                    entry['detected_scripts']={k:classify_script(txt[k]) for k in PALICO_FIELDS}
                    entry['name']=txt['name']
                    entry['original_name']=p['ja']['name']
                    entry['original_comment']=p['ja']['comment']
                    entry['original_creator']=p['ja']['owner']
                    entry['proposed_english_name']=p['en']['name']
                    entry['proposed_english_comment']=p['en']['comment']
                    entry['proposed_english_owner']=p['en']['owner']
                    entry['owner_policy']='Preserve original fullwidth Latin creator names; romanize only Japanese-script creator names; protect customization'
                    entry['editorial']=p.get('editorial',{})
                    if pid in blocked_ids:
                        entry.update(status='blocked_invalid_catalog_text',reason='Translation catalog contains invalid text; changes prohibited for this record')
                    elif 'custom' in fields.values():
                        entry.update(status='protected_custom_text',reason='Promotional nickname, comment or creator may be customized; do not overwrite')
                    elif all(txt[k]==p['en'][k] for k in PALICO_LOCALIZED_FIELDS):
                        entry.update(status='already_localized',reason='Name, comment and Meowster already match approved localization')
                    elif pid not in selection:
                        entry.update(status='preserved_by_choice',reason='Optional Palico localization disabled/not selected')
                    elif any(fields[k]=='Previous localized version' for k in PALICO_LOCALIZED_FIELDS):
                        entry.update(status='eligible_editorial_repair',reason='Recognized prior localization; finish approved name/comment/Meowster text')
                    else:entry.update(status='eligible_translation',reason='Recognized Palico; localize name, comment and original Meowster label without changing credited identity')
        except (ValueError,UnicodeError,IndexError) as e:
            entry.update(status='skipped_invalid_palico_text',reason=str(e))
        records.append(entry)
    return {'records':records,'selected_palico_ids':sorted(selection),
            'not_found_catalog_ids':sorted(set(p['id'] for p in catalog)-seen),
            'warning':'Only promotional download records inspected; Meowster labels selected for preservation/translation as appropriate, but unrelated hunter fields are not inspected.'}


# Independently verified 0xA0 recruited-Palico arrays, within three separate
# hunter slots (0x60000 apart) in the supported 0x121000-byte general save.
# No entire character blocks are parsed or modified by the analyzer.
HIRED_TABLE_START = 0x5DA68
HUNTER_STRIDE = 0x60000
HUNTER_SLOTS = 3
HIRED_SLOTS = 25
PALICO_RECORD_BYTES = 0xA0


def hired_record_offset(hunter_slot:int,slot:int)->int:
    if not (0<=hunter_slot<HUNTER_SLOTS and 0<=slot<HIRED_SLOTS):
        raise ValueError('Unsupported hired-Palico slot coordinates')
    return HIRED_TABLE_START+hunter_slot*HUNTER_STRIDE+slot*PALICO_RECORD_BYTES


def inspect_hired_palicoes(inner:bytes,catalog:list[dict],selection:set[str],blocked_ids:set[str]|None=None):
    """Opt-in analysis: only exact, uniquely identified promo copies are writable.

    Ordinary Palicoes are intentionally ignored; user-edited text is protected.
    Field read is bounded to verified 0xA0 record offsets; no hunter data scan.
    """
    blocked_ids=blocked_ids or set()
    result=[]
    for hunter in range(HUNTER_SLOTS):
        for slot in range(HIRED_SLOTS):
            start=hired_record_offset(hunter,slot)
            if start+PALICO_RECORD_BYTES>len(inner)-24:
                raise ValueError('Hired Palico table extends into checksum/footer')
            raw=inner[start:start+PALICO_RECORD_BYTES]
            if raw[0x30:0x30+26]==bytes(26):continue
            try:found=read_palico_text(raw,0)
            except (UnicodeError,ValueError):continue # Not recognized as a supported Palico
            matches=[]
            for cat in catalog:
                aliases=cat.get('legacy_en',{})
                recognized={f:found[f] in (cat['ja'][f],cat['en'][f],aliases.get(f)) for f in PALICO_FIELDS}
                if sum(recognized.values())>=2:matches.append((cat,recognized))
            if len(matches)!=1:continue # Never infer identity from an ambiguous match
            cat,recognized=matches[0];pid=cat['id']
            fields={f:'recognized' if recognized[f] else 'custom' for f in PALICO_FIELDS}
            rec={'hunter_slot':hunter,'slot':slot,'id':pid,'name':found['name'],
                 'original_name':cat['ja']['name'],'original_comment':cat['ja']['comment'],
                 'original_creator':cat['ja']['owner'],
                 'proposed_english_name':cat['en']['name'],
                 'proposed_english_comment':cat['en']['comment'],
                 'proposed_english_owner':cat['en']['owner'],
                 'editorial':cat.get('editorial',{}),'language_fields':fields,
                 'owner_policy':'Preserve fullwidth Latin Meowster style; romanize only recognized Japanese-script text; preserve creator identity'}
            if pid not in selection:
                rec.update(status='preserved_by_choice',reason='This promotional Palico was not selected')
            elif pid in blocked_ids:
                rec.update(status='blocked_invalid_catalog_text',reason='Catalog is not safe for this Palico')
            elif not all(recognized.values()):
                rec.update(status='protected_custom_text',reason='One or more hired Palico text fields differ from approved originals; do not overwrite custom names/comments')
            elif all(found[f]==cat['en'][f] for f in PALICO_LOCALIZED_FIELDS):
                rec.update(status='already_localized',reason='Recruited name, comment and Meowster already match the approved text')
            else:
                rec.update(status='eligible_translation',reason='Recognized original/legacy recruited promotional Palico; update only name, comment and Meowster text')
            rec['planned_action']='translate_selected_text' if rec['status']=='eligible_translation' else 'preserve_unchanged'
            result.append(rec)
    return {'records':result,'hunter_slot_count':HUNTER_SLOTS,
       'note':'Only positively identified promotional copies; ordinary/custom Palicoes, stats, gear, skills and hunter data are untouched.'}


def analyse_set(prefix:str,folders:dict,catalog:dict,quests_enabled:bool,selected:set[str],blocked_ids:set[str]|None=None,hired_enabled:bool=False):
    blocked_ids=blocked_ids or set()
    result={'save_set':prefix,'containers':{},'preview':{},'warnings':[]}
    for folder in FOLDERS:
        if folder not in folders:continue
        pair=folders[folder]
        info={'directory':folder,'source_hashes':{k:sha(v) for k,v in sorted(pair.items())},'status':'unsupported','errors':[]}
        result['containers'][folder]=info
        if not {'MHP3RD.BIN','PARAM.SFO'}<=pair.keys():
            info['errors'].append('MHP3RD.BIN or PARAM.SFO missing; no detection attempted');continue
        try:
            mode,inner=detect_psp(pair['MHP3RD.BIN'],pair['PARAM.SFO'],folder)
            info.update(status='validated',encryption=('unencrypted' if mode==0 else f'PSP mode {mode}'),
                        inner_sha256=sha(inner),format='MHP3rd supported fixed container length',
                        checksum='validated')
            if folder=='ULJM05800QST':
                info['quest_inventory']=inspect_quests(inner,catalog['quests'],quests_enabled,blocked_ids)
                if info['quest_inventory']['structural_errors']:
                    info['status']='partially_recognized'
                    info['errors'].append('One or more quest slots failed validation')
            else:
                references=inner[0x668:0x6b2].split(b'\0')
                dlo=[]
                for x in references:
                    if not x:continue
                    try:t=x.decode('ascii')
                    except UnicodeError:continue
                    if re.fullmatch(r'[a-zA-Z0-9_.-]+\.dlo',t):dlo.append(t)
                info['downloaded_palico_references']=dlo
                info['palico_inventory']=inspect_palicoes(inner,catalog['palicoes'],selected,blocked_ids)
                if hired_enabled:
                    info['hired_palico_inventory']=inspect_hired_palicoes(inner,catalog['palicoes'],selected,blocked_ids)
                if not dlo:
                    for rec in info['palico_inventory']['records']:
                        if rec.get('status') in ('eligible_translation','eligible_editorial_repair'):
                            rec.update(status='skipped_unverified_palico_metadata', reason='No verified promotional DLC .dlo references; cannot authorize an edit')
                info['other_bonus_data']='Not mapped; left untouched by design'
                if not dlo:info['errors'].append('No recognized .dlo metadata; Palico identity needs further validation')
        except (ValueError,struct.error,UnicodeError,IndexError) as e:
            info['errors'].append(str(e))
    if len(folders)==1:
        result['warnings'].append('Only one save directory found. Missing DLC category will not be analyzed.')
    allrec=[]
    for typ,name in [('ULJM05800QST','quest_inventory'),('ULJM05800','palico_inventory'),('ULJM05800','hired_palico_inventory')]:
        d=result['containers'].get(typ,{})
        allrec.extend(d.get(name,{}).get('records',[]))
    counts={}
    for r in allrec:
        counts[r['status']]=counts.get(r['status'],0)+1
        r['planned_action']='translate_selected_text' if r['status'] in ('eligible_translation','eligible_partial_text','eligible_editorial_repair') else 'preserve_unchanged'
    result['preview']={'record_status_counts':counts,
       'partial_approval_required':any(k.startswith(('skipped','protected','blocked')) for k in counts) or any(c['status']!='validated' for c in result['containers'].values()),
       'source_character_data':('Only opted-in recruited promotional Palico name/comment/Meowster fields identified; all other hunter data remains opaque and untouched' if hired_enabled else 'Never parsed, compared against a reference hunter, or edited'),
       'summary':{'eligible':sum(v for k,v in counts.items() if k.startswith('eligible')),
                  'already_localized':counts.get('already_localized',0),
                  'preserved_by_choice':counts.get('preserved_by_choice',0),
                  'skipped_or_blocked':sum(v for k,v in counts.items() if k.startswith(('skipped','protected','blocked')))},
       'writes_to_source':False,
       'patch_capability':'NOT AVAILABLE: analysis only'}
    if not result['containers']:result['warnings'].append('No recognized MHP3rd save files found')
    return result


def analyze(input_path:Path,quests_enabled=True,palico_ids:set[str]|None=None,hired_enabled:bool=False):
    palico_ids=palico_ids or set()
    cat,cat_hash=load_catalog()
    qa=audit_catalog(cat)
    unknown=palico_ids-{p['id'] for p in cat['palicoes']}
    if unknown:raise ValueError('Unknown Palico selection: '+', '.join(sorted(unknown)))
    before_sha=sha(input_path.read_bytes()) if input_path.is_file() else None
    members=read_members(input_path)
    sets=group_sets(members)
    if not sets:raise ValueError('No ULJM05800 / ULJM05800QST MHP3RD.BIN + PARAM.SFO save sets found')
    result={'analyzer_version':'0.6.3','operation':'READ_ONLY_ANALYZE',
        'catalog_sha256':cat_hash,'catalog_quality':qa,'source_path':str(input_path.resolve()),
        'source_archive_sha256':before_sha,'options':{'quests':quests_enabled,'palico_ids':sorted(palico_ids),'hired_palicoes':bool(hired_enabled)},
        'save_sets':[],'limitations':[
          'Analyzer does not patch, install, or decrypt output files onto disk.',
          'Requires intact recognized MHP3rd containers, game key and supported PSP encryption mode.',
          'Catalog includes 65 patch-6.3.0 quest translations, one independent draft, and five unverified Palico editorial drafts.',
          'Opted-in recruited Palico analysis examines only positively identified 0xA0 promotional copies in supported hunter slots, without reading hunter stats.',
          'Original fullwidth Latin Meowster lettering is preserved exactly; Japanese-script Meowsters are romanized only from approved identities. Custom attribution is protected.',
          'Custom DLC data is reported conservatively and never modified.'
        ]}
    for pref,folders in sorted(sets.items()):
        result['save_sets'].append(analyse_set(pref,folders,cat,quests_enabled,palico_ids,set(qa['blocked_records']),hired_enabled))
    if qa['errors']:
        result['limitations'].append('BLOCKER: Invalid translation catalog entries prevent safe patching of affected records.')
    # Source fingerprint binds the future analyze/patch plan to exact inputs/options.
    result['plan_fingerprint']=sha(json.dumps({'catalog':cat_hash,'options':result['options'],
        'members':sorted((k,sha(v)) for k,v in members.items())},sort_keys=True).encode())
    if before_sha is not None:
        if sha(input_path.read_bytes())!=before_sha:
            raise ValueError('Source archive changed during analysis; results discarded')
    else:
        # Detect common concurrent writes to files in a live PPSSPP SAVEDATA folder.
        second_snapshot=read_members(input_path)
        if {k:sha(v) for k,v in members.items()} != {k:sha(v) for k,v in second_snapshot.items()}:
            raise ValueError('Source folder changed during analysis; results discarded')
    return result


def render_text(report):
    lines=['MHP3rd DLC Localization — READ-ONLY ANALYSIS',
      'Analyzer version: '+report['analyzer_version'],
      'Source: '+report['source_path'],
      'Plan fingerprint: '+report['plan_fingerprint'],
      'Write action: NONE (this program cannot patch saves)','']
    for s in report['save_sets']:
        lines.append('SAVE SET: '+s['save_set'])
        for folder,c in s['containers'].items():
            lines.append(f"  {folder}: {c['status']} | {c.get('encryption','undetermined')}")
            if 'quest_inventory' in c:
                q=c['quest_inventory']
                lines.append(f"    Installed quests: {q['occupied_slots']}; empty slots: {q['empty_slots']}; absent from catalog: {len(q['missing_known_quest_ids'])}")
            if 'palico_inventory' in c:
                lines.append(f"    Promotional Palico records detected: {len(c['palico_inventory']['records'])}; .dlo references: {len(c['downloaded_palico_references'])}")
            if 'hired_palico_inventory' in c:
                lines.append(f"    Recruited promotional Palico copies identified: {len(c['hired_palico_inventory']['records'])}; only opted-in text can be updated")
            for e in c['errors']:lines.append('    VALIDATION NOTE: '+e)
        for key,v in sorted(s['preview']['record_status_counts'].items()):lines.append(f'  {key}: {v}')
        if s['preview']['partial_approval_required']:
            lines.append('  CAUTION: Partial/unverified records. Future patching must request explicit approval.')
        lines.extend('  NOTICE: '+x for x in s['warnings'])
        lines.append('')
    lines.append('Per-record IDs, reasons, offsets and field statuses are provided in the JSON report.')
    lines.append('Character slots/gear/stats were not examined. No source file was modified.')
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser=argparse.ArgumentParser(description='READ-ONLY MHP3rd DLC localization analysis — NO SAVE PATCHING')
    parser.add_argument('--input',required=True,type=Path,help='Existing ZIP or save folder')
    parser.add_argument('--json',type=Path,help='Optional NEW technical JSON report (outside input)')
    parser.add_argument('--html',type=Path,help='Optional NEW privacy-safe offline HTML preview (outside input)')
    parser.add_argument('--shareable-json',type=Path,help='Optional NEW privacy-safe JSON report (outside input)')
    parser.add_argument('--no-quests',action='store_true',help='Preserve all quests; analyze only')
    parser.add_argument('--hired-palicoes',action='store_true',help='Opt in to updating existing recruited promotional Palicoes (only if selected)')
    parser.add_argument('--palico',action='append',default=[],metavar='ID',help='Optional promotional Palico ID; see README')
    args=parser.parse_args(argv)
    outputs=[p.resolve() for p in (args.json,args.html,args.shareable_json) if p is not None]
    if len(outputs)!=len(set(outputs)):parser.error('Reports must use different output paths')
    for out in outputs:
        inp=args.input.resolve()
        if out.exists():parser.error('Report output already exists; no overwrites')
        if inp.is_file() and out==inp:parser.error('Cannot write over source')
        if inp.is_dir() and inp in out.parents:parser.error('Report must be outside source directory')
    try:
        r=analyze(args.input,not args.no_quests,set(args.palico),args.hired_palicoes)
        print(render_text(r))
        if args.json:
            # Report contains identifiers/text only; never contains user save payloads.
            with args.json.open('x',encoding='utf-8') as f:json.dump(r,f,ensure_ascii=False,indent=2)
            print('Wrote technical JSON report: '+str(args.json))
        if args.shareable_json:
            from report_privacy import redact_report
            with args.shareable_json.open('x',encoding='utf-8') as f:
                json.dump(redact_report(r),f,ensure_ascii=False,indent=2)
            print('Wrote privacy-safe JSON report: '+str(args.shareable_json))
        if args.html:
            from html_report import render_html
            from report_privacy import redact_report
            args.html.open('x',encoding='utf-8').write(render_html(redact_report(r)))
            print('Wrote privacy-safe HTML preview: '+str(args.html))
    except (ValueError,OSError,zipfile.BadZipFile) as e:
        parser.exit(2,'ANALYZE REFUSED: '+str(e)+'\n')

if __name__=='__main__':main()
