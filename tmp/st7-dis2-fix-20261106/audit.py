"""候補の変更範囲・宣言・受け先・元不変・異常時を照合する。"""
from pathlib import Path,PurePosixPath
from collections import Counter,defaultdict
from itertools import product
import json,sys,copy,runpy,contextlib,io
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;m=json.loads((b/'build.json').read_text(encoding='utf-8'));p=sm.Project(m['stage']);original=sm.Project(m['backup']);current=sm.Project(m['source_internal'])
assert current.fingerprint==m['internal_sha']
allowed={'ST7_A_Dis2_左SF排出','RCON_IAI','Error_エラー処理'}
diff=[]
for s,t in sm.align(original,p):
    if s['name'] not in allowed:assert s['rows']==t['rows'],s['name']
    else:diff.append({'section':s['name'],'old_rows':len(s['rows']),'new_rows':len(t['rows'])})
mp={int(k):v for k,v in m['old_to_new_rows'].items()};rm={int(k):v for k,v in m['rcon_old_to_new_rows'].items()};rows=p.section('ST7_A_Dis2_左SF排出')['rows'];rc=p.section('RCON_IAI')['rows']
def stripmeta(r):return [{k:v for k,v in c.items() if k!='Ix'} for c in r['CLs']],[{k:v for k,v in c.items() if k!='Ix'} for c in r['VLs']]
assert stripmeta(rows[mp[16]])==stripmeta(m['old_user_row16']),'ユーザー修正済み16行は結線・条件を完全維持する'
M=lambda n:f'ST7_A_Dis2_M[{n}]'
normal=defaultdict(list);contacts=defaultdict(list)
for s in p.sections:
    for i,r in enumerate(s['rows']):
        for c in r['CLs']:
            if c['__type']=='ST' and not c.get('S') and not c.get('RS'):normal[c['Var']].append([s['name'],i])
            if c['__type']=='LD':contacts[c['Var']].append([s['name'],i])
requests={c['Var'] for r in rows for c in r['CLs'] if c['__type']=='ST' and '_Auto[' in c.get('Var','')}
for tag in requests:assert len(normal[tag])==1 and contacts[tag],(tag,normal[tag],contacts[tag])
assert not any(c.get('Var','').startswith(('TimerQ_In_Sen_SH_B_','TimerQ_In_Sen_NG2_Tray_B_')) for r in rows for c in r['CLs'])
for axis,start,finish in [(3,120,121),(5,201,202)]:
    assert not any(f'RCON1_{axis}_M[2]' in json.dumps(s['rows']) for s in original.sections),'使用済みの補助番号を上書きしない'
# 物理実行のP_Offや設定値転送など、修正した受付4行以外は全て保存時のまま。
oldrc=original.section('RCON_IAI')['rows']
for i,r in enumerate(oldrc):
    if i not in [120,121,201,202]:assert r==rc[rm[i]],i
oldvars=original.declarations();newvars=p.declarations();added=[]
for part,decls in oldvars.items():
    a={d['N']:d for d in decls};z={d['N']:d for d in newvars[part]}
    assert set(a)<=set(z)
    for name,decl in a.items():assert decl==z[name],(part,name)
    for name in set(z)-set(a):added.append({'table':part,'declaration':z[name]})
assert {x['declaration']['N'] for x in added}==set(m['new_local_and_external'])
for x in added:
    decl=x['declaration']
    if decl['G']=='VAR':assert decl['D']=='TON' and decl['R']=='0' and decl['Const']=='0' and decl['RO']=='0'
    else:assert decl['G']=='VAR_EXTERNAL' and decl['D']=='BOOL'
# 新しいmain外部参照が全てglobalの同型へつながる。
main=next(v for k,v in newvars.items() if k=='86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml');glob={v['N']:v for vv in newvars.values() for v in vv if v.get('G')=='VAR_GLOBAL'}
for x in added:
    decl=x['declaration']
    if decl['G']=='VAR_EXTERNAL':assert decl['N'] in glob and glob[decl['N']]['D'].lower()==decl['D'].lower()
