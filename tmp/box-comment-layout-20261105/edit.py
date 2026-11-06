"""G版の今回編集箇所について、行間コメントだけを読みやすく整える。"""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from copy import copy,deepcopy
import json,hashlib,io,re,unicodedata

b=Path(__file__).parent
prior=json.loads((b.parent/'box-cycle-implement-20261105/verification.json').read_text(encoding='utf-8'))
src=Path(prior['output']);raw=src.read_bytes();sha=hashlib.sha256(raw).hexdigest()
sections={}
with ZipFile(io.BytesIO(raw)) as z:
    for n in z.namelist():
        if not n.endswith('.oem'):continue
        for e in E.fromstring(z.read(n)).iter():
            if e.get('type')!='PouBody':continue
            part=n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml'
            t=z.read(part).decode('utf-8-sig')
            if t.lstrip().startswith('{"CLs"'):
                sections[e.get('name')]={'part':part,'lines':t.splitlines(keepends=True),'rows':[json.loads(l) for l in t.splitlines()]}
box=sections['BoxPacking_箱詰め'];rcon=sections['RCON_IAI'];sf=sections['ST7_A_Dis2_左SF排出']
assert len(box['rows'])==45 and len(rcon['rows'])==457 and len(sf['rows'])==32,'最新ファイルの行構成を再確認してください'
dest=src.with_name(src.name.replace('20261105G.smc2','20261105H.smc2'))
assert dest!=src and not dest.exists()
changes=[]

def width(text):return sum(2 if unicodedata.east_asian_width(c) in 'FWA' else 1 for c in text)

def wrap(text,limit=46):
    # 変数名・行番号は分割せず、日本語の句読点と文字の境界で折り返す。
    tokens=re.findall(r'[A-Za-z0-9_\[\].]+|[^A-Za-z0-9_\[\].]',text)
    out=[];line=''
    for token in tokens:
        if line and width(line+token)>limit:
            out.append(line.rstrip());line=''
        line+=token
    if line:out.append(line.rstrip())
    return out

def format_existing(text):
    out=[]
    for line in text.replace('\r\n','\n').splitlines():
        if not line.strip():continue
        line=line.strip()
        # 1つの行にある分岐・軸を、それぞれ独立した行へ。
        parts=line.split('／')
        for part in parts:
            part=part.strip()
            m=re.match(r'^(#?【[^】]+】)(.*)$',part)
            if m:
                if out and out[-1]!='':out.append('')
                out.append(m[1])
                if m[2]:out.extend(wrap(m[2]))
                if m[1].startswith('#'):out.append('')
            else:out.extend(wrap(part))
    return '\r\n'.join(out).strip()

def set_comment(name,index,text):
    s=sections[name];old=s['rows'][index].get('CMT','');new=text.replace('\r\n','\n').strip().replace('\n','\r\n')
    if old!=new:
        s['rows'][index]['CMT']=new
        changes.append({'section':name,'row':index,'before':old,'after':new})

boxname='BoxPacking_箱詰め'
for i,r in enumerate(box['rows']):set_comment(boxname,i,format_existing(r.get('CMT','')))

