"""画像の7行パターンだけを4組へ複製し、却下されたC版をバックアップ後に置換する。"""
from pathlib import Path
from zipfile import ZipFile
from xml.sax.saxutils import quoteattr,escape
import collections,copy,datetime,hashlib,json,re,shutil,sys,tempfile,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8');sys.stderr.reconfigure(encoding='utf-8')
BASE=Path(__file__).parent
SRC=next(Path(r'C:\Users\SEIGI-N13\Desktop').glob('3089-2603A_*_20261023B.smc2'))
DST=SRC.with_name(SRC.stem[:-1]+'C.smc2')
EXPECTED_B='c6a9531be2fc5c8287c127edfb8af0f994373be5c312ab02f391a519f939e736'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(SRC)==EXPECTED_B
old_c_hash=sha(DST)
with ZipFile(SRC) as z:
    infos=z.infolist();zipcomment=z.comment;original={i.filename:z.read(i) for i in infos}
oempath=next(n for n in original if n.endswith('.oem'))
prefix=oempath.rsplit('/',1)[0]+'/'
GLOBAL='f07dd06c-505c-431b-b9fc-098949805b4e';MODE='b530d740-9d69-41c3-974a-97c06e823eb2'
ORIGIN='a6a85ff3-f6aa-4c8c-a49b-ae9f1e045ba8';META='20a6b651-4c34-401a-965e-db3e18414d5c'
MOTOR='4bc99ae0-7ace-4891-a17a-c3fe2079278d';OUTPUT='09c1f70b-b9ac-4e5d-884f-9779e69a597a'
path=lambda ident:prefix+ident+'.xml'
texts={}
for n,b in original.items():
    try:texts[n]=b.decode('utf-8-sig')
    except UnicodeError:pass
def records(t):
    return {r['N']:r for r in [dict(p.split('=',1) for p in l.lstrip('+').split('\t') if '=' in p)
                              for l in t.splitlines() if l.startswith('++')]}
def station_comment(comment,context=''):
    comment=comment.replace('旋回','反転')
    def inject(m):
        station='ST4' if m[1]=='1' else 'ST6'
        return m[0] if station in comment else station+' '+m[0]
    comment=re.sub(r'反転([12])(?!\d)',inject,comment)
    match=re.search(r'_Rev_(01|02)_',context)
    if match and not re.search(r'\bST[46]\b',comment):comment=('ST4 ' if match[1]=='01' else 'ST6 ')+comment
    return comment
updated={n:t.replace('_Swv_','_Rev_').replace('旋回','反転') for n,t in texts.items()}
for n,t in list(updated.items()):
    if t.startswith('[SLWD'):
        lines=[]
        for line in t.splitlines(keepends=True):
            match=re.search(r'\tN=([^\t\r\n]+)',line);context=match[1] if match else ''
            line=re.sub(r'(?<=\tCom=)[^\t\r\n]*',lambda m:station_comment(m[0],context),line)
            line=re.sub(r' C="([^"]*)"',lambda m:' C='+quoteattr(station_comment(ET.fromstring('<v C="'+m[1]+'"/>').get('C'),context)),line)
            lines.append(line)
        updated[n]=''.join(lines)
    elif t.lstrip().startswith('{') and '"CLs"' in t:
        updated[n]=re.sub(r'"CMT":("(?:\\.|[^"\\])*")',lambda m:'"CMT":'+json.dumps(station_comment(json.loads(m[1])),ensure_ascii=False),t)

def rows(ident):return records(updated[path(ident)])
def add(ident,name,dtype,group,comment,ec=None):
    assert name not in rows(ident),name
    line='++D='+dtype+'\tN='+name+'\tG='+group+'\tCom='+comment
    if ec:line+='\tEC=<ECs>'+''.join('<EC EK="['+str(i)+']" C='+quoteattr(c)+' />' for i,c in ec.items())+'</ECs>'
    line+='\r\n';n=path(ident)
    if group=='VAR':
        marker='+GN=VAR_EXTERNAL';pos=updated[n].index(marker)
        updated[n]=updated[n][:pos]+line+updated[n][pos:]
    else:updated[n]+=line
