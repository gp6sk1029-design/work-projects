"""保存済みC版の宣言・配線と原点復帰のブール論理を独立再検証する。"""
from pathlib import Path
from zipfile import ZipFile
import collections,hashlib,json,re,sys,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')
BASE=Path(__file__).parent
D=json.loads((BASE/'rev_origin_design_20261023.json').read_text(encoding='utf-8'))
SOURCE=Path(D['source']);DEST=Path(D['destination']);P=D['paths'];G=D['groups']
with ZipFile(SOURCE) as za,ZipFile(DEST) as zb:
    assert za.testzip() is None and zb.testzip() is None
    A={n:za.read(n) for n in za.namelist()};B={n:zb.read(n) for n in zb.namelist()}
assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==D['sourceHash']
def text(data,name):return data[name].decode('utf-8-sig')
def rungs(data,name):return [json.loads(line) for line in text(data,name).splitlines() if line.strip()]
def decls(data,name):
    return {r['N']:r for r in [dict(p.split('=',1) for p in l.lstrip('+').split('\t') if '=' in p)
        for l in text(data,name).splitlines() if l.startswith('++')]}
global_vars=decls(B,P['global']);mode_vars=decls(B,P['mode']);device_vars=decls(B,P['device']);io_vars=decls(B,P['io'])
origin=rungs(B,P['origin']);motor=rungs(B,P['motor']);output=rungs(B,P['output'])
checks=[]
def check(condition,name):
    assert condition,name
    checks.append(name)
def walk(obj):
    if isinstance(obj,dict):
        yield obj
        for v in obj.values():yield from walk(v)
    elif isinstance(obj,list):
        for v in obj:yield from walk(v)
check(len(origin)==35 and len(motor)==16,'原点復帰35行・モータ16行')
for key in ['global','mode','device','io']:
    old=decls(A,P[key]);new=decls(B,P[key])
    for name,row in old.items():
        n=name.replace('_Swv_','_Rev_')
        check(n in new,key+':既存宣言保持:'+name)
        for attr,v in row.items():
            if attr in ['N','Com','EC']:continue
            check(new[n].get(attr)==v,key+':型/割付/保持/初期値保持:'+name+':'+attr)
for n,b in B.items():
    try:t=b.decode('utf-8-sig')
    except UnicodeError:continue
    check('_Swv_' not in t,'旧変数名なし:'+n)
    check('旋回' not in t,'旧コメント表記なし:'+n)
    if t.lstrip().startswith('{') and '"CLs"' in t:
        for r in rungs(B,n):
            check(isinstance(r.get('CLs'),list),'ラダーJSON構造:'+n)
    elif t.lstrip().startswith('<') and n.endswith(('.xml','.oem')):
        ET.fromstring(t)
meta=ET.fromstring(text(B,P['meta']))
meta_names=[e.get('Name') for e in meta.iter('Variable')]
check(len(meta_names)==len(set(meta_names)),'メモリ変数名の重複なし')
for name,dtype,comment,template in D['newGlobals']:
    check(name in global_vars and global_vars[name]['D']==dtype,'新規グローバル型:'+name)
    check(name in meta_names,'新規グローバルのメタ登録:'+name)
    me=next(e for e in meta.iter('Variable') if e.get('Name')==name)
    check(me.get('Comment')==comment,'新規グローバルのメタコメント:'+name)
for variables in [mode_vars,device_vars,io_vars]:
    for name,row in variables.items():
        if row['G']=='VAR_EXTERNAL' and (name in {x[0] for x in D['newGlobals']} or '_Rev_' in name):
            check(name in global_vars,'外部参照の実体:'+name)
            check(row['D'].lower()==global_vars[name]['D'].lower(),'外部参照の型:'+name)
            check(row.get('Com','')==global_vars[name].get('Com',''),'外部参照のコメント:'+name)

