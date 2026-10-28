#!/usr/bin/env python3
"""Read-only MHP3rd DLC extraction using documented PSP save crypto and mhtools quest cipher.

Input: Stage 1 Original_Extracted; output is isolated Stage2_Working.
Crypto formula and constants were independently checked against:
  https://github.com/TeamGDB/Yakumo/blob/main/profiles/mhp3rd/host/save_data/savedata_crypto.cpp
  https://github.com/codestation/mhtools/blob/master/src/crypt/QuestCypher.java
  https://github.com/codestation/mhtools/blob/master/src/keys/QuestKeys.java
Game key as documented by Apollo Patcher test fixtures:
  https://github.com/bucanero/apollo-patcher/blob/master/tools/verify-manifest.tsv
"""
from __future__ import annotations
import hashlib,json,struct,sys
from pathlib import Path
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
from cryptography.hazmat.primitives.cmac import CMAC
from mh_inner_cipher import dec as mh_decrypt_container, enc as mh_encrypt_container

ROOT=Path(__file__).resolve().parent
INPUT=ROOT/'Original_Extracted'
OUT=ROOT/'Stage2_Working'
KEY=bytes.fromhex('E305CEFAEB46B031859A275BDF32D863')
KIRK={0x03:'9802C4E6EC9E9E2FFC634CE42FBB4668',0x04:'99244CD258F51BCBB0619CA73830075F',0x0c:'8485C848750843BC9B9AECA79C7F6018',0x0e:'C871FDB3BCC5D2F2E2D7729DDF826882',0x10:'32295BD5EAF7A34216C88E48FF50D371',0x12:'5DC71139D01938BC027FDDDCB0837D9D',0x53:'AFFE8EB13DD17ED80A61241C959256B6',0x57:'1C9BC490E3066481FA59FDB600BB2870',0x64:'03B302E85FF381B13B8DAA2A90FF5E61'}
SDKEY={2:'FAAA50EC2FDE5493AD14B2CEA53005DF',3:'36A53EACC5269EA383D9EC256C484872',4:'D8C0B0F33E6B7685FDFB4D7D451E9203',5:'CB15F407F96A523C04B9B2EE5C53FA86',6:'7044A3AEEF5DA5F2857FF2D694F5363B',7:'EC6D29592635A57F972A0DBCA3263300'}
PARAMS={1:(0x03,None,0x04,None,None,0x53),3:(0x0c,2,0x0e,4,3,0x57),5:(0x10,5,0x12,7,6,0x64)}
SEED0=(0x3DF3,0x1709,0xB381,0x747B)
SEED1=(0xFFA9,0xFF9D,0xFFF1,0xFFC7)
QUEST_SIZE=24592;QUEST_LAST=2496

def sha(b):return hashlib.sha256(b).hexdigest()
def xor(a,b):return bytes(x^y for x,y in zip(a,b))
def mask(b,which):return xor(b,bytes.fromhex(SDKEY[which])) if which else b

def aes(seed,block,encrypt=False):
 c=Cipher(algorithms.AES(bytes.fromhex(KIRK[seed])),modes.ECB())
 ctx=c.encryptor() if encrypt else c.decryptor()
 return ctx.update(block)+ctx.finalize()

def file_hash(enc,mode,key):
 hashseed,hashmask,*_=PARAMS[mode]
 cm=CMAC(algorithms.AES(bytes.fromhex(KIRK[hashseed])))
 cm.update(enc)
 h=mask(cm.finalize(),hashmask)
 return aes(hashseed,xor(h,key),True) if mode!=1 else h

def parse_sfo(b):
 if b[:4]!=b'\0PSF':raise ValueError('Not SFO')
 k,v,n=struct.unpack_from('<III',b,8);records={}
 for i in range(n):
  kp,fmt,l,cap,pos=struct.unpack_from('<HHIII',b,20+i*16)
  name=b[k+kp:b.find(b'\0',k+kp)].decode('utf-8')
  records[name]={'offset':v+pos,'length':l,'data':b[v+pos:v+pos+l]}
 return records