# 複雑な分岐・合流は、1経路につき1行にし、信号情報と分離する。
custom={
0:'''#【01 初回コンテナ確認】

【開始条件】
・初回確認が未完了
・初回処理中でない

M[1]の自己保持は上記条件を迂回''',
1:'''【初回確認完了】
取出し先判定へ受渡したら、M[2]を保持

通常運転中は初回確認へ戻らない''',
2:'''【初回確認中】
開始から初回確認完了まで保持

M[2]成立で解除''',
3:'''【初回：コンテナ状態判定】
RCON2_5：コンテナ設置・排出軸

① 受渡位置＋到着 → 4行：排出戻
② 設置位置       →15行：取出し先判定
③ 排出位置       → 8行：初回排出
④ 位置未確定     →10行：設置準備

X1003：コンテナ到着
※ 受渡位置[1]の判定に使用''',
6:'''【初回：トレイ方向判定】
X1007：コンテナトレイ方向

方向OK →15行：取出し先判定
方向NGが10秒継続 →7行：排出位置へ''',
8:'''【初回：コンテナ排出】
Y1205：コンテナ排出行

合流元
・3行：排出位置にある
・7行：方向NGの排出移動完了''',
10:'''#【02 コンテナ設置】

【受渡位置へ移動】
RCON2_5：コンテナ設置・排出軸
位置設定[1]：受渡位置

合流元
・3行：軸位置未確定
・9行：初回排出完了
・44行：満杯排出完了

44行からは、X1010のOFFで復帰
X1010：空コンテナ送り戻確認''',
11:'''【受渡位置・コンテナ到着確認】
RCON2_5：コンテナ設置・排出軸
位置設定[1]：受渡位置
X1003：コンテナ到着

確認後、Y1204：コンテナ排出戻''',
15:'''#【03 ワーク取出し】

【取出し先の選択】
ST7の取出し待ちを確認し、A側を優先
Busy成立まで、判定・選択を保持

合流元
・3／6／14行：コンテナ準備完了
・39行：80個未満で繰返し

A側選択 →16行：A側Busy
B側選択 →17行：B側Busy''',
16:'''【A側：取出し・箱内配置中】
選択を受けて、Busyを自己保持
成立時にBox_Total_CTへ5個加算

解除条件
・39行：次の取出しへ継続
・44行：満杯排出完了''',
19:'''【A側：取出し位置へ移動】
RCON2_2：箱詰めX軸
RCON2_3：箱詰めY軸
位置設定[1]：A側取出し位置

X移動完了 →20行
Y移動完了 →21行
両軸の合流 →22行''',
22:'''【A側：XY移動完了の合流】
20行：X軸完了 ＋21行：Y軸完了

両軸完了 →27行：取出し下降''',
23:'''【B側：取出し位置へ移動】
RCON2_2：箱詰めX軸
RCON2_3：箱詰めY軸
位置設定[2]：B側取出し位置

X移動完了 →24行
Y移動完了 →25行
両軸の合流 →26行''',
26:'''【B側：XY移動完了の合流】
24行：X軸完了 ＋25行：Y軸完了

両軸完了 →27行：取出し下降''',
27:'''【取出し下降：A・B合流】
合流元：22行（A側）／26行（B側）

RCON2_4：箱詰めZ軸
位置設定[2]：取出し下降位置''',
30:'''【A側：取出し・退避完了】
チャック後、箱詰めZ軸の上昇完了を確認
RCON2_4：箱詰めZ軸

→ ST7 A側の取出し待ちを解除''',
31:'''#【04 箱内配置】

【箱内X位置の選択・移動】
RCON2_2：箱詰めX軸
位置設定[3]：箱内X開始位置

目標＝開始位置＋ピッチ×列番号
ピッチ：HMI_Box_X_Pitch_mm
列番号：0～3''',
32:'''【箱内Y位置の選択・移動】
RCON2_3：箱詰めY軸
位置設定[3]：箱内Y開始位置

目標＝開始位置＋ピッチ×行番号
ピッチ：HMI_Box_Y_Pitch_mm
行番号：0～3''',
35:'''【箱内：XY移動完了の合流】
33行：X軸完了 ＋34行：Y軸完了

両軸完了 →36行：箱内下降''',
39:'''#【05 入数判定・満杯排出】

【箱詰めZ軸の上昇完了後に判定】
RCON2_4：箱詰めZ軸

80個未満 →15行：次の取出し選択
80個     →40行：満杯コンテナ排出''',
44:'''【満杯排出・軸戻り完了】
RCON2_5：コンテナ設置・排出軸

完了立上りでBox_Total_CTを0へ

→10行：次のコンテナ設置
  X1010：空コンテナ送り戻確認のOFFで復帰'''
}
for i,text in custom.items():set_comment(boxname,i,text)

# G作成時に編集したRCON行だけを対象とする。残りの既存コメントは保持。
with ZipFile(prior['backup']) as f:
    old=[json.loads(l) for l in f.read(prior['rcon_part']).decode('utf-8-sig').splitlines()]
with ZipFile(prior['staged']) as g:
    previous=[json.loads(l) for l in g.read(prior['rcon_part']).decode('utf-8-sig').splitlines()]
