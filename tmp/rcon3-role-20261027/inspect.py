"""RCON1_3の用途コメントだけを読取り調査する。"""
from pathlib import Path
import collections,hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261027B.smc2')
texts={};found=[];counts={}
def add(n,kind,context,c):
    if 'RCON1_3' in context or 'RCON1_3' in c or (context in ['RCON1_OUT[3]','RCON1_IN[3]']):
        if any(x in c for x in ['SF','ストック','送り','排出','仕分け']):found.append({'entry':n,'kind':kind,'context':context,'comment':c})
with zipfile.ZipFile(SOURCE) as z:
    assert z.testzip() is None
    for n in z.namelist():
        try:t=z.read(n).decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' in t:continue
        texts[n]=t
        if t.startswith('[SLWD'):
            for l in t.splitlines():
                if not l.startswith('++D='):continue
                p=dict(x.split('=',1) for x in l[2:].split('\t') if '=' in x)
                add(n,'Com',p['N'],p.get('Com',''))
                if p.get('EC'):
                    for e in ET.fromstring(p['EC']):add(n,'EC',p['N']+e.get('EK',''),e.get('C',''))
        elif t.lstrip().startswith('{'):
            try:rows=[json.loads(l) for l in t.splitlines() if l.strip()]
            except Exception:continue
            if rows and all('CLs' in r for r in rows):
                counts[n]=len(rows)
                for i,r in enumerate(rows):add(n,'CMT',str(i),r.get('CMT',''))
        elif t.lstrip().startswith('<'):
            try:r=ET.fromstring(t)
            except ET.ParseError:continue
            for e in r.iter():
                if 'Comment' in e.attrib:add(n,'Comment',e.get('Address','')+' '+e.get('Name',''),e.get('Comment',''))
data={'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'texts':texts,'found':found,'ladder_counts':counts}
(BASE/'inspection.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
print('SOURCE_SHA256',data['sha256'])
print('RELATED_ROLE_COMMENTS',len(found),'COUNTS',dict(collections.Counter(x['kind'] for x in found)))
for c,count in collections.Counter(x['comment'] for x in found).items():print('COMMENT',count,c)
