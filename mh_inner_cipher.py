"""MHP3rd inner savedata crypto, ported from mhtools DecryptUtils + SavedataCypher.
GPLv3-or-later source reference: https://github.com/codestation/mhtools
For read-only research on a copy of the user's DLC.
"""
import struct
TABLE=bytes.fromhex('''
A6 21 22 F9 3D FB F5 06 87 54 76 75 ED 16 33 2E
5A 17 50 1C DE AF 73 39 B5 28 D9 F1 CD 98 5F 2D
78 62 29 C9 FD EA 32 CC 31 70 34 61 AE 4D FE C2
45 24 F8 FC D7 2F D8 26 59 A0 BD A5 01 18 A1 95
EE 4B 1A 7A 5B DB F0 27 E6 F4 B2 AD 4A 14 9A 20
B9 36 4F 3B CA E4 41 85 3A 46 5C CB 3C EC 63 84
66 C4 EB 25 AA 7E C3 47 9B 74 8B 5D 23 8F 72 81
8C 56 C6 D4 40 60 A2 6D E5 B0 15 58 52 0F 7D 67
EF D2 0B CF 0D D6 2B 0A 9F 80 5E 3F 71 68 05 86
BB 38 CE 7F F3 83 03 48 D3 FA 35 DF 44 7C 82 93
53 A3 09 6A 77 13 55 DD BE 00 9C B4 E3 9E BC 96
A7 E2 42 4E 37 0E F6 9D 1B 2A 79 BF DC A9 88 4C
D0 AB C5 69 D1 E1 AC E9 C1 B6 7B 57 90 07 30 92
B7 1E DA 49 0C B8 A4 FF B3 F2 64 8A C7 02 6C 08
6F F7 89 C0 10 A8 8D BA 91 43 6B 3E D5 65 E0 6E
12 2C 94 99 E8 1F C8 11 8E B1 E7 51 1D 97 04 19
''')
assert len(TABLE)==256 and len(set(TABLE))==256
INVERSE=bytes(TABLE.index(i) for i in range(256))

def dec(data:bytes)->bytes:
    assert len(data)%4==0
    b=bytearray(data)
    ln=len(b)-4
    seed=bytes(b[ln:]).translate(TABLE).translate(TABLE)
    lower,upper=struct.unpack('<HH',seed)
    lower=lower or 0x215f;upper=upper or 0xdfa3
    for pos in range(0,ln,4):
        lower=lower*0x215f%0xff8f
        upper=upper*0xdfa3%0xffef
        beta=lower|(upper<<16)
        val=int.from_bytes(bytes(b[pos:pos+4]).translate(TABLE),'little')
        val=val^beta
        b[pos:pos+4]=(val.to_bytes(4,'little')).translate(TABLE)
    b[ln:]=seed
    return bytes(b)

def enc(data:bytes)->bytes:
    assert len(data)%4==0
    b=bytearray(data)
    ln=len(b)-4
    seed=bytes(b[ln:]);lower,upper=struct.unpack('<HH',seed)
    lower=lower or 0x215f;upper=upper or 0xdfa3
    for pos in range(0,ln,4):
        lower=lower*0x215f%0xff8f
        upper=upper*0xdfa3%0xffef
        beta=lower|(upper<<16)
        val=int.from_bytes(bytes(b[pos:pos+4]).translate(INVERSE),'little')
        val=val^beta
        b[pos:pos+4]=(val.to_bytes(4,'little')).translate(INVERSE)
    b[ln:]=seed.translate(INVERSE).translate(INVERSE)
    return bytes(b)
