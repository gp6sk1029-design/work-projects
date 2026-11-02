"""反転名の統一と4組同時原点復帰の確認用C版を生成する。実機へ接続しない。"""
from pathlib import Path
from zipfile import ZipFile
import copy,datetime,hashlib,json,re,sys,uuid,xml.etree.ElementTree as ET
from xml.sax.saxutils import escape,quoteattr

sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).parent
SOURCE=next(Path(r'C:\Users\SEIGI-N13\Desktop').glob('3089-2603A_*_20261023B.smc2'))
DEST=SOURCE.with_name(SOURCE.stem[:-1]+'C.smc2')
SOURCE_HASH='c6a9531be2fc5c8287c127edfb8af0f994373be5c312ab02f391a519f939e736'
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_HASH,'調査後に原本が更新された'
if DEST.exists():
    assert hashlib.sha256(DEST.read_bytes()).hexdigest() in {
        '9c6c8aceb59172be4be6edfb918e983086a1a7af19048c7bb34d36521d882dd2'
    },'今回生成した未納品C版以外は上書きしない'
NOW=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime('%m/%d/%Y %H:%M:%S')
with ZipFile(SOURCE) as zin:
    INFOS=zin.infolist(); ZIP_COMMENT=zin.comment
    ORIGINAL={i.filename:zin.read(i) for i in INFOS}

PREFIX=next(n.rsplit('/',1)[0]+'/' for n in ORIGINAL if n.endswith('.oem'))
GLOBAL='f07dd06c-505c-431b-b9fc-098949805b4e'
MODE='b530d740-9d69-41c3-974a-97c06e823eb2'
DEVICE='a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10'
IO='9576fedf-9472-4ce6-b9ed-6eda5b4f0514'
ORIGIN='a6a85ff3-f6aa-4c8c-a49b-ae9f1e045ba8'
MOTOR='4bc99ae0-7ace-4891-a17a-c3fe2079278d'
OUTPUT='09c1f70b-b9ac-4e5d-884f-9779e69a597a'
META='20a6b651-4c34-401a-965e-db3e18414d5c'
OEM=next(n for n in ORIGINAL if n.endswith('.oem'))
TEXT={}
for n,b in ORIGINAL.items():
    try:TEXT[n]=b.decode('utf-8-sig')
    except UnicodeError:pass
def path(identifier):return PREFIX+identifier+'.xml'
def decode(identifier):return TEXT[path(identifier)]
def guid():return str(uuid.uuid4())
GROUPS=[{'side':s,'number':num,'station':st,'axis':axis,'axisnum':int(axis[-3:]),
         'label':s+('(左側)' if s=='A' else '(右側)')+' '+st+' 反転'+num[-1],
         'seq':f'ST4_{s}_Rev_{num}_Origin_M','done':f'ST4_{s}_Rev_{num}_OriginDone',
         'busy':f'ST4_{s}_Rev_{num}_OriginBusy',
         'param':'Homing_Para_Stm' if axis.endswith('000') else 'Homing_Para_Stm_Axis'+axis[-3:]}
    for s,num,st,axis in [('A','01','ST4','Stm_A_Rev_Axis000'),
                          ('A','02','ST6','Stm_A_Rev_Axis001'),
                          ('B','01','ST4','Stm_B_Rev_Axis002'),
                          ('B','02','ST6','Stm_B_Rev_Axis003')]]

def station_comment(comment,context=''):
    comment=comment.replace('旋回','反転')
    def inject(m):
        station='ST4' if m[1]=='1' else 'ST6'
        return m[0] if station in comment else station+' '+m[0]
    comment=re.sub(r'反転([12])(?!\d)',inject,comment)
    match=re.search(r'_Rev_(01|02)_',context)
    if match and not re.search(r'\bST[46]\b',comment):
        comment=('ST4 ' if match[1]=='01' else 'ST6 ')+comment
    for g in GROUPS:
        if g['axis'] in context and g['station'] not in comment:
            comment=g['station']+' '+comment
    return comment