def comment(ident,name,value,ec=None):
    pat=r'(?m)^\+\+[^\r\n]*\tN='+re.escape(name)+r'(?=\t|$)[^\r\n]*'
    def replace(m):
        parts=[p for p in m[0].split('\t') if not p.startswith('Com=') and not (ec is not None and p.startswith('EC='))]
        parts.append('Com='+value)
        if ec is not None:parts.append('EC=<ECs>'+''.join('<EC EK="['+str(i)+']" C='+quoteattr(c)+' />' for i,c in ec.items())+'</ECs>')
        return '\t'.join(parts)
    updated[path(ident)],count=re.subn(pat,replace,updated[path(ident)]);assert count==1,(ident,name)

groups=[{'side':side,'number':num,'station':station,'axis':axis,
    'seq':f'ST4_{side}_Rev_{num}_Origin_M','done':f'ST4_{side}_Rev_{num}_OriginDone',
    'label':side+('(左側)' if side=='A' else '(右側)')+' '+station+' 反転'+num[-1]}
    for side,num,station,axis in [('A','01','ST4','Stm_A_Rev_Axis000'),('A','02','ST6','Stm_A_Rev_Axis001'),
                                 ('B','01','ST4','Stm_B_Rev_Axis002'),('B','02','ST6','Stm_B_Rev_Axis003')]]
template=[json.loads(l) for l in updated[path(ORIGIN)].splitlines() if l.strip()]
assert len(template)==7
newglobals=[]
def ensure_global(name,dtype,description,sample):
    if name not in rows(GLOBAL):
        add(GLOBAL,name,dtype,'VAR_GLOBAL',description)
        newglobals.append((name,dtype,description,sample))
def external(name):
    real=rows(GLOBAL)[name]
    if name not in rows(MODE):add(MODE,name,real['D'],'VAR_EXTERNAL',real.get('Com',''))
    else:assert rows(MODE)[name]['D'].lower()==real['D'].lower(),name

def map_var(value,g):
    value=value.replace('ST4_A_Rev_01_Origin_M',g['seq']).replace('ST4_A_Rev_01_OriginDone',g['done'])
    value=value.replace('Stm_A_Rev_Axis000',g['axis'])
    value=re.sub(r'(Out_CYw_Rev_)01_(Pick|Chk)_A_',lambda m:m[1]+g['number']+'_'+m[2]+'_'+g['side']+'_',value)
    value=value.replace('TimerQ_In_Sen_Work_A_Pos_04','TimerQ_In_Sen_Work_'+g['side']+'_Pos_'+('04' if g['number']=='01' else '06'))
    if g['side']=='B':value=value.replace('Auto_A_Start','Auto_B_Start')
    return value
def remap(obj,g):
    if isinstance(obj,dict):return {k:(map_var(v,g) if k=='Var' and isinstance(v,str) else remap(v,g)) for k,v in obj.items()}
    if isinstance(obj,list):return [remap(v,g) for v in obj]
    return obj
def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values():yield from walk(v)
    elif isinstance(obj,list):
        for v in obj:yield from walk(v)
