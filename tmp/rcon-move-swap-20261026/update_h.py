"""確認済みの指示に従い、RCON軸別MOVE60個の値引数だけを入れ替える。"""
from pathlib import Path
import copy,hashlib,json,shutil,sys,zipfile

sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261026G.smc2')
DEST=SOURCE.with_name(SOURCE.name.replace('20261026G','20261026H'))
STAGED=BASE/DEST.name
REPORT=BASE/'verification.json'
EXPECTED_SOURCE='128eb302c2780738e234a2c221565e7e11de7967b7008a22da6f93d0c0612611'

def walk(value):
    if isinstance(value,dict):
        yield value
        for child in value.values():yield from walk(child)
    elif isinstance(value,list):
        for child in value:yield from walk(child)

def move_args(node):
    ins=[p for p in node['In'] if p.get('Arg')=='In']
    outs=[p for p in node['Out'] if p.get('Arg')=='Out']
    assert len(ins)==len(outs)==1
    assert ins[0]['__type']==outs[0]['__type']=='PRM'
    return ins[0],outs[0]

def build():
    assert not DEST.exists(),'既存H版は上書きしません'
    source_hash=hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    assert source_hash==EXPECTED_SOURCE,'確認後にG版が変更されました'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
    name=next(n for n in original if n.endswith('7b1666c7-ee97-4210-81b2-fed5a6172074.xml'))
    text=original[name].decode('utf-8-sig')
    old=[json.loads(l) for l in text.splitlines() if l.strip()]
    assert len(old)==246
    new=copy.deepcopy(old);swaps=[]
    expected_rows={40*(axis-1)+j for axis in range(1,7) for j in [0,1,2,3,4,20,21,22,23,24]}
    for i,row in enumerate(new):
        nodes=[n for n in walk(row) if n.get('__type')=='F' and n.get('Name')=='MOVE']
        if not nodes:continue
        assert i in expected_rows and len(nodes)==1
        assert row['CLs'][0].get('Var')=='P_Off','今回の確認対象と実行条件が異なります'
        ins,outs=move_args(nodes[0]);before_in,before_out=ins['Var'],outs['Var']
        ins['Var'],outs['Var']=before_out,before_in
        swaps.append({'row':i,'axis':i//40+1,'before_in':before_in,'before_out':before_out,
                      'after_in':ins['Var'],'after_out':outs['Var']})
    assert len(swaps)==60 and {s['row'] for s in swaps}==expected_rows
    # 同じ操作で元に戻せることにより、引数以外の全属性・配線・コメント保持を確認する。
    restored=copy.deepcopy(new)
    for row in restored:
        for node in walk(row):
            if node.get('__type')=='F' and node.get('Name')=='MOVE':
                ins,outs=move_args(node);ins['Var'],outs['Var']=outs['Var'],ins['Var']
    assert restored==old
    # 変更のない行は元バイトを維持する。
    lines=text.splitlines(keepends=True)
    assert len(lines)==len(new)
    for change in swaps:
        i=change['row'];ending=lines[i][len(lines[i].rstrip('\r\n')):]
        lines[i]=json.dumps(new[i],ensure_ascii=False,separators=(',',':'))+ending
    changed=(b'\xef\xbb\xbf' if original[name].startswith(b'\xef\xbb\xbf') else b'')+''.join(lines).encode('utf-8')
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=comment
        for info in infos:z.writestr(info,changed if info.filename==name else original[info.filename])
    # 保存済みデータを独立再読込みし、全60対と全204非対象エントリを照合する。
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        assert all(z.read(n)==raw for n,raw in original.items() if n!=name)
        saved=[json.loads(l) for l in z.read(name).decode('utf-8-sig').splitlines() if l.strip()]
        assert saved==new
        for s in swaps:
            node=next(n for n in walk(saved[s['row']]) if n.get('Name')=='MOVE')
            ins,outs=move_args(node)
            assert ins['Var']==s['before_out'] and outs['Var']==s['before_in']
    counts={}
    for n,raw in original.items():
        try:t=raw.decode('utf-8-sig')
        except UnicodeError:continue
        if not t.lstrip().startswith('{'):continue
        try:rs=[json.loads(l) for l in t.splitlines() if l.strip()]
        except json.JSONDecodeError:continue
        if rs and all(isinstance(r,dict) and 'CLs' in r for r in rs):counts[n]=len(rs)
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==source_hash
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':source_hash,
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'entries':len(original),'changed_entries':[name],
            'swaps':swaps,'move_count':60,'all_conditions_P_Off_preserved':True,'comments_unchanged':True,
            'all_nonargument_ladder_data_unchanged':True,'all_other_entries_byte_identical':True,
            'ladder_counts':counts,'native_validation':None,'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('swaps','ladder_counts')},ensure_ascii=False,indent=2))

def publish():
    report=json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert report['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in report['native_validation'].values())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==report['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==report['output_sha256']
    with STAGED.open('rb') as incoming,DEST.open('xb') as outgoing:shutil.copyfileobj(incoming,outgoing)
    assert hashlib.sha256(DEST.read_bytes()).hexdigest()==report['output_sha256']
    report['published']=True
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