# 宣言名・全参照・メモリ変数メタ情報・検証キーを同一対応で変更する。
UPDATED={n:t.replace('_Swv_','_Rev_').replace('旋回','反転') for n,t in TEXT.items()}
rename_rows={}
for n,t in TEXT.items():
    if t.startswith('[SLWD'):
        names=re.findall(r'(?m)^\+\+[^\r\n]*\tN=([^\t\r\n]+)',t)
        mapped=[x.replace('_Swv_','_Rev_') for x in names]
        # もともとの重複を除外して、新しい名前衝突が発生しないことを確認。
        assert len(set(names))==len(set(mapped)),n
        rename_rows[n]=sum('_Swv_' in x for x in names)
        lines=[]
        for line in UPDATED[n].splitlines(keepends=True):
            name=re.search(r'\tN=([^\t\r\n]+)',line)
            context=name[1] if name else ''
            line=re.sub(r'(?<=\tCom=)[^\t\r\n]*',lambda m:station_comment(m[0],context),line)
            line=re.sub(r' C="([^"]*)"',lambda m:' C="'+escape(station_comment(ET.fromstring('<e C="'+m[1]+'"/>').get('C'),context),{'"':'&quot;'})+'"',line)
            lines.append(line)
        UPDATED[n]=''.join(lines)
    elif UPDATED[n].lstrip().startswith('{'):
        def update_cmt(m):
            return '"CMT":'+json.dumps(station_comment(json.loads(m[1])),ensure_ascii=False)
        UPDATED[n]=re.sub(r'"CMT":("(?:\\.|[^"\\])*")',update_cmt,UPDATED[n])
    elif n.endswith('.xml') and UPDATED[n].lstrip().startswith('<'):
        UPDATED[n]=re.sub(r'<Variable\b[^>]*>',lambda m:re.sub(r'Comment="([^"]*)"',lambda c:'Comment='+quoteattr(station_comment(ET.fromstring('<v Comment="'+c[1]+'"/>').get('Comment'),ET.fromstring(m[0].rstrip('/>')+'/>').get('Name',''))),m[0]),UPDATED[n])

def fields(t):
    return [dict(part.split('=',1) for part in line.lstrip('+').split('\t') if '=' in part)
            for line in t.splitlines() if line.startswith('++')]
def rows(identifier):return fields(UPDATED[path(identifier)])
def rowmap(identifier):return {r['N']:r for r in rows(identifier)}
def add_decl(identifier,name,dtype,group,comment,extra=None):
    assert name not in rowmap(identifier),(identifier,name)
    parts=['++D='+dtype,'N='+name,'G='+group,'Com='+comment]
    if extra:parts.extend(k+'='+v for k,v in extra.items())
    line='\t'.join(parts)+'\r\n'
    n=path(identifier);t=UPDATED[n]
    if group=='VAR':
        marker='+GN=VAR_EXTERNAL'
        assert marker in t
        pos=t.index(marker);UPDATED[n]=t[:pos]+line+t[pos:]
    else:UPDATED[n]=t+('' if t.endswith('\n') else '\r\n')+line
def set_comment(identifier,name,comment,ec=None):
    n=path(identifier)
    pat=r'(?m)^\+\+[^\r\n]*\tN='+re.escape(name)+r'(?=\t|$)[^\r\n]*'
    def change(m):
        parts=[p for p in m[0].split('\t') if not p.startswith('Com=') and not (ec is not None and p.startswith('EC='))]
        parts.append('Com='+comment)
        if ec is not None:
            parts.append('EC=<ECs>'+''.join('<EC EK="['+str(i)+']" C='+quoteattr(c)+' />' for i,c in ec.items())+'</ECs>')
        return '\t'.join(parts)
    UPDATED[n],count=re.subn(pat,change,UPDATED[n])
    assert count==1,(identifier,name,count)

NEW_GLOBALS=[]
def global_add(name,dtype,comment,template):
    add_decl(GLOBAL,name,dtype,'VAR_GLOBAL',comment)
    NEW_GLOBALS.append((name,dtype,comment,template))
