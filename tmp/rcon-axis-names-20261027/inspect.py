"""A版の軸専用候補と参照箇所を読取り確認する。"""
from pathlib import Path
import collections,hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261027A.smc2')
texts={};tables={};ladders={}
with zipfile.ZipFile(SOURCE) as z:
    assert z.testzip() is None
    for n in z.namelist():
        try:t=z.read(n).decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' in t:continue
        texts[n]=t
        if t.startswith('[SLWD'):
            tables[n]={}
            for l in t.splitlines():
                if l.startswith('++D='):
                    p=dict(s.split('=',1) for s in l[2:].split('\t') if '=' in s)
                    tables[n][p['N']]=p
        elif t.lstrip().startswith('{'):
            try:rs=[json.loads(l) for l in t.splitlines() if l.strip()]
            except Exception:continue
            if rs and all('CLs' in r for r in rs):ladders[n]=rs
globals_name=next(n for n,t in texts.items() if t.startswith('[SLWD') and '+GN=VAR_GLOBAL' in t)
g=tables[globals_name]
candidate=[n for n in g if n.startswith(('RCON1_','HMI_RCON1_')) and not re.search(r'RCON1_[1-6]_',n) and not any(s in n for s in ['Raw','Rx','Tx','Gw','Layout','ByteOrder','SwapBytes','Comm','Axis','Motion','Write','SpeedUnit','Encode'])]
print('SOURCE_HASH',hashlib.sha256(SOURCE.read_bytes()).hexdigest())
print('GLOBAL_CANDIDATES',[(n,g[n]['D']) for n in candidate])
print('NUMBERED_TARGET_PRESENT','RCON1_1_OUT_TargetPos_mm' in g,'OLD_TARGET_PRESENT','RCON1_OUT_TargetPos_mm' in g)
print('AXIS2_NAMES',[n for n in g if n.startswith(('RCON1_2_','HMI_RCON1_2_'))])
counts=collections.Counter()
for n,rows in ladders.items():
    for i,r in enumerate(rows):
        tokens=set(re.findall(r'\b(?:HMI_)?RCON1_[A-Za-z0-9_]+',json.dumps(r,ensure_ascii=False)))
        hits=sorted(tokens.intersection(candidate))
        if hits:
            counts.update(hits)
            # 参照変数名だけを返し、無関係なプログラム本文やコメントは出力しない。
            print('REF',Path(n).stem,i,hits)
print('REF_COUNTS',dict(counts))
data={'source':str(SOURCE),'sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
      'texts':texts,'tables':tables,'globals_name':globals_name,'candidates':candidate,
      'ladder_counts':{n:len(rs) for n,rs in ladders.items()}}
(BASE/'inspection.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