newrungs=[]
for ix,g in enumerate(groups):
    labels={1:g['label']+' 原点復帰開始',2:g['label']+' 原点復帰中',3:g['label']+' ピックアップ戻',
        4:g['label']+' モータ原点復帰開始',5:g['label']+' ピックアップ行',6:g['label']+' チャック閉',
        7:g['label']+' 原点復帰完了（ワーク無）'}
    if ix:
        add(MODE,g['seq'],'ARRAY[0..99] OF Bool','VAR',g['label']+' 原点復帰工程',labels)
        add(MODE,g['done'],'BOOL','VAR',g['label']+' 原点復帰完了')
    else:
        comment(MODE,g['seq'],g['label']+' 原点復帰工程',labels)
        comment(MODE,g['done'],g['label']+' 原点復帰完了')
    if g['side']=='B':
        ensure_global('Auto_B_Start','BOOL','B(右側)自動運転開始（後続処理未接続）','Auto_A_Start')
    for suffix,label in [('_Origin','モータ原点復帰開始'),('_OriginDone','モータ原点復帰完了')]:
        name=g['axis']+suffix
        ensure_global(name,'BOOL',g['label']+' '+label,'Stm_A_Rev_Axis000'+suffix)
        comment(GLOBAL,name,g['label']+' '+label)
    block=remap(copy.deepcopy(template),g)
    for i,r in enumerate(block):
        r['CMT']=('#' if i==0 else '')+labels[i+1]
        # 行コメントの工程2/3以降はラダーの動作順に合わせる。
        r['CMT']=('#' if i==0 else '')+g['label']+' '+[
            '原点復帰開始','原点復帰中','ピックアップ戻','モータ原点復帰開始','ピックアップ行','チャック閉','原点復帰完了（ワーク無）'][i]
        if i in [2,4,5]:
            array=next(c['Var'].split('[')[0] for c in r['CLs'] if c.get('__type')=='ST' and c.get('Var','').startswith('Out_CYw_'))
            physical=array.removesuffix('_Origin');real=rows(GLOBAL)[physical]
            ensure_global(array,rows(GLOBAL)[{'Pick_H':'Out_CYw_Rev_01_Pick_A_H_Origin',
                'Pick_F':'Out_CYw_Rev_01_Pick_A_F_Origin','Chk_H':'Out_CYw_Rev_01_Chk_A_H_Origin'}['_'.join(physical.split('_')[-3::2])]]['D'],
                '原点復帰 '+real.get('Com',''),
                {'Pick_H':'Out_CYw_Rev_01_Pick_A_H_Origin','Pick_F':'Out_CYw_Rev_01_Pick_A_F_Origin','Chk_H':'Out_CYw_Rev_01_Chk_A_H_Origin'}['_'.join(physical.split('_')[-3::2])])
            tag=re.search(r'【Y\d+】',real.get('Com',''))
            if tag:r['CMT']=tag[0]+' '+r['CMT']
    for c in walk(block):
        if 'Var' not in c:continue
        base=re.split(r'[.\[]',c['Var'])[0]
        if base not in rows(MODE):external(base)
    newrungs.extend(block)
assert len(newrungs)==28
updated[path(ORIGIN)]=''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in newrungs)

# 改名した変数のコメントだけをグローバルと外部参照で一致させる。
for n,t in list(updated.items()):
    if not t.startswith('[SLWD') or n==path(GLOBAL):continue
    for name,row in list(records(t).items()):
        if row['G']=='VAR_EXTERNAL' and '_Rev_' in name and name in rows(GLOBAL):
            comment(Path(n).stem,name,rows(GLOBAL)[name].get('Com',''))

# 宣言した未接続信号のメタ情報だけを追加し、FBや出力命令は追加しない。
meta=updated[path(META)];root=ET.fromstring(meta)
metadata={e.get('Name'):e for e in root.iter('Variable')}
extras=[]
import uuid
for name,dtype,description,sample in newglobals:
    assert name not in metadata
    element=copy.deepcopy(metadata[sample]);element.tail=None
    element.set('Name',name);element.set('Address','new_Controller_0.'+name)
    element.set('Comment',description);element.set('Id',str(uuid.uuid4()))
    extras.append('    '+ET.tostring(element,encoding='unicode')+'\r\n')
meta=meta.replace('</VariableGroup>',''.join(extras)+'</VariableGroup>')
def sync_meta(m):
    e=ET.fromstring(m[0]);name=e.get('Name')
    if name not in rows(GLOBAL):return m[0]
    return re.sub(r'Comment="[^"]*"','Comment='+quoteattr(rows(GLOBAL)[name].get('Com','')),m[0])
updated[path(META)]=re.sub(r'<Variable\b[^>]*?/>',sync_meta,meta)

now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%m/%d/%Y %H:%M:%S')
oem=updated[oempath]
for n,t in updated.items():
    enc='utf-8-sig' if original[n].startswith(b'\xef\xbb\xbf') else 'utf-8'
    if t.encode(enc)==original[n]:continue
    ident=Path(n).stem
    oem=re.sub(r'<Entity\b[^>]*\bid="'+re.escape(ident)+r'"[^>]*>',lambda m:re.sub(r'dateLastModified="[^"]*"','dateLastModified='+quoteattr(now),m[0]),oem)
