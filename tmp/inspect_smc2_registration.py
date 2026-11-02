"""指定プロジェクトの型・変数・EtherCAT設定を読み取り専用で調べる。"""
from pathlib import Path
import zipfile
import re
import hashlib
import xml.etree.ElementTree as ET
import collections
import sys
sys.stdout.reconfigure(encoding='utf8')
p=Path(sys.argv[1])
with zipfile.ZipFile(p) as z:
    assert z.testzip() is None
    print('HASH',hashlib.sha256(p.read_bytes()).hexdigest())
    print('ENTRIES',len(z.infolist()))
    if '--target' in sys.argv:
        ids=['4bdcdc10-734d-4589-b299-075e93db9b10','22aaf14a-1b6b-4d6b-8ef3-92d6b44c6fa5']
        for id in ids:
            matches=[n for n in z.namelist() if id in n]
            print('TARGET_FILES',id,matches)
            if not matches: continue
            f=matches[0]
            b=z.read(f)
            try:t=b.decode('utf-8-sig')
            except UnicodeError:
                print('BINARY_HEAD',repr(b[:100]))
                hits=re.findall(rb'[ -~]{5,}',b)
                for i,s in enumerate(hits):
                    if re.search(rb'RCGW|RCON|Node1|Node5',s):print('BINARY_STRING',i,s[:800])
                continue
            print('TARGET',f,'SIZE',len(t),'TEXT',t[:16500])
        f=next(n for n in z.namelist() if n.endswith('f07dd06c-505c-431b-b9fc-098949805b4e.xml'))
        t=z.read(f).decode('utf-8-sig')
        lines=t.splitlines()
        print('GLOBAL_GROUPS',[l for l in lines if l.startswith('+GN=')])
        print('EXISTING_STRUCT_VARS',[l for l in lines if '++D=sData' in l])
        print('INITIAL_VALUE_EXAMPLES',[l for l in lines if '\tIV=' in l][:5])
        print('EXISTING_NODE_ASSIGNMENTS',[l for l in lines if re.search(r'AT=ECAT://node#[12345]/',l)][:6])
        print('GLOBALS_HEAD',repr(t[:2000]))
        hits=[(i+1,l) for i,l in enumerate(lines) if re.search(r'RCON|RCGW|AT=ECAT',l,re.I)]
        print('GLOBALS_MATCHES',len(hits))
        for i,l in hits[:12]:print(i,l[:1400])
        print('GLOBALS_TAIL',repr(t[-200:]))
        sys.exit()
    for f in z.infolist():
        b=z.read(f)
        try:t=b.decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' in t:continue
        if f.filename.endswith('.manifest'):
            print('MANIFEST',f.filename,t[:4500])
        elif f.filename.endswith('.oem'):
            root=ET.fromstring(t)
            for e in root.iter():
                s=ET.tostring(e,encoding='unicode')
                if e.tag=='Entity' and (any(k in str(e.attrib) for k in ['Global','DataType','Struct','EtherCat','EtherCAT','Device','Variable']) or 'RCON' in str(e.attrib)):
                    print('OEM_ENTITY',e.attrib)
            print('OEM_HEAD',t[:1900])
        elif t.startswith('[SLWD'):
            lines=t.splitlines()
            print('SLWD',f.filename,'LINES',len(lines),'HEAD',repr(t[:600]))
            hits=[line for line in lines if re.search(r'RCON|RCGW|ST_RCON|RC[1-9]_.*PDO',line,re.I)]
            for line in hits[:8]:print('SLWD_RCON',line[:1500])
            if hits:print('SLWD_RCON_COUNT',len(hits))
            struct=[line for line in lines if re.search(r'\bT=|\bDT=',line) and ('STRUCT' in line.upper() or 'ST_' in line)]
            for line in struct[:4]:print('SLWD_STRUCT',line[:1800])
        elif 'RCGW-ECT' in t or 'RCON-GW' in t:
            print('RCON_FILE',f.filename,'SIZE',len(b))
            for m in list(re.finditer(r'RCGW-ECT|RCON-GW',t))[:5]:print('RCON_CONTEXT',repr(t[max(0,m.start()-160):m.end()+250]))
        elif re.search(r'StructureType|StructType|DataTypeDefinition|\[.*ST.*\]',t):
            print('TYPE_CANDIDATE',f.filename,repr(t[:1200]))
