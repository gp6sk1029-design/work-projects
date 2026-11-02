"""利用者のF_1版を読み、完了信号とコメントの編集対象を調査する。"""
from pathlib import Path
import hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).resolve().parent
source=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261026F_1.smc2')
texts={}
with zipfile.ZipFile(source) as z:
    assert z.testzip() is None
    for n in z.namelist():
        try:t=z.read(n).decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' not in t:texts[n]=t
data={'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'texts':texts}
(base/'inspection.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
print('HASH',data['sha256'])
for n,t in texts.items():
    if t.startswith('[SLWD'):
        selected=[l for l in t.splitlines() if ('RCON1_1_M' in l or 'RCON1_1_MoveDone' in l)]
        if selected:print('DECL',n,'\n'+'\n'.join(selected))
        if '+N=ST_RCON' in t or 'Name="ST_RCON' in t:print('TYPES',n,t[:1600])
    if t.lstrip().startswith('{'):
        try:rows=[json.loads(l) for l in t.splitlines() if l.strip()]
        except Exception:continue
        hits=[(i,re.findall(r'"Var"\s*:\s*"([^"]*)"',json.dumps(r))) for i,r in enumerate(rows) if re.search(r'RCON1_[1-6]_M\[2\]',json.dumps(r))]
        if hits:print('REFS',n,hits)
        if n.endswith('7b1666c7-ee97-4210-81b2-fed5a6172074.xml'):
            print('ROWS',len(rows))
            print('HEAD',[(i,r.get('CMT','')) for i,r in enumerate(rows[:41])])
    if n.endswith('20a6b651-4c34-401a-965e-db3e18414d5c.xml'):
        root=ET.fromstring(t)
        for el in root.iter():
            if el.get('Name')=='RCON1_1_M':print('META',ET.tostring(el,encoding='unicode')[:1500])
    if 'ST_RCON' in t and not t.startswith('[SLWD') and '<DataType' in t:print('TYPEFILE',n,t[:600])
