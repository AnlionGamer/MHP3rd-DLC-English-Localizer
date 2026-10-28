"""Focused Meowster text validation without touching save files."""
import analyze_dlc as a
from patch_dlc import patch_palico_container

cat=a.load_catalog()[0]['palicoes']
original=bytearray(4000)
for idx,p in enumerate(cat):
    for name,(offset,units) in a.PALICO_FIELDS.items():
        txt=p['ja'][name].encode('utf-16le')+b'\0\0'
        original[idx*0xA0+offset:idx*0xA0+offset+units*2]=txt.ljust(units*2,b'\0')
# Build valid MH inner checksum and use five trusted records.
from patch_dlc import game_checksum
original[-24:-4]=game_checksum(bytes(original))
records=a.inspect_palicoes(bytes(original),cat,{p['id'] for p in cat})['records']
assert all(r['status']=='eligible_translation' for r in records),records
modified,edits=patch_palico_container(bytes(original),records,cat)
assert len(edits)==5,edits
for idx,p in enumerate(cat):
    assert a.read_palico_text(modified,idx)==p['en'], (idx,p)
    for fld in ('name','comment','owner'):
        old=a.read_palico_text(bytes(original),idx)[fld]
        new=a.read_palico_text(modified,idx)[fld]
        if old!=p['en'][fld]:assert new==p['en'][fld]
print('PASS five downloaded Meowster name/comment/name localized with exact source diff allowance')
# User-owned custom creator must not be replaced, even with valid Palico identifier.
custom=bytearray(original)
start,units=a.PALICO_FIELDS['owner']
custom[start:start+units*2]=('Somebody'.encode('utf-16le')+b'\0\0').ljust(units*2,b'\0')
custom[-24:-4]=game_checksum(bytes(custom))
result=a.inspect_palicoes(bytes(custom),cat,{p['id'] for p in cat})['records']
assert result[0]['status']=='protected_custom_text', result[0]
assert sum(r['status']=='eligible_translation' for r in result)==4
print('PASS customized owner protected; four other recognized Palicoes eligible')
# Optional selection off means zero write targets.
none=a.inspect_palicoes(bytes(original),cat,set())['records']
assert all(r['status']=='preserved_by_choice' for r in none)
unchanged,edits=patch_palico_container(bytes(original),none,cat)
assert unchanged==bytes(original) and not edits
print('PASS Palico localization disabled means no Meowster edits')
