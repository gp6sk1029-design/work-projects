"""段バラシの合意範囲だけを修正した候補とstage計画を作る。"""
from pathlib import Path,PurePosixPath
from copy import deepcopy
import sys,json,re,uuid
from xml.etree import ElementTree as E
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
inside=sm.Project(d['internal']);external=sm.Project(d['external'])
assert inside.fingerprint==d['internal_sha'] and external.fingerprint==d['external_sha']
source=next(s for s in d['sections'] if s['name']=='Destacker_段バラシ');old=deepcopy(source['rows']);r=deepcopy(old)
M=lambda n:f'Destacker_M[{n}]'
busy='Destacker_Init_Busy';done='RCON2_1_MoveDone'
def ld(v,x=0,y=0,nc=False):
    c={'__type':'LD','Var':v}
    if x:c['X']=x
    if y:c['Y']=y
    if nc:c['Not']=True
    return c
def st(v,x,y=0):
    c={'__type':'ST','Var':v,'X':x}
    if y:c['Y']=y
    return c
def hl(x,y):return {'__type':'HL','X':x,'Y':y}
def row(cs,vs,cmt):return sm.reindex({'CLs':cs,'VLs':vs,'CMT':cmt.replace('\n','\r\n')})
def insert_branch_column(rr,x,contact,bypass_ys):
    for c in rr['CLs']:
        if c.get('X',0)>=x:c['X']=c.get('X',0)+1
    for v in rr['VLs']:
        if v.get('X',0)>=x:v['X']+=1
    rr['CLs'].append(contact)
    rr['CLs'].extend(hl(x,y) for y in bypass_ys)
    sm.reindex(rr)
def common_column(rr,x,contact):
    for c in rr['CLs']:
        if c.get('X',0)>=x:c['X']=c.get('X',0)+1
    for v in rr['VLs']:
        if v.get('X',0)>x:v['X']+=1
    rr['CLs'].append(contact);sm.reindex(rr)

# 初回開始のBusyは開始枝だけ。完了M26は開始・初回状態判定を共通で解除する。
insert_branch_column(r[0],1,ld(busy,1,nc=True),[1])
common_column(r[0],3,ld(M(26),3,nc=True))
common_column(r[1],2,ld(M(26),2,nc=True))
common_column(r[2],2,ld(M(26),2,nc=True))
r[0]['CMT']='#【01 初回確認】\r\n初回未完了・処理中でなければ開始'
r[1]['CMT']='【初回の爪保持】\r\n【Y1203】：段バラシ爪 行\r\n初回確認済みでは動作しない'
r[2]['CMT']='【初回の位置判定】\r\nRCON2_1：段バラシ軸\r\n安全位置にいるか判定'

# 11行の誤った完了接点が残っている場合だけ訂正。今回はユーザー修正済み。
corrected_done=0
for c in r[11]['CLs']:
    if c.get('Var')=='Out_CYw_Sep_Claw_H_Done':c['Var']='Out_CYw_Empty_Container_CY_H_Done';corrected_done+=1
assert any(c.get('Var')=='Out_CYw_Empty_Container_CY_H_Done' for c in r[11]['CLs'])
assert r[12]['CLs'][0]['Var']==M(15)

# 各移動工程で、古いDoneのOFFを見てから次のONを認める。
spec=[(7,27,5,'初回 安全位置'),(8,28,6,'初回 1段目'),(10,29,8,'初回 安全戻り'),(16,30,13,'通常 1段目'),(21,31,16,'通常 2段目'),(23,32,18,'排出位置')]
guards={}
for step,guard,target,label in spec:
    assert any(c['__type']=='LD' and c.get('Var')==done for c in r[target]['CLs'])
    insert_branch_column(r[target],1,ld(M(guard),1),[1,2] if target==8 else [1])
    guards[target]=row([ld(M(step)),ld(done,1,nc=True),ld(M(guard),1,1),st(M(guard),2)],
        [{'X':1},{'X':2}],f'【{label} 完了待ちの準備】\n今回工程でDone OFFを確認して保持\n工程終了で解除')
    r[target]['CMT']=(r[target].get('CMT','')+'\r\n今回工程のDone OFF確認後、完了ONを待つ').strip()

initial_busy=row([ld(M(1)),ld(busy,y=1),ld(M(26),1,nc=True),st(busy,2)],
    [{'X':1}],'【初回処理中】\n開始から初回確認済みまで保持')
initial_done=row([ld(M(11)),ld(M(12),1),ld('Out_CYw_Empty_Container_CY_H_Done',2),ld(M(26),y=1),hl(1,1),hl(2,1),st(M(26),3)],
    [{'X':3}],'【初回確認済み】\n初回側から通常入口への受渡しで保持\n通常サイクルでは解除しない')
