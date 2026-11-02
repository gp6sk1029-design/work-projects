"""最新D版のトレイ変数・参照・説明を読み取り専用で確認する。"""
from pathlib import Path
import collections,hashlib,json,re,sys,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261029D.smc2')
texts={};tables={};ladders={};hits={}
with zipfile.ZipFile(SOURCE) as z:
    assert z.testzip() is None
    prefix=SOURCE.read_bytes()[:4].hex()
    for n in z.namelist():
        raw=z.read(n)
        try:t=raw.decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' in t:continue
        texts[n]=t
        if t.startswith('[SLWD'):
            tables[n]={}
            for l in t.splitlines():
                if l.startswith('++D='):
                    p=dict(s.split('=',1) for s in l[2:].split('\t') if '=' in s)
                    tables[n][p['N']]=p
                    if re.search(r'NG[12]_Tray|NG[12]トレイ',l):
                        print('DECL',Path(n).stem,{k:v for k,v in p.items() if k in ['N','D','G','Com','AT']})
        elif t.lstrip().startswith('{'):
            try:rows=[json.loads(l) for l in t.splitlines() if l.strip()]
            except Exception:continue
            if rows and all('CLs' in r for r in rows):ladders[n]=rows
        if re.search(r'NG[12]_Tray|NG[12]トレイ',t):
            tokens=collections.Counter(re.findall(r'[A-Za-z_][A-Za-z0-9_]*NG[12]_Tray[A-Za-z0-9_]*',t))
            comments=sorted(set(re.findall(r'[^<>\t\r\n"=]{0,55}NG[12]トレイ[^<>\t\r\n"=]{0,55}',t)))
            hits[n]={'tokens':dict(tokens),'comments':comments}
            print('HIT',n,'TOKENS',dict(tokens),'COMMENTS',comments[:30])
print('PREFIX',prefix,'HASH',hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'LADDERS',len(ladders),'RUNGS',sum(map(len,ladders.values())))
for n,t in texts.items():
    if t.lstrip().startswith('<') and re.search('NG[12]トレイ',t):
        import xml.etree.ElementTree as ET
        root=ET.fromstring(t)
        for e in root.iter():
            if e.text and re.search('NG[12]トレイ',e.text):print('XML_TEXT',Path(n).stem,e.tag.rsplit('}',1)[-1],e.text)
data={'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'texts':texts,'tables':tables,'hits':hits,'ladder_counts':{n:len(r) for n,r in ladders.items()}}
(BASE/'inspection.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
