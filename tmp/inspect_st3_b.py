"""B版のST3工程と要素コメントを読み取り専用で確認する。"""
import sys,json,re,hashlib
from pathlib import Path
from zipfile import ZipFile
sys.stdout.reconfigure(encoding='utf-8')
p=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_2026102B.smc2')
if len(sys.argv)>1:p=Path(sys.argv[1])
with ZipFile(p) as z:
    assert z.testzip() is None
    print('SHA256',hashlib.sha256(p.read_bytes()).hexdigest())
    for n in z.namelist():
        try:t=z.read(n).decode('utf-8-sig')
        except UnicodeError:continue
        if 'ST3_A_Dis1_M' not in t:continue
        print('ENTRY',n)
        if t.lstrip().startswith('{'):
            for rn,line in enumerate(t.splitlines()):
                if not line.strip():continue
                r=json.loads(line)
                hits=[(i,c) for i,c in enumerate(r.get('CLs',[])) if 'ST3_A_Dis1_M' in json.dumps(c)]
                if not hits:continue
                print('RUNG',rn,'CMT',r.get('CMT',''))
                if '--rung8' in sys.argv and rn==8:hits=list(enumerate(r.get('CLs',[])))
                for i,c in hits:print('CELL',i,json.dumps(c,ensure_ascii=False))
        else:
            for line in t.splitlines():
                if 'ST3_A_Dis1_M' in line:print(line)
