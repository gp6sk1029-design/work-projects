"""消えた表示の原因になった9行の内部参照を、正常原本から組み直す。"""
from pathlib import Path
from zipfile import ZipFile
import copy,hashlib,json,re,sys,tempfile,uuid
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
BASE=Path(__file__).parent
C=next(Path(r'C:\Users\SEIGI-N13\Desktop').glob('3089-2603A_*_20261023C.smc2'))
assert hashlib.sha256(C.read_bytes()).hexdigest()=='e09c4681e30b39a9b635ba045c9fb610aeb6a8699c5c8f684de8677c02580009'
source=C.parent/'C版_シリンダ出力追加前_20261023_qdbjjeco'/C.name
assert hashlib.sha256(source.read_bytes()).hexdigest()=='c0cfe7d3fc6254a4f670c1f40d0f8af1b79459a4edda2a03c126b71209a70fcb'
with ZipFile(C) as z:
    infos=z.infolist();comment=z.comment;payload={i.filename:z.read(i) for i in infos}
target=next(n for n in payload if n.endswith('09c1f70b-b9ac-4e5d-884f-9779e69a597a.xml'))
with ZipFile(source) as z:
    normal=[json.loads(l) for l in z.read(target).decode('utf-8-sig').splitlines() if l.strip()]
before=[json.loads(l) for l in payload[target].decode('utf-8-sig').splitlines() if l.strip()]
rows=copy.deepcopy(normal);changed=[]
def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values():yield from walk(v)
    elif isinstance(obj,list):
        for v in obj:yield from walk(v)
for rn,r in enumerate(rows):
    physical=next((c['Var'] for c in r['CLs'] if c.get('__type')=='ST' and re.fullmatch(r'Out_CYw_Rev_0[12]_(?:Pick|Chk)_[AB]_[HF]',c.get('Var',''))),None)
    if not physical:continue
    num,mechanism,side,direction=re.fullmatch(r'Out_CYw_Rev_(0[12])_(Pick|Chk)_([AB])_([HF])',physical).groups()
    if (mechanism,direction) not in [('Pick','H'),('Pick','F'),('Chk','H')]:continue
    request=physical+'_Origin[1]'
    if any(c.get('Var')==request for c in r['CLs']):continue
    # 左/右母線より前に部品番号を確保し、母線と縦線番号も2つ後ろへ送る。
    insert=r['LRI']
    assert all(c.get('Ix',0)<insert for c in walk(r['CLs']))
    r['LRI']+=2;r['RRI']+=2
    for c in r['CLs']:
        # 入力側の枝だけを下げる。右側の並列コイルを下げると接続が切れる。
        if c.get('Y',0)>=1 and c.get('X',0)<4:c['Y']+=1
    for v in r['VLs']:
        v['Ix']+=2
        if v['X']==4 and v.get('Y',0)>=1:v['Y']+=1
    join=[v for v in r['VLs'] if v['X']==4 and v.get('Y',0)==0]
    assert len(join)==1
    # 連続した縦線の全区間は同じ部品番号を共有する。
    vertical_index=join[0]['Ix'];join[0]['Y']=1
    r['VLs'].append({'Ix':vertical_index,'X':4})
    r['CLs'] += [
        {'__type':'LD','Ix':insert,'Var':request,'Y':1},
        {'__type':'F','In':[{'__type':'PF','Arg':'In'}],'Ix':insert+1,'Name':'Up',
         'Out':[{'__type':'PF','Arg':''}],'X':1,'Y':1,'Id':str(uuid.uuid4())},
        {'__type':'HL','X':2,'Y':1},{'__type':'HL','X':3,'Y':1}]
    assert max(c.get('Ix',0) for c in walk(r['CLs']))<r['LRI']<r['RRI']
    assert all(v['Ix']>r['RRI'] for v in r['VLs'])
    changed.append((rn,request))
assert len(rows)==316 and [n for n,t in changed]==[88,94,97,184,190,193,196,202,205]
for rn,r in enumerate(rows):
    if rn not in {n for n,t in changed}:assert r==before[rn]
payload[target]=(b'\xef\xbb\xbf' if payload[target].startswith(b'\xef\xbb\xbf') else b'')+''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in rows).encode('utf-8')
stage=BASE/'output_repaired_nativecheck_20261023.smc2'
if stage.exists():
    assert hashlib.sha256(stage.read_bytes()).hexdigest()=='0e6ca0c7d0114d27cd5a951b2190518883fdba9829bbc0920c0b71ba39b2a71e','今回の検証用以外は上書きしない'
with ZipFile(stage,'w') as z:
    z.comment=comment
    for info in infos:z.writestr(info,payload[info.filename])
with ZipFile(stage) as z:assert z.testzip() is None
print(json.dumps({'検証用ファイル':str(stage),'変更行':changed,'行数':len(rows),'SHA256':hashlib.sha256(stage.read_bytes()).hexdigest()},ensure_ascii=False,indent=2))