def external(identifier,name):
    globalrow=rowmap(GLOBAL)[name]
    if name not in rowmap(identifier):
        add_decl(identifier,name,globalrow['D'],'VAR_EXTERNAL',globalrow.get('Com',''),
                 {'Const':'1'} if globalrow.get('Const')=='1' else None)
    else:
        assert rowmap(identifier)[name]['D'].lower()==globalrow['D'].lower(),(identifier,name)
        set_comment(identifier,name,globalrow.get('Com',''))

original_origin=[json.loads(l) for l in UPDATED[path(ORIGIN)].splitlines() if l.strip()]
assert len(original_origin)==7
original_motor=[json.loads(l) for l in UPDATED[path(MOTOR)].splitlines() if l.strip()]
assert len(original_motor)==4 and original_motor[1]['CLs'][0]['__type']=='IST'
origin_template=copy.deepcopy(original_origin)
motor_template=copy.deepcopy(original_motor[:3])
for r in motor_template:
    for c in r['CLs']:
        if c.get('Var')=='Stm_A_Rev_Axis000_Power.Enable':
            c['Var']='Stm_A_Rev_Axis000_Power.Status'

# 自動変換する名前の対応を1組ごとに固定する。
def group_var(value,g):
    value=value.replace('ST4_A_Rev_01_Origin_M',g['seq']).replace('ST4_A_Rev_01_OriginDone',g['done'])
    value=value.replace('Stm_A_Rev_Axis000',g['axis'])
    value=re.sub(r'(Out_CYw_Rev_)01_(Pick|Chk)_A_',lambda m:m[1]+g['number']+'_'+m[2]+'_'+g['side']+'_',value)
    value=value.replace('TimerQ_In_Sen_Work_A_Pos_04','TimerQ_In_Sen_Work_'+g['side']+'_Pos_'+('04' if g['number']=='01' else '06'))
    value=value.replace('Homing_Para_Stm',g['param'])
    return value
def transform(obj,g):
    if isinstance(obj,dict):return {k:transform(v,g) for k,v in obj.items()}
    if isinstance(obj,list):return [transform(v,g) for v in obj]
    if isinstance(obj,str):return group_var(obj,g)
    return obj

def finish_rung(cells,comment,vls=None):
    index=0
    def assign(cell):
        nonlocal index
        cell['Ix']=index;index+=1
        for k in ['In','Out']:
            for c in cell.get(k,[]):assign(c)
    for cell in cells:assign(cell)
    rung={'CLs':cells,'CMT':comment,'LRI':index,'RRI':index+1,'VLs':[]}
    index+=2
    for x,y in (vls or []):
        v={'Ix':index,'X':x}
        if y:v['Y']=y
        rung['VLs'].append(v);index+=1
    return rung
def ld(name,x=0,y=0,neg=False):
    cell={'__type':'LD','Var':name,'X':x,'Y':y}
    if neg:cell['Not']=True
    return cell
def coil(name,x,y=0,reset=False):
    cell={'__type':'ST','Var':name,'X':x,'Y':y}
    if reset:cell['R']=True
    return cell
def series(contacts,target,comment):
    return finish_rung([ld(n,i,neg=neg) for i,(n,neg) in enumerate(contacts)]+[coil(target,len(contacts))],comment)