updated[oempath]=oem
payload=dict(original)
for n,t in updated.items():payload[n]=t.encode('utf-8-sig' if original[n].startswith(b'\xef\xbb\xbf') else 'utf-8')

# 原本と同じ接点・コイル・分岐・座標・Ix・命令属性であることを直接比較する。
checks=0
def check(condition,message):
    global checks
    assert condition,message
    checks+=1
for index,g in enumerate(groups):
    expected=remap(copy.deepcopy(template),g)
    actual=copy.deepcopy(newrungs[index*7:(index+1)*7])
    for er,ar in zip(expected,actual):er.pop('CMT',None);ar.pop('CMT',None)
    check(expected==actual,'画像パターンの回路構造不変:'+g['label'])
    for k in range(1,8):
        check(sum(c.get('__type')=='ST' and c.get('Var')==g['seq']+f'[{k}]' for r in actual for c in r['CLs'])==1,'工程出力一意')
    for c in walk(actual):
        if c.get('Var'):check(re.split(r'[.\[]',c['Var'])[0] in rows(MODE),'参照変数の宣言:'+c['Var'])
for n,t in updated.items():
    check('_Swv_' not in t and '旋回' not in t,'名前・コメントの置換:'+n)
    if t.lstrip().startswith('<') and n.endswith(('.xml','.oem')):ET.fromstring(t)
    if t.startswith('[SLWD'):
        old=records(texts[n]);new=records(t)
        for name,row in old.items():
            newname=name.replace('_Swv_','_Rev_');check(newname in new,'既存変数保持')
            for attr,val in row.items():
                if attr not in ['N','Com','EC']:check(new[newname].get(attr)==val,'既存型・割付保持')
for ident in [MOTOR,OUTPUT]:
    before=[json.loads(l) for l in texts[path(ident)].splitlines() if l.strip()]
    after=[json.loads(l) for l in updated[path(ident)].splitlines() if l.strip()]
    def normalize(obj):
        if isinstance(obj,dict):return {k:normalize(v) for k,v in obj.items() if k!='CMT'}
        if isinstance(obj,list):return [normalize(v) for v in obj]
        if isinstance(obj,str):return obj.replace('_Swv_','_Rev_').replace('旋回','反転')
        return obj
    check(normalize(before)==normalize(after),'関連セクションの制御追加撤回:'+ident)
check('Origin_StartPulse' not in '\n'.join(updated.values()),'却下された共通開始なし')
check('OriginBusy' not in updated[path(ORIGIN)],'個別Busy新設なし')
check(not any(c.get('R') for c in walk(newrungs) if c.get('__type')=='ST'),'リセット処理追加なし')
check(sum(c.get('Var')=='Origin_Busy' and c.get('__type')=='ST' for c in walk(newrungs))==4,'共通Busyも画像どおり複製')
check(not any(c.get('Var')=='OriginDone' and c.get('__type')=='ST' for c in walk(newrungs)),'全体完了集約なし')
check(all(payload[n]==b for n,b in original.items() if n.endswith(('.dat','.stsdb4'))),'機器・軸・埋込DB不変')
assert sha(SRC)==EXPECTED_B and sha(DST)==old_c_hash

# 一時ファイルを検査し終えてから既存Cをバックアップし、利用者指定のCに上書きする。
with tempfile.NamedTemporaryFile(prefix='origin_template_',suffix='.smc2',dir=BASE,delete=False) as f:stage=Path(f.name)
with ZipFile(stage,'w') as zout:
    zout.comment=zipcomment
    for info in infos:zout.writestr(info,payload[info.filename])
with ZipFile(stage) as z:
    check(z.testzip() is None,'保存ZIP正常')
    check(z.namelist()==list(original),'新しいエントリの追加なし')
    check([json.loads(l) for l in z.read(path(ORIGIN)).decode('utf-8-sig').splitlines() if l.strip()]==newrungs,'保存ラダー28行読戻し一致')
backup=Path(tempfile.mkdtemp(prefix='C版_差戻し前バックアップ_20261023_',dir=SRC.parent))
for f in [DST,DST.with_suffix('.変更内容.txt'),DST.with_suffix('.変数一覧.txt'),DST.with_suffix('.検証結果.json')]:
    if f.exists():shutil.copy2(f,backup/f.name)