def psp_stream(enc,mode,key):
 if mode not in PARAMS:raise ValueError('Unknown encryption mode')
 if len(enc)<16:raise ValueError('Encrypted data too short')
 _,_,headerseed,maskin,maskout,streamseed=PARAMS[mode]
 header=enc[:16];data=enc[16:]
 context=xor(header,key) if mode!=1 else header
 prefix=mask(aes(headerseed,mask(context,maskin)),maskout)
 # Decrypt all counter blocks in one call. The KIRK seed cipher uses CBC\n # decrypt with previous encrypted counter as the chaining value.\n
 count=(len(data)+15)//16
 counters=bytearray(count*16)
 for i in range(count):counters[16*i:16*i+16]=prefix[:12]+struct.pack('<I',i+1)
 stream=aes(streamseed,bytes(counters))
 plain=bytearray(len(data));prev=bytes(16)
 for i in range(count):
  start=16*i;end=min(start+16,len(data));counter=counters[start:start+16]
  keystream=xor(stream[start:start+16],prev)
  plain[start:end]=xor(data[start:end],keystream[:end-start]);prev=counter
 return bytes(plain)

def mh_decrypt_slot(slot):
 if len(slot)!=QUEST_SIZE:raise ValueError('Slot size mismatch')
 if slot[:16]==bytes(16):return None
 data=bytearray(slot)
 keys=list(struct.unpack_from('<4H',data,0))
 keys=[k or s for k,s in zip(keys,SEED0)]
 for offset in range(8,QUEST_SIZE,2):
  idx=(offset//2)&3
  keys[idx]=(keys[idx]*SEED0[idx])%SEED1[idx]
  v=struct.unpack_from('<H',data,offset)[0]^keys[idx]
  struct.pack_into('<H',data,offset,v)
 # header should hold payload size at offset 8; 0x20 header from mhtools
 payload_size=struct.unpack_from('<I',data,8)[0]
 valid=0<payload_size<=QUEST_SIZE-0x20
 full_length=payload_size+0x20
 return data,valid,payload_size,full_length

def run():
 manifest={'stage':2,'source_archive':'MHP3rd_All_DLC_NoCharSaves.zip', 'psp_key_source':'Apollo Patcher sample manifest', 'game_key_sha256':sha(KEY),'containers':{}}
 originals_before={f.parent.name:sha(f.read_bytes()) for f in INPUT.glob('*/MHP3RD.BIN')}
 for folder in ('ULJM05800QST','ULJM05800'):
  indir=INPUT/folder; enc=(indir/'MHP3RD.BIN').read_bytes()
  sfo=parse_sfo((indir/'PARAM.SFO').read_bytes());params=sfo['SAVEDATA_PARAMS']['data']
  flag=params[0]; mode={0x01:1,0x21:3,0x41:5}.get(flag)
  if mode is None:raise ValueError(f'Unexpected savedata mode flag {flag:x}')
  # First file list entry stores data filename then hash at +0x0D.
  filelist=sfo['SAVEDATA_FILE_LIST']['data']
  expected=filelist[0x0d:0x1d];calculated=file_hash(enc,mode,KEY)
  match=(expected==calculated)
  print(folder,'mode',mode,'encrypted integrity (PARAM.SFO file hash):',match)
  if not match:raise ValueError('PSP savedata hash mismatch; refusing unverified decryption')
  plain=psp_stream(enc,mode,KEY)
  # Cipher symmetric: encrypt in place using original header (no new random seed)
  rebuilt=enc[:16]+xor(plain,psp_stream(enc[:16]+bytes(len(plain)),mode,KEY))
  roundtrip=(rebuilt==enc)
  if not roundtrip:raise ValueError('Cipher roundtrip did not reproduce original data')
  out=OUT/'PSP_Decrypted'/folder/'MHP3RD.BIN'
  out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(plain)
  inf={'encrypted_bytes':len(enc),'decrypted_bytes':len(plain),'mode':mode,'sfo_file_hash_verified':match,'psp_cipher_roundtrip_identical':roundtrip,'encrypted_sha256':sha(enc),'plaintext_sha256':sha(plain),'first_64_plain_hex':plain[:64].hex()}
  manifest['containers'][folder]=inf
  # MHP3rd adds its own additional savedata cipher *inside* PSP encryption.
  inner=mh_decrypt_container(plain)
  inner_roundtrip=mh_encrypt_container(inner)==plain
  if not inner_roundtrip:raise ValueError('Inner MH savedata cipher roundtrip mismatch')
  innerpath=OUT/'MH_Inner_Decrypted'/folder/'MHP3RD.BIN'
  innerpath.parent.mkdir(parents=True,exist_ok=True);innerpath.write_bytes(inner)
  inf.update({'inner_savedata_bytes':len(inner),'inner_savedata_sha256':sha(inner),'inner_cipher_roundtrip_identical':inner_roundtrip})
  if folder=='ULJM05800QST':
   if len(inner)!=100*QUEST_SIZE+QUEST_LAST:raise ValueError('QST size not recognized')
   nvalid=0;nempty=0;ninvalid=0;nsha=0;nround=0;slots=[]
   outdir=OUT/'Quest_Extracted';outdir.mkdir(parents=True,exist_ok=True)
   for old in outdir.glob('quest_slot_*.mib'):old.unlink()  # remove stale generated outputs only
   for i in range(100):
    slot=inner[i*QUEST_SIZE:(i+1)*QUEST_SIZE]
    decoded=mh_decrypt_slot(slot)
    if decoded is None:
     nempty+=1;slots.append({'slot':i,'status':'empty'});continue
    data,valid,payload_size,full_length=decoded
    fn_bytes=slot[-16:];tag=fn_bytes.split(b'\0')[0].decode('ascii','replace')
    verified_sha=hashlib.sha1(data[32:full_length]+b'sR2Tf4eLAj8b3TH7').digest()==data[12:32] if valid else False
    cipher_roundtrip=(bytes(mh_decrypt_slot(bytes(data))[0])==slot)
    record={'slot':i,'status':'decrypted' if valid else 'unrecognized','mib_tag':tag,'size_field':payload_size,'full_length':full_length,'quest_sha1_verified':verified_sha,'cipher_roundtrip_identical':cipher_roundtrip}
    if valid and verified_sha and cipher_roundtrip:
     nvalid+=1;nsha+=1;nround+=1;name=f'quest_slot_{i:03d}_{tag}';path=outdir/name
     if '/' in tag or '\\' in tag or len(tag)<5:raise ValueError('Unsafe quest tag')
     path.write_bytes(data[:full_length]);record['file']=name;record['sha256']=sha(data[:full_length])
    else:ninvalid+=1;record['status']='verification_failed'
    slots.append(record)
   end=inner[100*QUEST_SIZE:]
   (outdir/'enddata.bin').write_bytes(end)
   inf.update({'slots_valid':nvalid,'slots_empty':nempty,'slots_invalid':ninvalid,'quest_sha1_pass_count':nsha,'quest_cipher_roundtrip_pass_count':nround,'slots':slots,'enddata_sha256':sha(end)})
   print('QST',nvalid,'valid quests,',nempty,'empty slots,',ninvalid,'unrecognized slots')
   if ninvalid or nvalid!=66:raise ValueError('Unrecognized quest data or unexpected slot count')
   print('First valid tags:',[(a['slot'],a['mib_tag']) for a in slots if a['status']=='decrypted'][:8])
 (OUT/'manifest_stage2.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
 originals_after={f.parent.name:sha(f.read_bytes()) for f in INPUT.glob('*/MHP3RD.BIN')}
 if originals_before!=originals_after:raise ValueError('Original source files were somehow changed')
 print('Original encrypted source BINs unchanged:',originals_before==originals_after)
 return manifest
if __name__=='__main__':run()