rows=[];mapping={};guard_indices={}
for i,rr in enumerate(r):
    if i in guards:guard_indices[i]=len(rows);rows.append(guards[i])
    mapping[i]=len(rows);rows.append(rr)
    if i==0:busy_index=len(rows);rows.append(initial_busy)
    if i==9:done_index=len(rows);rows.append(initial_done)
assert len(rows)==29

ops=[]
def replace(part,data,label):
    fn=b/(label+'.bin');fn.write_bytes(data)
    ops.append({'op':'replace-part','part':part,'expected_sha256':sm.sha(external.entries[part]),'file':str(fn.resolve())})
target=external.section('Destacker_段バラシ')
raw=inside.entries[source['part']];newline='\r\n' if b'\r\n' in raw else '\n'
payload=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+(newline.join(json.dumps(v,ensure_ascii=False,separators=(',',':')) for v in rows)+newline).encode('utf-8')
replace(target['part'],payload,'destacker')

# 既存表を維持してローカルBusyのみ追加。M26～32は既存配列要素のコメントを追記。
comments={26:'初回確認済み',27:'初回安全位置 前完了解除確認',28:'初回1段目 前完了解除確認',29:'初回安全戻り 前完了解除確認',30:'1段目 前完了解除確認',31:'2段目 前完了解除確認',32:'排出位置 前完了解除確認'}
var_changes=[]
for internal_part,txt in inside.variable_parts.items():
    changed=False;lines=[]
    for line in txt.splitlines():
        if line.startswith('++D='):
            fs=dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p)
            if fs.get('N')=='Destacker_M':
                assert fs['D'].lower()=='array[0..99] of bool'
                assert fs.get('R','0')=='0','既存配列が保持設定のため、初回済みの起動仕様を再検討する必要があります'
                ec=E.fromstring(fs.get('EC','<ECs/>'))
                for n,comment in comments.items():
                    assert not any(x.get('EK')==f'[{n}]' for x in ec)
                    E.SubElement(ec,'EC',{'EK':f'[{n}]','C':comment})
                newec=E.tostring(ec,encoding='unicode',short_empty_elements=True)
                if '\tEC=' in line:line=re.sub(r'\tEC=[^\t\r\n]*','\tEC='+newec,line)
                else:line+='\tEC='+newec
                changed=True
        lines.append(line)
    newtxt='\r\n'.join(lines)+'\r\n'
    if internal_part=='86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml':
        assert '+GN=VAR_EXTERNAL' in newtxt and busy not in newtxt
        newtxt=newtxt.replace('+GN=VAR_EXTERNAL','++D=BOOL\tN='+busy+'\tG=VAR\tR=0\tConst=0\tRO=0\tCom=段バラシ初回処理中\r\n+GN=VAR_EXTERNAL',1);changed=True
    if changed:
        hits=[part for part in external.variable_parts if PurePosixPath(part).name==PurePosixPath(internal_part).name];assert len(hits)==1
        target_part=hits[0];orig=external.entries[target_part]
        data=(b'\xef\xbb\xbf' if orig.startswith(b'\xef\xbb\xbf') else b'')+newtxt.encode('utf-8')
        replace(target_part,data,'vars_'+PurePosixPath(internal_part).stem);var_changes.append(target_part)

# 受け渡しファイルの名前と表示名をI版へ揃える。制御とは別の1属性だけ。
newname='3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105I'
for part,data in external.entries.items():
    if part.endswith('.oem'):
        text=data.decode('utf-8-sig');match=re.search(r'<Entity\b[^>]*\btype="Solution"[^>]*>',text);assert match
        original=match.group(0);updated=re.sub(r'\bname="[^"]*"','name="'+newname+'"',original,count=1)
        assert updated!=original
        text=text[:match.start()]+updated+text[match.end():]
        replace(part,(b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8'),'oem_name')
plan={'source_sha256':external.fingerprint,'operations':ops};sm.save_json(b/'plan.json',plan)
meta={'source_external':str(external.path),'external_sha':external.fingerprint,'internal':str(inside.path),'internal_sha':inside.fingerprint,'source_user_rows':old,'old_to_new':mapping,'guard_rows':guard_indices,'spec':spec,'busy_row':busy_index,'done_row':done_index,'corrected_done_contacts':corrected_done,'variable_parts':var_changes,'solution_name':newname,'target':str(external.path.with_name(newname+'.smc2')),'row_count':len(rows)}
sm.save_json(b/'build.json',meta)
assert inside.current_fingerprint()==inside.fingerprint and external.current_fingerprint()==external.fingerprint
print(json.dumps({k:v for k,v in meta.items() if k!='source_user_rows'},ensure_ascii=False))
