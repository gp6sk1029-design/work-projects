from pathlib import Path
import sys,json,re
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;meta=json.loads((b.parent.parent/'box-cycle-implement-20261105/verification.json').read_text(encoding='utf-8'))
current=sm.Project('C:/OMRON/Data/Solution/fe78558c-1d0e-41d5-9b83-730179a87edb')
old=sm.Project('C:/Users/SEIGI-N13/work-projects/outputs/box-cycle-implement-20261105/3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105F_変更前.smc2')
g=sm.Project(meta['staged'])
def clean(rows):return [{k:v for k,v in r.items() if k!='CMT'} for r in rows]
same=clean(current.section('RCON_IAI')['rows'])==clean(g.section('RCON_IAI')['rows'])
newrows=current.section('RCON_IAI')['rows'];oldrows=old.section('RCON_IAI')['rows']
for newindex in [283,322,323,324]:
    prior=next((int(k) for k,v in meta['rcon_old_to_new_rows'].items() if v==newindex),None)
    print('ROW_MAPPING',prior,'->',newindex)
    if prior is not None:
        print('OLD',[(c['__type'],c.get('Var',c.get('Name','')),c.get('Not',False)) for c in oldrows[prior]['CLs'] if c['__type']!='HL'])
flags=['RCON2_CommOK','RCON2_WriteEnable','RCON2_LayoutConfirmed','RCON2_ByteOrderConfirmed','RCON2_AxisApply[2]','RCON2_MotionPermit[2]','RCON2_IN[2].DataValid','RCON2_EncodeOK[2]','RCON2_2_Ready']
result=[]
for tag in flags:
    writes=[];st=[]
    for sec in current.sections:
        for i,r in enumerate(sec['rows']):
            for c in r['CLs']:
                if (c['__type']=='ST' and c.get('Var')==tag) or any(p.get('Var')==tag for p in c.get('Out',[])):
                    writes.append([sec['name'],i,c['__type']])
                if c['__type']=='IST':
                    raw=json.dumps(c,ensure_ascii=False)
                    # 配列添字がループ変数の場合も別途広い文字列検索を残す。
                    base=tag.split('[')[0]
                    if re.search(re.escape(tag)+r'\s*:=',raw) or re.search(re.escape(base)+r'\[[^\]]+\](?:\.[A-Za-z0-9_]+)?\s*:=',raw):st.append([sec['name'],i])
    definitions=[];base=tag.split('[')[0]
    for part,content in current.variable_parts.items():
        for line in content.splitlines():
            if not line.startswith('++D='):continue
            f=dict(t.split('=',1) for t in line[2:].split('\t') if '=' in t)
            if f.get('N')==base and f.get('G')=='VAR_GLOBAL':definitions.append(f)
    result.append({'tag':tag,'ladder_writes':writes,'ST_assignment_candidates':st,'global_definitions':definitions})
out={'current_sha':current.fingerprint,'oldF_sha':old.fingerprint,'G_sha':g.fingerprint,'current_RCON_control_equal_G':same,'flags':result,'scope':'明示的なラダー書込みとST代入候補の検索。HMI/外部書込みや間接参照の動作は未確認。'}
out['permission_names_defined_in_F']={n:any(('\tN='+n+'\t') in content for content in old.variable_parts.values()) for n in ['RCON2_CommOK','RCON2_WriteEnable','RCON2_LayoutConfirmed','RCON2_ByteOrderConfirmed','RCON2_AxisApply','RCON2_MotionPermit']}
(b/'rcon_explanation_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
for i in [454,455,456]:
    print('COMMUNICATION_ST',i)
    for c in newrows[i]['CLs']:
        if c['__type']=='IST':
            print(json.dumps(c,ensure_ascii=False)[:11000])