mapping={int(k):v for k,v in prior['rcon_old_to_new_rows'].items()}
targets=set(range(457))-set(mapping.values())
targets.update(new for prev,new in mapping.items() if old[prev].get('CMT','')!=previous[new].get('CMT',''))
for i in sorted(targets):set_comment('RCON_IAI',i,format_existing(rcon['rows'][i].get('CMT','')))
for axis,base in [(2,283),(3,323),(4,363),(5,403)]:
    name={2:'箱詰めX軸',3:'箱詰めY軸',4:'箱詰めZ軸',5:'コンテナ設置・排出軸'}[axis]
    head=f'RCON2_{axis}：{name}'
    set_comment('RCON_IAI',mapping[base]-1,f'''#【{head}】

【自動開始許可】
通信確認・軸許可・準備完了で許可

非常停止・一時停止・リセット中は不許可''')
    set_comment('RCON_IAI',mapping[base+5],f'''【移動開始】
{head}

既存Up＋TOFで100ms保持
開始許可OFFで内部Startを解除''')
    count={2:3,3:3,4:5,5:6}[axis]
    set_comment('RCON_IAI',mapping[base+38],f'''【自動要求の受付・開始保持】
{head}
要求[1]～[{count}]を並列で受付

前回完了の100ms保持中は待機
完了解除後、既存TONで確認''')
    set_comment('RCON_IAI',mapping[base+38]+1,f'''【今回移動の受付確認】
{head}

開始保持中にPEND OFFを記憶
開始保持解除で、受付確認も解除''')
    set_comment('RCON_IAI',mapping[base+39],f'''【移動完了】
{head}

今回受付済み ＋ PEND ONで完了
既存TONで100ms保持''')
set_comment('ST7_A_Dis2_左SF排出',31,'''【A側：取出し待ち】
ストックフォルダ回転完了後に保持

箱詰めA側の取出し・Z上昇完了で解除
→ 次のストックフォルダ回転準備''')

# 全行で、コメント以外が完全一致することを確認する。
patches={};audit=[]
with ZipFile(io.BytesIO(raw)) as z:
    for name in [boxname,'RCON_IAI','ST7_A_Dis2_左SF排出']:
        s=sections[name];original=[json.loads(l) for l in s['lines']];changed=[];newlines=[]
        for i,(a,c,line) in enumerate(zip(original,s['rows'],s['lines'])):
            aa=deepcopy(a);cc=deepcopy(c);aa.pop('CMT',None);cc.pop('CMT',None);assert aa==cc
            if a!=c:
                changed.append(i)
                ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
                newlines.append(json.dumps(c,ensure_ascii=False,separators=(',',':'))+ending)
            else:newlines.append(line)
        if changed:
            originalraw=z.read(s['part']);patches[s['part']]=(b'\xef\xbb\xbf' if originalraw.startswith(b'\xef\xbb\xbf') else b'')+''.join(newlines).encode('utf-8')
        audit.append({'section':name,'changed_rows':changed,'count':len(changed),'row_count':len(s['rows']),'part':s['part']})
    stream=io.BytesIO()
    with ZipFile(stream,'w') as w:
        w.comment=z.comment
        for info in z.infolist():w.writestr(copy(info),patches.get(info.filename,z.read(info.filename)))
    data=stream.getvalue()
    with ZipFile(io.BytesIO(data)) as w:
        assert w.testzip() is None and w.namelist()==z.namelist()
        assert set(n for n in z.namelist() if z.read(n)!=w.read(n))==set(patches)
stage=b/dest.name;stage.write_bytes(data)
report={'source':str(src),'source_sha256':sha,'previous_G_sha256':prior['output_sha256'],'source_updated_since_previous':sha!=prior['output_sha256'],
    'staged':str(stage),'output':str(dest),'output_sha256':hashlib.sha256(data).hexdigest(),'comment_only':True,
    'sections':audit,'changed_comment_rows':sum(x['count'] for x in audit),'changed_parts':list(patches),'unchanged_parts':212-len(patches),'published':False}
(b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/box-comment-layout-20261105');out.mkdir(parents=True,exist_ok=True)
listing='\n\n'.join('【'+name+'】\n'+'\n\n'.join(str(i)+'行\n'+r.get('CMT','') for i,r in enumerate(sections[name]['rows']) if i in next(a['changed_rows'] for a in audit if a['section']==name)) for name in [boxname,'RCON_IAI','ST7_A_Dis2_左SF排出'])
(out/'H版_行間コメント一覧.txt').write_text(listing.replace('\r\n','\n'),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False))