normal_writers=collections.Counter(c.get('Var') for r in origin for c in r['CLs'] if c.get('__type')=='ST' and not c.get('R'))
check(normal_writers['Origin_Busy']==1,'共通Busyは1か所だけ出力')
check(normal_writers['OriginDone']==1,'共通完了は1か所だけ出力')
for i,g in enumerate(G):
    for k in range(1,8):check(normal_writers[g['seq']+f'[{k}]']==1,'工程出力一意:'+g['seq']+f'[{k}]')
    check(normal_writers[g['done']]==1,'個別完了出力一意:'+g['done'])
    check(normal_writers[g['busy']]==1,'個別Busy出力一意:'+g['busy'])
    elem=ET.fromstring(mode_vars[g['seq']]['EC'])
    check({e.get('EK') for e in elem}=={f'[{k}]' for k in range(1,8)},'工程コメント1～7:'+g['seq'])
    check(all(g['station'] in e.get('C') and g['side'] in e.get('C') for e in elem),'工程コメントのST/左右:'+g['seq'])
    block=origin[5+7*i:12+7*i]
    sensor='TimerQ_In_Sen_Work_'+g['side']+'_Pos_'+('04' if g['number']=='01' else '06')
    check(any(c.get('Var')==sensor and c.get('Not') for c in block[-1]['CLs']),'ワークセンサ対応:'+g['label'])
    check(any(c.get('Var')==g['axis']+'_Origin' for c in block[3]['CLs']),'原点指令軸対応:'+g['label'])
    check(any(c.get('Var')==g['axis']+'_OriginDone' for c in block[4]['CLs']),'原点完了軸対応:'+g['label'])
    fb_names=[c.get('Var') for r in motor[i*4:(i+1)*4] for c in r['CLs'] if c.get('__type')=='FB']
    check(set(fb_names)=={g['axis']+s for s in ['_Power','_HomeWithParameter','_ZeroSet']},'独立FB3個:'+g['label'])
    for name in fb_names:
        check(name in device_vars,'FBローカル宣言:'+name)
    st=motor[i*4+1]['CLs'][0]['TXT']
    check(len(re.findall(r'^'+re.escape(g['param'])+r'\.',st,re.M))==16,'独立原点パラメータ16項目:'+g['label'])
    for r in block:
        for c in walk(r):
            if not c.get('Var'):continue
            name=re.split(r'[.\[]',c['Var'])[0]
            check(name in mode_vars,'原点復帰の全変数宣言:'+name)
    for r in motor[i*4:(i+1)*4]:
        for c in walk(r):
            v=c.get('Var','')
            if not v or '#' in v or re.fullmatch(r'(?:TRUE|FALSE)',v):continue
            check(re.split(r'[.\[]',v)[0] in device_vars,'モータ制御の全変数宣言:'+v)
for rn,name in D['outputOriginContactsAdded']:
    check(sum(c.get('Var')==name and c.get('__type')=='LD' for c in output[rn]['CLs'])==1,'原点接点追加:'+name)
    base=name.split('[')[0]
    check(base in io_vars and base in global_vars,'原点接点のグローバル/外部宣言:'+base)
for rn,old,new in D['outputBusyContactsReplaced']:
    check(sum(c.get('Var')==new and c.get('Not') for c in output[rn]['CLs'])==1,'Busy接点の軸対応:'+new)

# 原点復帰ラダーの接点・横線・縦線をグラフ化し、保存データそのものを走査する。
class Simulator:
    def __init__(self):self.state=collections.defaultdict(bool);self.edges={}
    def rung(self,r):
        cells=r['CLs'];height=max(c.get('Y',0) for c in cells)
        graph=collections.defaultdict(set)
        for v in r['VLs']:
            x=v['X'];y=v.get('Y',0);graph[(x,y)].add((x,y+1));graph[(x,y+1)].add((x,y))
        functions=[]
        for c in cells:
            x=c.get('X',0);y=c.get('Y',0);kind=c['__type']
            if kind=='HL':graph[(x,y)].add((x+1,y))
            elif kind=='LD':
                val=self.state[c['Var']]
                if c.get('Not'):val=not val
                if val:graph[(x,y)].add((x+1,y))
            elif kind=='F':
                assert c['Name']=='Up';functions.append(c)
            else:assert kind=='ST',kind
        def reachable():
            reached={(0,y) for y in range(height+1)};todo=list(reached)
            while todo:
                node=todo.pop()
                for end in graph[node]:
                    if end not in reached:reached.add(end);todo.append(end)
            return reached
        reached=reachable()
        for c in functions:
            node=(c.get('X',0),c.get('Y',0));on=node in reached
            if on and not self.edges.get(c['Id'],False):graph[node].add((node[0]+1,node[1]))
            self.edges[c['Id']]=on
        reached=reachable()
        for c in cells:
            if c['__type']!='ST':continue
            power=(c.get('X',0),c.get('Y',0)) in reached
            if c.get('R'):
                if power:self.state[c['Var']]=False
            else:self.state[c['Var']]=power
    def scan(self):
        for r in origin:self.rung(r)
    def command(self,g,m,d):return f"Out_CYw_Rev_{g['number']}_{m}_{g['side']}_{d}_Origin[1]"
    def set_done(self,g,m,d):self.state[f"Out_CYw_Rev_{g['number']}_{m}_{g['side']}_{d}_Done"]=True