# 各組のローカル工程・保持ビットと、他POUへ渡すグローバル信号を準備。
add_decl(MODE,'Origin_StartPulse','BOOL','VAR','反転4組 原点復帰開始パルス')
for ix,g in enumerate(GROUPS):
    if ix:
        add_decl(MODE,g['seq'],'ARRAY[0..99] OF Bool','VAR',g['label']+' 原点復帰工程')
        add_decl(MODE,g['done'],'BOOL','VAR',g['label']+' 原点復帰完了')
    add_decl(MODE,g['busy'],'BOOL','VAR',g['label']+' 原点復帰中')
    motor_command=g['axis']+'_Origin'; motor_done=g['axis']+'_OriginDone';motor_busy=g['axis']+'_Busy'
    if ix:
        global_add(motor_command,'BOOL',g['label']+' モータ原点復帰開始','Stm_A_Rev_Axis000_Origin')
        global_add(motor_done,'BOOL',g['label']+' モータ原点復帰完了','Stm_A_Rev_Axis000_OriginDone')
        global_add(g['param'],'_sHOMING_REF',g['label']+' 原点復帰パラメータ','Homing_Para_Stm')
        for suffix,dtype in [('_Power','MC_Power'),('_HomeWithParameter','MC_HomeWithParameter'),('_ZeroSet','MC_SetPosition')]:
            add_decl(DEVICE,g['axis']+suffix,dtype,'VAR',g['label']+' '+{'_Power':'サーボON','_HomeWithParameter':'原点復帰命令','_ZeroSet':'原点座標設定'}[suffix])
    global_add(motor_busy,'BOOL',g['label']+' モータ動作中（原点復帰・座標設定）','Stm_A_Rev_Axis000_OriginDone')
    for name in [motor_command,motor_done]:
        external(MODE,name);external(DEVICE,name)
    for name in [g['axis'],g['param'],motor_busy]:external(DEVICE,name)
    external(IO,motor_busy)
    sensor='TimerQ_In_Sen_Work_'+g['side']+'_Pos_'+('04' if g['number']=='01' else '06')
    external(MODE,sensor)
    for mechanism,direction in [('Pick','H'),('Pick','F'),('Chk','H')]:
        stem=f"Out_CYw_Rev_{g['number']}_{mechanism}_{g['side']}_{direction}"
        array=stem+'_Origin'
        if array not in rowmap(GLOBAL):
            template=f'Out_CYw_Rev_01_{mechanism}_A_{direction}_Origin'
            dtype=rowmap(GLOBAL)[template]['D']
            comment='原点復帰 '+rowmap(GLOBAL)[stem]['Com']
            global_add(array,dtype,comment,template)
        for name in [array,stem+'_Done']:external(MODE,name);external(IO,name)
    comments={1:g['label']+' 原点復帰開始',2:g['label']+' 原点復帰受付',
              3:g['label']+' ピックアップ戻',4:g['label']+' モータ原点復帰',
              5:g['label']+' ピックアップ行',6:g['label']+' チャック閉',7:g['label']+' 原点復帰完了（ワーク無）'}
    set_comment(MODE,g['seq'],g['label']+' 原点復帰工程',comments)
    set_comment(MODE,g['done'],g['label']+' 原点復帰完了')
    for name,comment in [(motor_command,g['label']+' モータ原点復帰開始'),(motor_done,g['label']+' モータ原点復帰完了'),(g['axis'],g['label']+' 軸'+str(g['axisnum']))]:
        set_comment(GLOBAL,name,comment)
        for identifier in [MODE,DEVICE]:
            if name in rowmap(identifier):set_comment(identifier,name,comment)

for name,comment in [('Origin_Busy','反転4組 原点復帰中'),('OriginDone','反転4組 原点復帰完了')]:
    set_comment(GLOBAL,name,comment);external(MODE,name)
external(MODE,'AutoMode')
external(MODE,'Auto_A_Start')

# HMIの押下エッジを先に取り、運転条件で後段を許可する。
start_cells=[ld('HMI_Home_SW'),{'__type':'F','Name':'Up','X':1,'Id':guid(),
    'In':[{'__type':'PF','Arg':'In'}],'Out':[{'__type':'PF','Arg':''}]}]
for x,name in enumerate(['M9999','AutoMode','Auto_A_Start','Origin_Busy'],2):start_cells.append(ld(name,x,neg=True))
start_cells.append(coil('Origin_StartPulse',6))
origin_rungs=[finish_rung(start_cells,'#反転4組 共通開始（ボタン押下時・自動運転中は開始しない）')]
for g in GROUPS:
    targets=[g['seq']+'['+str(i)+']' for i in range(1,8)]+[g['done'],g['busy'],g['axis']+'_OriginDone']
    cells=[ld('Origin_StartPulse')]+[coil(name,1,y,True) for y,name in enumerate(targets)]
    origin_rungs.append(finish_rung(cells,g['label']+' 再原点復帰の工程初期化',[(1,y) for y in range(len(targets)-1)]))

