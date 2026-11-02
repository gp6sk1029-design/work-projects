"""保存済みE版を独立に読み直し、対象の8入力・割付・関連参照を照合する。"""
from pathlib import Path
import collections,copy,hashlib,json,re,sys,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent;RP=BASE/'verification.json';r=json.loads(RP.read_text(encoding='utf-8-sig'))
def fields(l):return dict(x.split('=',1) for x in l[2:].split('\t') if '=' in x)
def rows(raw):return [json.loads(l) for l in raw.decode('utf-8-sig').splitlines() if l.strip()]
inverse={v:k for k,v in r['rename_map'].items()}
def restore(v):
    if isinstance(v,dict):return {k:restore(x) for k,x in v.items() if k!='CMT'}
    if isinstance(v,list):return [restore(x) for x in v]
    if isinstance(v,str):
        for new,old in sorted(inverse.items(),key=lambda p:len(p[0]),reverse=True):
            v=re.sub(r'(?<![A-Za-z0-9_])'+re.escape(new)+r'(?![A-Za-z0-9_])',old,v)
    return v
with zipfile.ZipFile(r['source']) as a,zipfile.ZipFile(r['staged']) as b:
    assert a.namelist()==b.namelist()
    changed=[n for n in a.namelist() if a.read(n)!=b.read(n)]
    assert set(changed)==set(r['changed_entries'])
    global_defs={};declared=collections.Counter();atcount=0;declcount=0
    for n in a.namelist():
        ar=a.read(n);br=b.read(n)
        if n.endswith(('.dat','.oem')):assert ar==br
        if n in r['ladder_counts']:
            aa=rows(ar);bb=rows(br)
            assert len(aa)==len(bb)==r['ladder_counts'][n]
            assert restore(aa)==restore(bb),'命令・配線・条件・定数の不一致'
        try:at=ar.decode('utf-8-sig');bt=br.decode('utf-8-sig')
        except UnicodeError:continue
        assert not re.search(r'NG1_Tray_0[12]_[AB]_',bt)
        assert 'NG1トレイ1' not in bt and 'NG1トレイ2' not in bt
        if at.startswith('[SLWD'):
            old=[fields(l) for l in at.splitlines() if l.startswith('++D=')]
            new=[fields(l) for l in bt.splitlines() if l.startswith('++D=')]
            assert len(old)==len(new)
            for av,bv in zip(old,new):
                ac=copy.deepcopy(av);bc=copy.deepcopy(bv)
                bc['N']=inverse.get(bc['N'],bc['N'])
                ac.pop('Com',None);bc.pop('Com',None)
                assert ac==bc,'名前と説明以外の属性変化'
                if av.get('AT'):assert av['AT']==bv['AT'];atcount+=1
                if av['N'] in r['rename_map']:declcount+=1
                if bv['G']=='VAR_GLOBAL':global_defs[bv['N']]=bv;declared[bv['N']]+=1
    assert declcount==43
    assert all(v==1 for v in declared.values())
    mapping=[]
    for side,unit,sidejp in [('A',2,'A(左側)'),('B',4,'B(右側)')]:
        for ng,bit in [(1,10),(2,12)]:
            for suffix,delta,meaning in [('Full',0,'満杯停止'),('Full_Warn',1,'満杯警告')]:
                name=f'In_Sen_NG{ng}_Tray_{side}_{suffix}';g=global_defs[name]
                comment=f'【X{unit}{bit+delta}】{sidejp} NG{ng}トレイ{meaning}'
                assert g['Com']==comment,(name,g['Com'],comment)
                assert g['AT']==f'IOBus://unit#{unit}/Input Bit 32 bits/Input Bit {bit+delta}'
                assert g['D']=='BOOL'
                assert global_defs['TimerQ_'+name]['Com']==comment
                mapping.append({'new':name,'comment':comment,'address':g['AT']})
    # 全ての変更後外部参照がグローバルに存在し型も一致する。
    for item in r['declaration_renames']:
        if item['group']=='VAR_EXTERNAL':assert global_defs[item['new']]['D']==item['type']
assert hashlib.sha256(Path(r['source']).read_bytes()).hexdigest()==r['source_sha256']
r['independent_audit']={'renamed_declarations':declcount,'input_signals':mapping,'all_physical_addresses_preserved':atcount,
    'unchanged_entries':r['entries']-len(changed),'logic_and_conditions_preserved':True,'all_external_names_resolved':True,'source_unchanged':True}
RP.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print('独立照合：入力8件・宣言43件・全I/O割付'+str(atcount)+'件保持。旧名残存0、ラダー条件不変、未変更エントリ'+str(r['entries']-len(changed)))
print(json.dumps(mapping,ensure_ascii=False,indent=2))