check(sha(backup/DST.name)==old_c_hash,'旧C版のバックアップ一致')
stage.replace(DST)
changed=[n for n in original if payload[n]!=original[n]]
result={'日付':'2026-10-23','原本':str(SRC),'上書き先':str(DST),'退避先':str(backup),
    '原本SHA256':EXPECTED_B,'旧C版SHA256':old_c_hash,'新C版SHA256':sha(DST),
    '検証件数':checks,'原点復帰行数':28,'新規グローバル宣言':len(newglobals),
    '変更エントリ':changed,'不変エントリ数':len(original)-len(changed),'追加エントリ数':0,
    'Sysmac読込み・ビルド':'未実施','PLC接続・転送':'なし',
    '用途':'指定された画像パターンの複製用ひな形。後段制御は利用者が設計する。'}
DST.with_suffix('.検証結果.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
notes=['原点復帰 画像パターン複製版（C上書き）','作成日：2026-10-23',
    '原本B：'+str(SRC),'上書きC：'+str(DST),'上書き前Cのバックアップ：'+str(backup),'',
    '【今回の確定ルール】',
    '提示された0～6行の7行パターンは、接点種別・自己保持・分岐・コイル・順番・配置を変えない。',
    '変数の対応と行/変数/要素コメントだけを変更して4組へ複製する。',
    '共通開始パルス、リセット、Busy/完了集約、追加インターロックを独断で作らない。',
    'FB増設・サーボON・出力接点・Busy差替え等、前C版で追加した関連制御もBの内容へ戻す。',
    '後段の接続・同時開始・終了/再始動処理は利用者が設計する。','',
    '【保持した名称・コメント変更】',
    '_Swv_→_Rev_、旋回→反転。01=ST4、02=ST6をコメントへ追加。',
    '変数名は指定のST4_A_Rev_02等を維持し、コメントにST6を記す。','',
    '【原点復帰ラダー28行】']
for i,g in enumerate(groups):notes.append(f"行{i*7}～{i*7+6}：{g['seq']} / {g['label']} / {g['axis']}")
notes += ['','【未接続のまま残すもの】',
    'Origin_Busyは画像どおり各組から同じ変数へ出力する。集約方法は追加していない。',
    'B側開始条件はAuto_B_Startへ対応させ、BOOL宣言のみ追加。B側自動運転処理との接続は未実装。',
    '追加3軸のモータ原点復帰開始/完了はBOOL信号の宣言のみ。原点復帰FBは追加しない。',
    '追加3組のシリンダ原点復帰配列は宣言のみ。Output側の新しい接点は追加しない。',
    'したがって今回は編集用ひな形であり、4組同時動作を完成・保証した版ではない。',
    '機器・軸設定・I/Oアドレス・元のCV2A_KEDの処理を変更していない。',
    '元Bは変更なし。旧Cは上記へ退避したため復元可能。',
    'Sysmac Studioでの読込み・ビルド・実機動作は未検証。PLC接続/転送なし。','',
    '【検証】',f'画像の7行と4組の構造を比較。確認{checks}件。',
    f'ZIP内{len(changed)}件変更、{len(original)-len(changed)}件不変、追加エントリなし。',
    '原本B SHA256：'+EXPECTED_B,'新C SHA256：'+sha(DST)]
DST.with_suffix('.変更内容.txt').write_text('\n'.join(notes)+'\n',encoding='utf-8-sig')
listing=['画像パターン複製版 変数一覧','新規グローバル（宣言のみ・後段未接続）']
listing += [' / '.join(x[:3]) for x in newglobals]
listing += ['','工程配列/完了ビット']+[g['seq']+' / '+g['done']+' / '+g['label'] for g in groups]
listing += ['','全28行の行コメント']+[str(i)+': '+r['CMT'] for i,r in enumerate(newrungs)]
DST.with_suffix('.変数一覧.txt').write_text('\n'.join(listing)+'\n',encoding='utf-8-sig')
(BASE/'origin_template_restore_verification_20261023.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='変更エントリ'},ensure_ascii=False,indent=2))