for g in GROUPS:
    block=transform(copy.deepcopy(origin_template),g)
    for r in block:
        for c in r['CLs']:
            if c.get('Var')=='Origin_Busy':c['Var']=g['busy']
            if c.get('Var')=='HMI_Home_SW':c['Var']='Origin_StartPulse'
            if c.get('Var')=='Auto_A_Start':c['Var']='AutoMode'
    # 完了後に受付と個別Busyを落とす。共通Busyへの多重出力を廃止。
    block[1]=finish_rung([ld(g['seq']+'[1]'),ld(g['seq']+'[2]',0,1),
        ld('M9999',1,neg=True),ld(g['done'],2,neg=True),
        coil(g['seq']+'[2]',3),coil(g['busy'],3,1)],g['label']+' 原点復帰中',[(1,0),(3,0)])
    for i,r in enumerate(block):
        r['CMT']=('#' if i==0 else '')+g['label']+' '+[
            '原点復帰開始','原点復帰中','ピックアップ戻','モータ原点復帰開始',
            'ピックアップ行','チャック閉','原点復帰完了（ワーク無）'][i]
        if i in [2,4,5]:
            output=next(c['Var'].split('[')[0] for c in r['CLs'] if c.get('__type')=='ST' and c.get('Var','').startswith('Out_CYw_'))
            # 実在の物理出力コメントからY番号を取得する。
            physical=output.removesuffix('_Origin')
            tag=re.search(r'【Y\d+】',rowmap(GLOBAL)[physical].get('Com',''))
            if tag:r['CMT']=tag[0]+' '+r['CMT']
    origin_rungs.extend(block)
cells=[];vls=[]
for y,g in enumerate(GROUPS):
    cells.extend([ld(g['busy'],0,y),ld(g['done'],1,y,True)])
    if y<len(GROUPS)-1:vls.append((2,y))
cells.extend([ld('M9999',2,neg=True),coil('Origin_Busy',3)])
origin_rungs.append(finish_rung(cells,'反転4組 原点復帰中の集約（いずれか実行中）',vls))
origin_rungs.append(series([(g['done'],False) for g in GROUPS]+[('M9999',True)],'OriginDone','反転4組 原点復帰完了の集約（4組すべて完了）'))

def dump_rungs(rungs):return ''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in rungs)
UPDATED[path(ORIGIN)]=dump_rungs(origin_rungs)

# 軸ごとの独立したパラメータ、FBインスタンス、完了・Busy信号を作る。
motor_rungs=[];INLINE_ADDITIONS=[];ADDED={}
oemroot=ET.fromstring(UPDATED[OEM])
section=next(e for e in oemroot.iter('Entity') if e.get('id')==MOTOR)
sample_inline=next(e for e in section.iter('Entity') if e.get('type')=='Inline')
for ix,g in enumerate(GROUPS):
    block=transform(copy.deepcopy(motor_template),g)
    block[0]['CMT']='#'+g['label']+' サーボON（既存非常停止条件）'
    block[1]['CMT']=g['label']+' 原点復帰パラメータ設定'
    block[2]['CMT']=g['label']+' モータ原点復帰・座標0設定・完了保持'
    if ix:
        inline=copy.deepcopy(sample_inline);inline.tail=None
        old_id=inline.get('id');new_id=guid();new_tracking=guid()
        inline.set('id',new_id);inline.set('name',new_tracking);inline.set('trackingId',new_tracking)
        inline.set('dateCreated',NOW);inline.set('dateLastModified',NOW)
        block[1]['CLs'][0]['EID']=new_tracking
        ET.indent(inline,space='  ',level=13)
        INLINE_ADDITIONS.append('                          '+ET.tostring(inline,encoding='unicode').replace('\n','\r\n')+'\r\n')
        ADDED[PREFIX+new_id+'.BookmarkGroup']=ORIGINAL[PREFIX+old_id+'.BookmarkGroup']
    motor_rungs.extend(block)
    motor_rungs.append(finish_rung([ld(g['axis']+'_HomeWithParameter.Busy'),
        ld(g['axis']+'_ZeroSet.Busy',0,1),coil(g['axis']+'_Busy',1)],
        g['label']+' モータBusy集約（原点復帰・座標設定）',[(1,0)]))
