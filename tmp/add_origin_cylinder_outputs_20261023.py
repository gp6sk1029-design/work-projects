"""C版の指定パターンを保持し、シリンダ原点復帰の出力枝9組だけを追加する。"""
from pathlib import Path
from zipfile import ZipFile
from xml.sax.saxutils import quoteattr
import collections,copy,datetime,hashlib,json,re,shutil,sys,tempfile,uuid,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
BASE=Path(__file__).parent
SRC=next(Path(r'C:\Users\SEIGI-N13\Desktop').glob('3089-2603A_*_20261023C.smc2'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source_hash=sha(SRC)
assert source_hash=='c0cfe7d3fc6254a4f670c1f40d0f8af1b79459a4edda2a03c126b71209a70fcb','前回確認後にC版が更新された'
with ZipFile(SRC) as z:
    infos=z.infolist();zipcomment=z.comment;original={i.filename:z.read(i) for i in infos}
oempath=next(n for n in original if n.endswith('.oem'));prefix=oempath.rsplit('/',1)[0]+'/'
path=lambda s:prefix+s+'.xml'
OUTPUT=path('09c1f70b-b9ac-4e5d-884f-9779e69a597a')
IO=path('9576fedf-9472-4ce6-b9ed-6eda5b4f0514')
GLOBAL=path('f07dd06c-505c-431b-b9fc-098949805b4e')
ORIGIN=path('a6a85ff3-f6aa-4c8c-a49b-ae9f1e045ba8')
MOTOR=path('4bc99ae0-7ace-4891-a17a-c3fe2079278d')
decode=lambda n:original[n].decode('utf-8-sig')
def records(text):
    return {r['N']:r for r in [dict(p.split('=',1) for p in l.lstrip('+').split('\t') if '=' in p)
            for l in text.splitlines() if l.startswith('++')]}
globals_=records(decode(GLOBAL));io_text=decode(IO);io_vars=records(io_text)
before=[json.loads(l) for l in decode(OUTPUT).splitlines() if l.strip()]
after=copy.deepcopy(before);changes=[];existing=[];newdecls=[]
def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values():yield from walk(v)
    elif isinstance(obj,list):
        for v in obj:yield from walk(v)
    return
for rn,r in enumerate(after):
    physical=next((c['Var'] for c in r['CLs'] if c.get('__type')=='ST' and
        re.fullmatch(r'Out_CYw_Rev_0[12]_(?:Pick|Chk)_[AB]_[HF]',c.get('Var',''))),None)
    if physical is None:continue
    num,mechanism,side,direction=re.fullmatch(r'Out_CYw_Rev_(0[12])_(Pick|Chk)_([AB])_([HF])',physical).groups()
    if (mechanism,direction) not in [('Pick','H'),('Pick','F'),('Chk','H')]:continue
    array=physical+'_Origin';target=array+'[1]'
    assert array in globals_ and globals_[array]['D'].startswith('ARRAY'),array
    if any(c.get('Var')==target for c in r['CLs']):
        existing.append((rn,target));continue
    old_rung=copy.deepcopy(r)
    maxix=max([r['LRI'],r['RRI']]+[c.get('Ix',0) for c in walk(r)])+1
    # 既存の手動/自己保持枝を1行だけ下へずらし、原点復帰枝を挿入する。
    for c in r['CLs']:
        if c.get('Y',0)>=1:c['Y']+=1
    for v in r['VLs']:
        if v.get('Y',0)>=1:v['Y']+=1
    r['CLs'] += [
        {'__type':'LD','Var':target,'X':0,'Y':1,'Ix':maxix},
        {'__type':'F','Name':'Up','X':1,'Y':1,'Ix':maxix+1,'Id':str(uuid.uuid4()),
         'In':[{'__type':'PF','Arg':'In'}],'Out':[{'__type':'PF','Arg':''}]},
        {'__type':'HL','X':2,'Y':1},{'__type':'HL','X':3,'Y':1}]
    first_vertical=[v for v in r['VLs'] if v.get('X')==4 and v.get('Y',0)==0]
    assert len(first_vertical)==1,(rn,first_vertical)
    first_vertical[0]['Y']=1
    r['VLs'].append({'Ix':maxix+2,'X':4,'Y':0})
    # 挿入を逆変換すると元のラダーに完全一致することを確認する。
    restored=copy.deepcopy(r);restored['CLs']=restored['CLs'][:-4];restored['VLs']=restored['VLs'][:-1]
    for c in restored['CLs']:
        if c.get('Y',0)>=2:c['Y']-=1
    for v in restored['VLs']:
        if v.get('Y',0)>=2:v['Y']-=1
        elif v.get('X')==4 and v.get('Y')==1:v.pop('Y',None)
    assert restored==old_rung,('既存条件の変更',rn)
    if array not in io_vars:
        row=globals_[array]
        line='++D='+row['D']+'\tN='+array+'\tG=VAR_EXTERNAL\tCom='+row.get('Com','')+'\r\n'
        io_text+=line;newdecls.append((array,row['D'],row.get('Com','')))
        io_vars=records(io_text)
    assert io_vars[array]['D']==globals_[array]['D']
    changes.append({'行':rn,'変数':target,'出力':physical,'コメント':r.get('CMT','')})
assert len(changes)==9 and len(existing)==3 and len(newdecls)==9
assert len(before)==len(after)==316

# 保存した配線に相当するブール論理を走査し、既存条件が全枝に有効なことを確認。
def evaluate(r,state):
    graph=collections.defaultdict(set);height=max(c.get('Y',0) for c in r['CLs'])
    for v in r['VLs']:
        x=v['X'];y=v.get('Y',0);graph[(x,y)].add((x,y+1));graph[(x,y+1)].add((x,y))
    pending=[]
    for c in r['CLs']:
        x=c.get('X',0);y=c.get('Y',0);kind=c['__type']
        if kind=='HL':graph[(x,y)].add((x+1,y))
        elif kind=='LD':
            val=state.get(c['Var'],False)
            if c.get('Not'):val=not val
            if val:graph[(x,y)].add((x+1,y))
        elif kind=='F':
            assert c['Name']=='Up';pending.append((x,y))
        else:assert kind=='ST'
    def reachable():
        reached={(0,y) for y in range(height+1)};todo=list(reached)
        while todo:
            p=todo.pop()
            for q in graph[p]:
                if q not in reached:reached.add(q);todo.append(q)
        return reached
    reached=reachable()
    for p in pending:
        if p in reached:graph[p].add((p[0]+1,p[1]))
    reached=reachable()
    return {c['Var']:(c.get('X',0),c.get('Y',0)) in reached for c in r['CLs'] if c['__type']=='ST'}
logical_checks=[]
for change in changes:
    r=after[change['行']];request=change['変数'];physical=change['出力']
    assert evaluate(r,{request:True})[physical]
    logical_checks.append('原点復帰枝の導通:'+physical)
    for c in before[change['行']]['CLs']:
        if c.get('__type')=='LD' and c.get('Not'):
            assert not evaluate(r,{request:True,c['Var']:True})[physical],(physical,c['Var'])
            logical_checks.append('既存遮断条件保持:'+physical+':'+c['Var'])

output_text=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in after)
oem=decode(oempath)
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%m/%d/%Y %H:%M:%S')
for n in [OUTPUT,IO]:
    ident=Path(n).stem
    oem,count=re.subn(r'<Entity\b[^>]*\bid="'+ident+r'"[^>]*>',
        lambda m:re.sub(r'dateLastModified="[^"]*"','dateLastModified='+quoteattr(now),m[0]),oem)
    assert count==1
ET.fromstring(oem)
updates={OUTPUT:output_text,IO:io_text,oempath:oem}
payload=dict(original)
for n,t in updates.items():payload[n]=t.encode('utf-8-sig' if original[n].startswith(b'\xef\xbb\xbf') else 'utf-8')
assert payload[ORIGIN]==original[ORIGIN] and payload[MOTOR]==original[MOTOR]
assert all(payload[n]==b for n,b in original.items() if n not in updates)
assert sha(SRC)==source_hash
with tempfile.NamedTemporaryFile(prefix='cylinder_origin_',suffix='.smc2',dir=BASE,delete=False) as f:stage=Path(f.name)
with ZipFile(stage,'w') as z:
    z.comment=zipcomment
    for info in infos:z.writestr(info,payload[info.filename])
with ZipFile(stage) as z:
    assert z.testzip() is None and z.namelist()==list(original)
    assert [json.loads(l) for l in z.read(OUTPUT).decode('utf-8-sig').splitlines() if l.strip()]==after
    assert z.read(ORIGIN)==original[ORIGIN] and z.read(MOTOR)==original[MOTOR]
    assert set(records(z.read(IO).decode('utf-8-sig')))-set(records(decode(IO)))=={n for n,d,c in newdecls}

backup=Path(tempfile.mkdtemp(prefix='C版_シリンダ出力追加前_20261023_',dir=SRC.parent))
for f in [SRC,SRC.with_suffix('.変更内容.txt'),SRC.with_suffix('.変数一覧.txt'),SRC.with_suffix('.検証結果.json')]:
    if f.exists():shutil.copy2(f,backup/f.name)
assert sha(backup/SRC.name)==source_hash
stage.replace(SRC)
result={'日付':'2026-10-23','C版':str(SRC),'上書き前バックアップ':str(backup),
    '変更前SHA256':source_hash,'変更後SHA256':sha(SRC),
    '追加した原点復帰出力枝':changes,'既存の原点復帰出力枝':existing,
    '追加外部変数':newdecls,'原点復帰ラダー28行':'全バイト不変',
    'モータセクション':'全バイト不変','出力セクション行数':316,
    '既存条件の確認':logical_checks,'変更エントリ':list(updates),
    '不変エントリ数':len(original)-len(updates),'Sysmac読込み・ビルド':'未実施','PLC接続・転送':'なし'}
SRC.with_suffix('.検証結果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
report=['C版 画像パターン保持＋シリンダ原点復帰出力の追加','更新日：2026-10-23',
    'C版：'+str(SRC),'上書き前バックアップ：'+str(backup),'',
    '【今回の変更】',
    'Origin_原点復帰は画像の7行×4組＝28行を全バイト保持。',
    'Output_出力へ追加3組分の原点復帰指令接点＋Up枝を9か所追加。',
    'A/ST4の既存3か所を含め、4組各3指令＝12か所のシリンダ出力へ接続。',
    '指令は各組のピックアップ戻・ピックアップ行・チャック閉の_Origin[1]。',
    'IO_入出力のVAR_EXTERNALへ既存グローバル配列の外部参照を9件追加。型とコメントは実体に一致。','']
report += [f"行{x['行']}：{x['変数']} → {x['出力']} ／ {x['コメント']}" for x in changes]
report += ['','【変更していないもの】',
    '共通開始パルス・リセット・Busy/完了集約・追加インターロックは作っていない。',
    '元のモータBusy接点、非常停止、一時停止、出力保持/リセットタイマの条件を維持。',
    'CV2A_KEDのモータ処理を変更せず、追加3軸のモータ原点復帰FBも追加していない。',
    '機器/軸/EtherCAT設定、グローバル変数、原点復帰28行、その他セクションを保持。',
    '同時開始・終了/再始動・追加モータ制御などの後段処理は利用者が設計する。',
    '今回シリンダ出力は接続したが、全体の原点復帰運転が完成した版ではない。','',
    '【検証】',
    '既存枝を逆変換して元回路との一致を確認。追加9枝で原点指令の導通と既存遮断条件を確認。',
    'ブール論理走査はSysmacシミュレータ/MC命令/実機の検証ではない。',
    f'ZIP/JSON/宣言/型を読戻し検証。変更は出力/IO外部変数/OEM時刻の3エントリ、他{len(original)-3}件不変。',
    'Sysmac Studioでの読込み・全体再ビルド・実機動作は未検証。PLC接続・転送なし。',
    '変更前C SHA256：'+source_hash,'変更後C SHA256：'+sha(SRC)]
SRC.with_suffix('.変更内容.txt').write_text('\n'.join(report)+'\n',encoding='utf-8-sig')
old_listing=(backup/SRC.with_suffix('.変数一覧.txt').name).read_text(encoding='utf-8-sig')
listing=old_listing.replace('新規グローバル（宣言のみ・後段未接続）',
    '既存の新規グローバル（シリンダ原点復帰配列は今回Outputへ接続、追加モータ信号等は後段未接続）')
listing+='\n【今回追加したIO外部参照（シリンダ原点復帰出力用）】\n'+'\n'.join(' / '.join(row) for row in newdecls)+'\n'
SRC.with_suffix('.変数一覧.txt').write_text(listing,encoding='utf-8-sig')
(BASE/'origin_cylinder_outputs_verification_20261023.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['既存条件の確認','追加外部変数','変更エントリ']},ensure_ascii=False,indent=2))
