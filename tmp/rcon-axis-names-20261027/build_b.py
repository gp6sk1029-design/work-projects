"""軸１専用の旧変数名だけを統一し、A版を保持してB版を生成する。"""
from pathlib import Path
import collections,copy,hashlib,json,re,shutil,sys,zipfile
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
DATA=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
SOURCE=Path(DATA['source'])
DEST=SOURCE.with_name(SOURCE.name.replace('20261027A','20261027B'))
STAGED=BASE/DEST.name
REPORT=BASE/'verification.json'
MAP={
 'RCON1_OUT_PositionBand_mm':'RCON1_1_OUT_PositionBand_mm',
 'RCON1_OUT_Speed_mm_s':'RCON1_1_OUT_Speed_mm_s',
 'RCON1_OUT_AccDec_G':'RCON1_1_OUT_AccDec_G',
 'RCON1_OUT_PushLimit_pct':'RCON1_1_OUT_PushLimit_pct',
 'RCON1_ActualPos_mm':'RCON1_1_ActualPos_mm',
 'RCON1_Current_mA':'RCON1_1_Current_mA',
 'RCON1_ActualSpeed_mm_s':'RCON1_1_ActualSpeed_mm_s',
 'RCON1_AlarmCode':'RCON1_1_AlarmCode',
 'RCON1_DataValid':'RCON1_1_DataValid',
 'RCON1_IAI_Auto':'RCON1_1_Auto',
 'HMI_RCON1_OUT_TargetPos':'HMI_RCON1_1_OUT_TargetPos',
}
# 保存A版のHMIメタ情報には、Addressと異なる旧表示名が４件ある。
# 対応する変数の名称へ揃え、軸番号なしの表示名を残さない。
META_ALIASES={f'RCON1_{suffix}':f'RCON1_1_OUT_{suffix}' for suffix in ['PositionBand_mm','Speed_mm_s','AccDec_G','PushLimit_pct']}
ALL_MAP={**MAP,**META_ALIASES}
PAT=re.compile(r'(?<![A-Za-z0-9_])('+'|'.join(map(re.escape,sorted(ALL_MAP,key=len,reverse=True)))+r')(?![A-Za-z0-9_])')
def rename(text):return PAT.sub(lambda m:ALL_MAP[m[0]],text)
def fields(line):return dict(x.split('=',1) for x in line[2:].split('\t') if '=' in x)
def decls(t):return {fields(l)['N']:fields(l) for l in t.splitlines() if l.startswith('++D=')}
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)

def build():
    assert not DEST.exists(),'既存B版は上書きしません'
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==DATA['sha256'],'調査後にA版が変更されています'
    g=DATA['tables'][DATA['globals_name']]
    assert all(old in g and new not in g for old,new in MAP.items())
    assert 'RCON1_1_OUT_TargetPos_mm' in g and 'RCON1_OUT_TargetPos_mm' not in g
    assert all(alias not in g for alias in META_ALIASES),'HMI表示名とPLC実変数の衝突'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
    changes={};replacements={};declaration_changes=[];ladder_refs=collections.Counter()
    for n,text in DATA['texts'].items():
        after=rename(text)
        if after!=text:
            changes[n]=after
            replacements[n]=dict(collections.Counter(m[0] for m in PAT.finditer(text)))
        if text.startswith('[SLWD'):
            before_decls=decls(text);after_decls=decls(after)
            assert len(before_decls)==len(after_decls)
            assert len(after_decls)==len({v.lower() for v in after_decls})
            for name,p in before_decls.items():
                nn=MAP.get(name,name)
                expected={k:rename(v) for k,v in p.items()}
                assert after_decls[nn]==expected,(n,name)
                # 型、初期値、保持、AT、定数・読取専用等は完全に保持。
                for k in set(p)-{'N','Com','EC'}:assert p[k]==after_decls[nn][k],(name,k)
                if name in MAP:declaration_changes.append({'entry':n,'old':name,'new':nn,'type':p['D'],'group':p['G']})
            for name in ('RCON1_1_OUT_TargetPos_mm','RCON1_OUT','RCON1_IN'):
                if name in before_decls:assert before_decls[name]==after_decls[name]
        if n in DATA['ladder_counts']:
            old=[json.loads(l) for l in text.splitlines() if l.strip()]
            new=[json.loads(l) for l in after.splitlines() if l.strip()]
            assert len(old)==len(new)==DATA['ladder_counts'][n]
            assert json.loads(rename(json.dumps(old,ensure_ascii=False)))==new
            for ar,br in zip(old,new):
                assert ar.get('CMT')==br.get('CMT'),'行コメントは変更しない'
                for node in walk(ar):
                    for k in ('Var','TXT'):
                        if isinstance(node.get(k),str):ladder_refs.update(m[0] for m in PAT.finditer(node[k]))
        if text.lstrip().startswith('<'):
            try:a=ET.fromstring(text);b=ET.fromstring(after)
            except ET.ParseError:continue
            assert len(list(a.iter()))==len(list(b.iter()))
            for ae,be in zip(a.iter(),b.iter()):
                assert ae.tag==be.tag and {k:rename(v) for k,v in ae.attrib.items()}==be.attrib
                assert rename(ae.text or '')==(be.text or '')
    assert all(ladder_refs[n]>0 for n in MAP)
    assert not any(n.endswith(('.dat','.oem')) for n in changes)
    # ASCII/UTF-16LEに含まれる別形式の参照がないことを確認する。
    for n,raw in original.items():
        if n in DATA['texts']:continue
        assert not any(old.encode() in raw or old.encode('utf-16-le') in raw for old in ALL_MAP),('未対応形式の参照',n)
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=comment
        for info in infos:
            raw=original[info.filename]
            if info.filename in changes:raw=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changes[info.filename].encode('utf-8')
            z.writestr(info,raw)
    # 保存済みZIPを原本と独立照合し、許可した名前以外の差分を禁止する。
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        for n,raw in original.items():
            if n not in changes:assert z.read(n)==raw
            else:
                assert z.read(n).decode('utf-8-sig')==rename(raw.decode('utf-8-sig'))
                assert not PAT.search(z.read(n).decode('utf-8-sig'))
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':DATA['sha256'],
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'rename_map':MAP,'metadata_alias_map':META_ALIASES,
            'entries':len(original),'changed_entries':list(changes),'replacements':replacements,'declaration_renames':declaration_changes,
            'ladder_reference_counts':dict(ladder_refs),'ladder_counts':DATA['ladder_counts'],'native_validation':None,'native_variables':None,
            'names_only_verified':True,'move_direction_unchanged':True,'conditions_comments_types_and_io_unchanged':True,
            'already_renamed_target_preserved':True,'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['replacements','declaration_renames','ladder_counts','rename_map','metadata_alias_map']},ensure_ascii=False,indent=2))

def publish():
    report=json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert report['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in report['native_validation'].values())
    assert report['native_variables']
    assert report['binding_audit']['metadata_names_unique'] and report['binding_audit']['user_edited_first_row_unchanged']
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==report['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==report['output_sha256']
    with STAGED.open('rb') as incoming,DEST.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
    assert hashlib.sha256(DEST.read_bytes()).hexdigest()==report['output_sha256']
    report['published']=True
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