UPDATED[path(MOTOR)]=dump_rungs(motor_rungs)

# 出力ラダーの原点復帰接点を追加。既存モード・停止・タイマ条件は維持。
out_rungs=[json.loads(l) for l in UPDATED[path(OUTPUT)].splitlines() if l.strip()]
contacts_added=[];busy_replaced=[]
for rn,r in enumerate(out_rungs):
    physical=next((c['Var'] for c in r['CLs'] if c.get('__type')=='ST' and re.fullmatch(r'Out_CYw_Rev_0[12]_(?:Pick|Chk)_[AB]_[HF]',c.get('Var',''))),None)
    if physical is None:continue
    match=re.fullmatch(r'Out_CYw_Rev_(0[12])_(Pick|Chk)_([AB])_([HF])',physical)
    num,mechanism,side,direction=match.groups()
    g=next(g for g in GROUPS if g['number']==num and g['side']==side)
    for c in r['CLs']:
        if c.get('Var') in ['Mtr_Flip_01_Busy','Mtr_Flip_02_Busy']:
            busy_replaced.append((rn,c['Var'],g['axis']+'_Busy'))
            c['Var']=g['axis']+'_Busy'
    if (mechanism,direction) not in [('Pick','H'),('Pick','F'),('Chk','H')]:continue
    target=physical+'_Origin[1]'
    if any(c.get('Var')==target for c in r['CLs']):continue
    # 自動操作枝の直下に独立した原点復帰パルス枝を追加する。
    maxix=max([r['LRI'],r['RRI']]+[c.get('Ix',0) for c in r['CLs']]+[v.get('Ix',0) for v in r['VLs']])+1
    for c in r['CLs']:
        if c.get('Y',0)>=1:c['Y']=c['Y']+1
    for v in r['VLs']:
        if v.get('Y',0)>=1:v['Y']=v['Y']+1
    new_contact=ld(target,0,1);new_contact['Ix']=maxix
    edge={'__type':'F','Name':'Up','X':1,'Y':1,'Ix':maxix+1,'Id':guid(),
          'In':[{'__type':'PF','Arg':'In'}],'Out':[{'__type':'PF','Arg':''}]}
    r['CLs'].extend([new_contact,edge,{'__type':'HL','X':2,'Y':1},{'__type':'HL','X':3,'Y':1}])
    # 既存の合流位置x=4を延長し、元の枝の意味を変えない。
    r['VLs'].append({'Ix':maxix+2,'X':4,'Y':0})
    # 既存Y=0からの線分は新しいY=1からへ移す。
    existing=[v for v in r['VLs'][:-1] if v.get('X')==4 and v.get('Y',0)==0]
    assert len(existing)==1,(rn,existing)
    existing[0]['Y']=1
    contacts_added.append((rn,target))
UPDATED[path(OUTPUT)]=dump_rungs(out_rungs)
assert len(contacts_added)==9 and len(busy_replaced)==16

# 既存外部参照にも実体の短いコメントを合わせ、空欄・表記差を解消する。
for n,t in list(UPDATED.items()):
    if not t.startswith('[SLWD') or n==path(GLOBAL):continue
    identifier=Path(n).stem
    for name,row in list(rowmap(identifier).items()):
        if row['G']=='VAR_EXTERNAL' and '_Rev_' in name and name in rowmap(GLOBAL):
            set_comment(identifier,name,rowmap(GLOBAL)[name].get('Com',''))

# グローバルのメモリ変数メタ情報を新宣言と整合させる。
meta_text=UPDATED[path(META)]
meta_root=ET.fromstring(meta_text)
meta_vars={e.get('Name'):e for e in meta_root.iter('Variable')}
meta_additions=[]
for name,dtype,comment,template in NEW_GLOBALS:
    assert name not in meta_vars
    if template not in meta_vars and dtype.upper()=='BOOL':
        template='Stm_A_Rev_Axis000_Origin'
    e=copy.deepcopy(meta_vars[template]);e.tail=None
    e.set('Name',name);e.set('Address','new_Controller_0.'+name)
    e.set('Id',guid());e.set('Comment',comment)
    meta_additions.append('    '+ET.tostring(e,encoding='unicode')+'\r\n')