with contextlib.redirect_stdout(io.StringIO()):ns=runpy.run_path(str(b/'test_conditions.py'))
Model=ns['Model'];find=lambda text:next(r for r in rows if r.get('CMT','').startswith(text))
# 起動直後のRetry NC立上りだけでは、初期位置前にM8/Endが立たない。
for work in [False,True]:
    a=Model({'Auto_A_Start':True,'Station_A_Data[7].Work_On':work,'TimerQ_In_Sen_Work_A_Pos_07':work,'HMI_A_SF_StackPitch_mm':-10.,'Station_A_Data[7].Total_Judge':1})
    for i,r in enumerate(rows):a.row(r,str(i))
    assert not a.e[M(8)] and not a.e['ST7_A_Dis2_End']
# 端位置4組、5個満杯と取出し側空き。正常時のみ回転開始。
turn_cases=[]
for h,f in product([False,True],repeat=2):
    a=Model({'Auto_A_Start':True,'TimerQ_In_Sen_SH_A_Ent':True,'RCON1_5_ActualPos_mm':0.,'RCON1_5_SafePos_mm':10.,'TimerQ_In_SenCY_SH_A_Turn_H':h,'TimerQ_In_SenCY_SH_A_Turn_F':f})
    for text in ['【回転端位置の確認】','【フォルダ回転の時間監視】','【回転異常の保持】']:a.row(find(text),text)
    a.row(rows[mp[27]],'start');assert a.e['ST7_A_SF_M[1]']==(h!=f);assert bool(a.e[M(44)])==(h==f)
    turn_cases.append({'H':h,'F':f,'start':a.e['ST7_A_SF_M[1]'],'error':a.e[M(44)]})
a=Model({'ST7_A_SF_Busy':True})
for i in range(1001):a.row(find('【フォルダ回転の時間監視】'),'watch')
a.row(find('【回転異常の保持】'),'error');assert a.e[M(44)]
# 設定異常とResetでの保持解除。原因が残ったまま許可しない。
for count,pitch in [(-1,-10.),(6,-10.),(0,0.)]:
    a=Model({M(8):True,M(9):True,'Station_A_Data[7].Total_Judge':1,'A_SF_CT':count,'HMI_A_SF_StackPitch_mm':pitch})
    a.row(find('【設定・判定異常】'),'config');a.row(find('【取出し開始の許可】'),'permit');assert a.e[M(43)] and not a.e[M(45)]
    a.e['In_Sw_RESET']=True;a.row(find('【ST7異常の解除】'),'reset');assert not a.e[M(43)]
conditions=json.loads((b/'conditions.json').read_text(encoding='utf-8'));flow=json.loads((b/'flow.json').read_text(encoding='utf-8'));native=json.loads((b/'native.json').read_text(encoding='utf-8-sig'))
assert all(x['candidate_sha']==p.fingerprint for x in [conditions,flow]) and native['sha256']==p.fingerprint and native['verified']
r={'candidate':str(p.path),'sha256':p.fingerprint,'sections':diff,'other_22_sections_identical':True,'user_modified_row16_preserved':True,'request_writers_and_receivers_verified':len(requests),'B_side_sensor_references_in_ST7':0,'existing_variable_declarations_unchanged':True,'added_declarations':added,'RCON_physical_output_and_other_rows_unchanged':True,'source_J_unchanged':True,'turn_endpoint_cases':turn_cases,'rotation_timeout_10s_test':True,'invalid_pitch_count_reset_tests':3,'initialization_gate_cases':2,'local_conditions':conditions,'flow':{'runs':len(flow['runs']),'items_per_run':15,'scope':flow['scope']},'native':{k:native[k] for k in ['rows','coils','parse_fail','model_fail','missing_connections','verified']},'full_application_build':False,'machine_test':False}
sm.save_json(b/'audit.json',r)
print(json.dumps({k:v for k,v in r.items() if k not in ['local_conditions','added_declarations','turn_endpoint_cases']},ensure_ascii=False,indent=2))
print('MANIFESTS',[(k,v[:260].decode('utf-8-sig','replace')) for k,v in p.entries.items() if '.manifest' in k])