sim=Simulator();sim.state['HMI_Home_SW']=True;sim.scan()
check(all(sim.state[sim.command(g,'Pick','H')] for g in G),'実ラダー論理:4組が同じ走査で開始')
check(sim.state['Origin_Busy'] and not sim.state['OriginDone'],'実ラダー論理:開始直後Busy/未完了')
sim.scan();check(not sim.state['Origin_StartPulse'],'実ラダー論理:ボタン保持で開始パルス継続しない')
for g in G:sim.set_done(g,'Pick','H')
sim.scan();check(all(sim.state[g['axis']+'_Origin'] for g in G),'実ラダー論理:各ピックアップ戻完了後に各軸を起動')
for g in G:sim.state[g['axis']+'_OriginDone']=True
sim.scan();check(all(sim.state[sim.command(g,'Pick','F')] for g in G),'実ラダー論理:各モータ完了後にピックアップ行')
for g in G:sim.set_done(g,'Pick','F')
sim.scan();check(all(sim.state[sim.command(g,'Chk','H')] for g in G),'実ラダー論理:各ピックアップ行完了後にチャック閉')
for g in G[:-1]:sim.set_done(g,'Chk','H')
sim.scan();check(not sim.state['OriginDone'] and sim.state['Origin_Busy'],'実ラダー論理:3組だけ完了しても全体完了しない')
last=G[-1];sim.set_done(last,'Chk','H');sensor='TimerQ_In_Sen_Work_B_Pos_06';sim.state[sensor]=True
sim.scan();check(not sim.state[last['done']],'実ラダー論理:ワーク有では最終完了しない')
sim.state[sensor]=False;sim.scan();check(sim.state['OriginDone'] and not sim.state['Origin_Busy'],'実ラダー論理:4組完了時だけ全体完了')
sim.scan();check(not sim.state['Origin_StartPulse'],'実ラダー論理:押し続けても完了後の自動再起動なし')
# 完了応答を次の復帰用に解除する。モータ完了保持はリセットラダーで落とす。
for g in G:
    for m,d in [('Pick','H'),('Pick','F'),('Chk','H')]:sim.state[f"Out_CYw_Rev_{g['number']}_{m}_{g['side']}_{d}_Done"]=False
sim.state['HMI_Home_SW']=False;sim.scan();sim.state['HMI_Home_SW']=True;sim.scan()
check(all(sim.state[sim.command(g,'Pick','H')] for g in G),'実ラダー論理:押し直しで4組とも再原点復帰')
check(not sim.state['OriginDone'] and all(not sim.state[g['axis']+'_OriginDone'] for g in G),'実ラダー論理:前回完了保持をリセット')
sim.state['M9999']=True;sim.scan()
check(not sim.state['Origin_Busy'] and not sim.state['OriginDone'],'実ラダー論理:既存非常停止条件で全体状態OFF')
check(all(not sim.state[sim.command(g,m,d)] for g in G for m,d in [('Pick','H'),('Pick','F'),('Chk','H')]),'実ラダー論理:既存非常停止条件で原点出力要求OFF')
sim.state['M9999']=False;sim.scan();check(not sim.state['Origin_StartPulse'],'実ラダー論理:ボタン保持のまま非常停止解除で再始動しない')
for inhibit in ['AutoMode','Auto_A_Start']:
    s=Simulator();s.state[inhibit]=True;s.state['HMI_Home_SW']=True;s.scan()
    check(not s.state['Origin_StartPulse'] and not s.state['Origin_Busy'],'実ラダー論理:運転中の開始禁止:'+inhibit)

# 追加した出力枝が手動/自動モードの接点を迂回しつつ、停止・モータBusy条件を守ること。
for rn,request in D['outputOriginContactsAdded']:
    physical=request.split('[')[0].removesuffix('_Origin')
    busy=next(new for r,old,new in D['outputBusyContactsReplaced'] if r==rn)
    s=Simulator();s.state[request]=True;s.rung(output[rn])
    check(s.state[physical],'出力ラダー論理:原点復帰枝で実出力要求:'+physical)
    for stop in ['M9999',busy,'Pause[1]']:
        s=Simulator();s.state[request]=True;s.state[stop]=True;s.rung(output[rn])
        check(not s.state[physical],'出力ラダー論理:停止/Busy条件保持:'+physical+':'+stop)

changed=[n for n in A if A[n]!=B[n]];added=[n for n in B if n not in A]
check(all(A[n]==B[n] for n in A if n.endswith('.dat')),'機器/軸/通信datは全件不変')
check(all(A[n]==B[n] for n in A if n.endswith('.stsdb4')),'埋込DBは原本保持')
result={'検証日':'2026-10-23','原本':str(SOURCE),'出力':str(DEST),'検証項目数':len(checks),
    '原本SHA256':D['sourceHash'],'出力SHA256':hashlib.sha256(DEST.read_bytes()).hexdigest(),
    '変更エントリ':changed,'追加エントリ':added,'不変エントリ数':len(A)-len(changed),
    'シミュレーション':'保存ラダーのブール論理走査。MC命令・実機・Sysmacシミュレータではない。',
    'Sysmac読込/再ビルド':'未実施','PLC接続/転送':'なし','検証一覧':checks}
(BASE/'rev_origin_verification_20261023.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['検証一覧','変更エントリ','追加エントリ']},ensure_ascii=False,indent=2))