assert meta_text.count('</VariableGroup>')==1
meta_text=meta_text.replace('</VariableGroup>',''.join(meta_additions)+'</VariableGroup>')
global_comments={r['N']:r.get('Com','') for r in rows(GLOBAL)}
def sync_meta(m):
    e=ET.fromstring(m[0]);name=e.get('Name')
    if name not in global_comments:return m[0]
    return re.sub(r'Comment="[^"]*"','Comment='+quoteattr(global_comments[name]),m[0])
meta_text=re.sub(r'<Variable\b[^>]*?/>',sync_meta,meta_text)
ET.fromstring(meta_text)
UPDATED[path(META)]=meta_text

# 新しいインラインSTだけをエンティティ登録。既存のID・構造は保持。
oem=UPDATED[OEM]
pos=oem.index('id="'+MOTOR+'"');close=oem.index('</ChildEntities>',pos)
oem=oem[:close]+''.join(INLINE_ADDITIONS)+oem[close:]
modified_ids=[Path(n).stem for n,t in UPDATED.items() if n in ORIGINAL and t.encode('utf-8-sig' if ORIGINAL[n].startswith(b'\xef\xbb\xbf') else 'utf-8')!=ORIGINAL[n]]
modified_ids+=['cfa8adea-9bd6-4e80-a765-2c085139e6da','0fe7f9c6-eab4-465d-bb5c-054ab06c6003','386a0c96-8f1f-4e16-af62-3e158a6366e7']
for identifier in set(modified_ids):
    pat=r'<Entity\b[^>]*\bid="'+re.escape(identifier)+r'"[^>]*>'
    oem=re.sub(pat,lambda m:re.sub(r'dateLastModified="[^"]*"','dateLastModified='+quoteattr(NOW),m[0]),oem)
ET.fromstring(oem);UPDATED[OEM]=oem

# 生成処理とは別に検証できる設計情報を保存。
design={'source':str(SOURCE),'destination':str(DEST),'sourceHash':SOURCE_HASH,'groups':GROUPS,
        'renamedDeclarations':rename_rows,'newGlobals':NEW_GLOBALS,
        'outputOriginContactsAdded':contacts_added,'outputBusyContactsReplaced':busy_replaced,
        'originRungs':len(origin_rungs),'motorRungs':len(motor_rungs),
        'paths':{'global':path(GLOBAL),'mode':path(MODE),'device':path(DEVICE),'io':path(IO),
                 'origin':path(ORIGIN),'motor':path(MOTOR),'output':path(OUTPUT),'meta':path(META),'oem':OEM}}
(BASE/'rev_origin_design_20261023.json').write_text(json.dumps(design,ensure_ascii=False,indent=2),encoding='utf-8')
payload=dict(ORIGINAL)
for n,t in UPDATED.items():
    payload[n]=t.encode('utf-8-sig' if ORIGINAL[n].startswith(b'\xef\xbb\xbf') else 'utf-8')
payload.update(ADDED)
with ZipFile(DEST,'w') as zout:
    zout.comment=ZIP_COMMENT
    for info in INFOS:zout.writestr(info,payload[info.filename])
    for n,b in ADDED.items():zout.writestr(n,b,compress_type=8)
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==SOURCE_HASH
print(json.dumps({'C版':str(DEST),'SHA256':hashlib.sha256(DEST.read_bytes()).hexdigest(),
 '変更エントリ':sum(payload[n]!=b for n,b in ORIGINAL.items()),'追加エントリ':len(ADDED),
 '新規グローバル':len(NEW_GLOBALS),'原点復帰ラダー':len(origin_rungs),'モータ制御ラダー':len(motor_rungs),
 '原点復帰接点追加':len(contacts_added),'モータBusy接点対応':len(busy_replaced)},ensure_ascii=False,indent=2))
