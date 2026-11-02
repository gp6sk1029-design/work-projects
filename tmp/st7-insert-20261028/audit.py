"""保存済みプロジェクトを行別の独立対応表で再照合する。"""
from pathlib import Path
import collections,hashlib,json,re,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
REPORT=BASE/'verification.json'
r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
PAT=re.compile(r'ST7_A_Dis2_M\[(\d+)\]')
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def flds(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
with zipfile.ZipFile(r['source']) as source,zipfile.ZipFile(r['staged']) as output:
    assert output.testzip() is None and source.namelist()==output.namelist()
    actual=[n for n in source.namelist() if source.read(n)!=output.read(n)]
    assert set(actual)==set(r['changed_entries'])
    target=next(n for n in r['ladder_counts'] if n.endswith('1c62506a-fffa-4120-bf30-bcfd518c76f9.xml'))
    original=[json.loads(l) for l in source.read(target).decode('utf-8-sig').splitlines() if l.strip()]
    after=[json.loads(l) for l in output.read(target).decode('utf-8-sig').splitlines() if l.strip()]
    assert len(original)==len(after)==31
    # 行ごとのコイル番号表を、生成側の計算式とは独立に照合する。
    expected_coils={9:[12],10:[13],11:[14],12:[15],13:[16],14:[17,18,19,20],15:[21],16:[22],
                    17:[23,24,25,26],18:[27],19:[28],20:[29],21:[30],22:[31],23:[32],24:[33]}
    for i,expected in expected_coils.items():
        got=[int(PAT.fullmatch(n['Var'])[1]) for n in walk(after[i]) if n.get('__type')=='ST' and PAT.fullmatch(n.get('Var',''))]
        assert got==expected,(i,expected,got)
    for i,(ar,br) in enumerate(zip(original,after)):
        assert ar.get('CMT')==br.get('CMT')
        aa,bb=list(walk(ar)),list(walk(br));assert len(aa)==len(bb)
        for old,new in zip(aa,bb):
            assert {k:v for k,v in old.items() if k not in ['Var','CLs','In','Out']}=={k:v for k,v in new.items() if k not in ['Var','CLs','In','Out']}
            if 'Var' not in old:continue
            m=PAT.fullmatch(old['Var'])
            if m:
                ix=int(m[1]);expected=ix
                if i>=14:
                    if i==14 and old is aa[1]:pass
                    elif i==14 and old.get('__type')=='LD' and old.get('Ix') is None and ix==16:pass
                    elif i==18 and ix==22:expected=27
                    elif ix>=22:expected=ix+6
                    elif ix>=12:expected=ix+5
                assert new['Var']==f'ST7_A_Dis2_M[{expected}]',(i,old,new)
            elif old['Var']!=new['Var']:
                assert old.get('__type')=='PRM' and old.get('Arg')=='Out'
                assert old['Var'] in ['RCON1_1_OUT_TargetPos_mm','RCON1_3_OUT_TargetPos_mm']
                assert new['Var'] in ['RCON1_3_OUT_TargetPos_mm','RCON1_5_OUT_TargetPos_mm']
    assert original[25:]==after[25:]
    assert all(original[i]==after[i] for i in [0,1,2,4,6,7,8,10,11,13])
    coil_counts=collections.Counter(int(PAT.fullmatch(n['Var'])[1]) for row in after for n in walk(row) if n.get('__type')=='ST' and PAT.fullmatch(n.get('Var','')))
    assert coil_counts=={i:1 for i in range(1,34)}
    matched_moves=0
    for i,row in enumerate(after):
        for n in walk(row):
            if n.get('Name')!='MOVE':continue
            ins=[p.get('Var','') for p in n['In'] if p.get('Arg')=='In']
            outs=[p.get('Var','') for p in n['Out'] if p.get('Arg')=='Out']
            m=re.fullmatch(r'HMI_RCON1_([35])_OUT_TargetPos\[\d+\]',ins[0] if ins else '')
            if m:assert outs==[f'RCON1_{m[1]}_OUT_TargetPos_mm'];matched_moves+=1
    assert matched_moves==16
    # ３変数表はEC以外を全て保持し、ECを除いた実行上の属性が完全一致することを確認。
    for name in r['declaration_entries']:
        at=source.read(name).decode('utf-8-sig');bt=output.read(name).decode('utf-8-sig')
        oldlines=at.splitlines();newlines=bt.splitlines();assert len(oldlines)==len(newlines)
        for a,b in zip(oldlines,newlines):
            if a==b:continue
            ap,bp=flds(a),flds(b)
            assert ap['N']==bp['N']=='ST7_A_Dis2_M'
            ap.pop('EC',None);bp.pop('EC',None);assert ap==bp
    for name in r['ladder_counts']:
        if name!=target:assert source.read(name)==output.read(name)
assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==r['source_sha256']
r['independent_audit']={'coils_1_to_33_unique':True,'row_to_coil_mapping_checked':True,
                        'all_16_axis_position_moves_consistent':True,'approved_move_changes':13,
                        'added_step_numbers_preserved':True,'other_ladders_unchanged':True,
                        'unchanged_entries':r['entries']-len(actual),'source_unchanged':True}
REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r['independent_audit'],ensure_ascii=False))
