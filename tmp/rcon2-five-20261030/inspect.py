"""利用者指定NSUB A版を読み取り専用で確認する。"""
from pathlib import Path
import zipfile, json, xml.etree.ElementTree as ET, hashlib, sys, re
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\3089-2603A_検査箱詰め装置_CORE_NSUB_PIP-02F02X_20261030A.smc2')
with zipfile.ZipFile(SOURCE) as z:
    assert z.testzip() is None
    texts={}
    for n in z.namelist():
        try: t=z.read(n).decode('utf-8-sig')
        except UnicodeError: continue
        if '\x00' not in t: texts[n]=t
oem=next(n for n in texts if n.endswith('.oem'))
es={e.get('id'):e.attrib for e in ET.fromstring(texts[oem]).iter('Entity')}
print('SOURCE',SOURCE,'SHA256',hashlib.sha256(SOURCE.read_bytes()).hexdigest())
print('ENTITIES',[v for v in es.values() if 'RCON' in v.get('name','')])
for n,t in texts.items():
    if t.startswith('[SLWD'):
        print('TABLE',n,t[:100].replace('\n',' '))
        lines=[l for l in t.splitlines() if re.search(r'\bN=(?:RCON2|RCON1_6|RCON1_1|HMI_RCON2)',l)]
        print('\n'.join(lines)[:12000])
    elif t.lstrip().startswith('{'):
        try: rows=[json.loads(l) for l in t.splitlines() if l.strip()]
        except Exception: continue
        if 'RCON' in es.get(Path(n).stem,{}).get('name',''):
            print('LADDER',n,len(rows))
            for i,r in enumerate(rows):
                print('ROW',i,r.get('CMT','').replace('\r\n',' / '),[d.get('Var') for d in r.get('CLs',[]) if 'Var' in d],['IST:'+d.get('TXT','')[:60] for d in r.get('CLs',[]) if d.get('__type')=='IST'])
            (BASE/'rcon_rows.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print('DEST_CONTENTS',[x.name for x in (SOURCE.parent/'Codex編集用').glob('*')])
(BASE/'inspection.json').write_text(json.dumps({'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'texts':texts,'entities':es,'oem_name':oem},ensure_ascii=False),encoding='utf-8')
