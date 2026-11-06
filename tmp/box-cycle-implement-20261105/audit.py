"""生成処理とは別に、変更範囲・連番・変数・既存STを検査する。"""
from pathlib import Path
from zipfile import ZipFile
from lxml import etree as E
from copy import deepcopy
from collections import Counter
import json,re
b=Path(__file__).parent;m=json.loads((b/'verification.json').read_text(encoding='utf-8'))
def rows(z,p):return [json.loads(l) for l in z.read(p).decode('utf-8-sig').splitlines()]
def fields(t):return {dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)['N']:dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in t.splitlines() if l.startswith('++D=')}
with ZipFile(b/'source.smc2') as old,ZipFile(m['staged']) as new:
    assert new.testzip() is None and old.namelist()==new.namelist()
    diff=[n for n in old.namelist() if old.read(n)!=new.read(n)]
    assert set(diff)==set(m['changed_parts']) and len(diff)==6
    a,c=rows(old,m['box_part']),rows(new,m['box_part'])
    mapping={int(k):v for k,v in m['old_to_new_rows'].items()}
    assert len(a)==42 and len(c)==45
    # 既存STは本文・大きさ・識別子・座標をそのまま保持する。
    for i,r in enumerate(a):
        for st in [x for x in r['CLs'] if x['__type']=='IST']:
            actual=next(x for x in c[mapping[i]]['CLs'] if x['__type']=='IST' and x['EID']==st['EID'])
            assert actual==st
    coils=Counter(x['Var'] for r in c for x in r['CLs'] if x['__type']=='ST' and x.get('Var','').startswith('BoxPacking_M['))
    assert coils==Counter({f'BoxPacking_M[{n}]':1 for n in range(1,50)}),coils
    # B側既存工程は共通M改番とコメントだけ。独自の動作は追加しない。
    for i in [15,21,22,23,24]:
        expected=deepcopy(a[i])
        for x in expected['CLs']:
            tag=x.get('Var','');match=re.fullmatch(r'BoxPacking_M\[(\d+)\]',tag)
            if match and int(match[1])>=2:x['Var']=f'BoxPacking_M[{int(match[1])+1}]'
        expected['CMT']=c[mapping[i]].get('CMT','')
        assert expected==c[mapping[i]],i
    # 初回状態分岐は全M改番・共通完了NCの追加のみ。X1003を設置・排出枝へ追加しない。
    init=c[mapping[1]]
    sensor=[x for x in init['CLs'] if x.get('Var')=='TimerQ_In_Sen_Container_Arrival']
    assert len(sensor)==1 and sensor[0].get('Y')==1
    assert c[mapping[36]]['CLs'][1]['Var']=='RCON2_4_MoveDone' and not c[mapping[36]]['CLs'][1].get('Not')
    assert c[mapping[32]]['CLs'][0]['Var']=='BoxPacking_M[36]'
    assert any(x.get('Var')=='BoxPacking_M[2]' and x.get('Not') for x in c[mapping[4]]['CLs'])
    r13=c[mapping[13]]
    for x,name in [(3,'BoxPacking_A_Busy'),(4,'BoxPacking_B_Busy')]:
        cs=[v for v in r13['CLs'] if v.get('X',0)==x and v.get('Y',0)==0]
        assert len(cs)==1 and cs[0]['Var']==name and cs[0].get('Not')
    for key in ['RCON2_2_Auto','RCON2_3_Auto','RCON2_4_Auto','RCON2_5_Auto']:
        before=[x['Var'] for r in a for x in r['CLs'] if x['__type']=='ST' and x.get('Var','').startswith(key+'[')]
        after=[x['Var'] for r in c for x in r['CLs'] if x['__type']=='ST' and x.get('Var','').startswith(key+'[')]
        assert before==after
    sa,sc=rows(old,m['sf_part']),rows(new,m['sf_part'])
    assert sa[:31]==sc[:31] and len(sc)==32
    assert sc[31]['VLs'][0]['X']==2 and len([v for v in sc[31]['CLs'] if v.get('Var')=='BoxPacking_A_Pickup_Done' and v.get('Not')])==1
    defs0=fields(old.read(m['scope_part']).decode('utf-8-sig'));defs=fields(new.read(m['scope_part']).decode('utf-8-sig'))
    assert set(defs)-set(defs0)==set(m['new_variable_names'])
    for name,prior in defs0.items():
        for key in set(prior)|set(defs[name]):
            if key not in ['Com','EC']:assert prior.get(key)==defs[name].get(key),(name,key)
    for name in m['new_variable_names']:
        v=defs[name];assert v['D']=='BOOL' and v['G']=='VAR' and v['Const']==v['RO']==v['R']=='0'
    ecs=E.fromstring(defs['BoxPacking_M']['EC'].encode('utf-8'))
    assert sorted(int(e.get('EK').strip('[]')) for e in ecs)==list(range(1,50))
    assert len(ecs)==49 and '初回確認完了' in defs['BoxPacking_M']['EC']
    ra,rc=rows(old,m['rcon_part']),rows(new,m['rcon_part']);rm={int(k):v for k,v in m['rcon_old_to_new_rows'].items()}
    assert len(rc)==457 and ra[:283]==rc[:283]
    for i,r in enumerate(ra):
        if i>=443:assert r==rc[rm[i]] # 通信変換STは一切変更しない。
    globals_part=next(n for n in diff if n.endswith('f07dd06c-505c-431b-b9fc-098949805b4e.xml'))
    for part in [globals_part,m['rcon_scope_part']]:
        fd0=fields(old.read(part).decode('utf-8-sig'));fd=fields(new.read(part).decode('utf-8-sig'))
        assert set(fd)-set(fd0) <= {'AutoMode'}
        for name,prior in fd0.items():
            for key in set(prior)|set(fd[name]):
                if key not in ['Com','EC']:assert prior.get(key)==fd[name].get(key),(name,key)
    for axis in range(2,6):
        base=283+(axis-2)*40
        start=rc[rm[base+5]]
        assert not any(x.get('Var')=='P_Off' for x in start['CLs'])
        assert len([x for x in start['CLs'] if x.get('Var')==f'RCON2_{axis}_M[3]'])==2
        assert next(x for x in start['CLs'] if x['__type']=='FB')['In'][1]['Var']=='T#100ms'
        assert any(x.get('Var')==f'RCON2_{axis}_M[2]' for x in rc[rm[base+39]]['CLs'])
        assert rc[rm[base+4]]==ra[base+4] # 押付け等の未使用出力は維持。
result={'changed_parts':len(diff),'unchanged_parts':len(old.namelist())-len(diff),'box_coils_sequential_1_to_49':True,'original_ST_exact':True,'b_control_preserved_with_renumbering':True,'initial_X1003_at_transfer_only':True,'new_nonretained_bool_variables':2,'rcon1_and_rcon2_1_and_output_unmodified':True,'rcon2_permission_values_unchanged':True,'existing_100ms_preserved':True}
(b/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
