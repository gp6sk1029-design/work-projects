"""承認されたRCON2の5軸テンプレートをNSUB B版へ追加する。"""
from pathlib import Path
import collections, copy, hashlib, json, re, shutil, sys, uuid, zipfile
import xml.etree.ElementTree as ET

sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
DATA=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
SOURCE=Path(DATA['source'])
DEST=SOURCE.parent/'Codex編集用'/SOURCE.name.replace('20261030A','20261030B')
STAGED=BASE/DEST.name
REPORT=BASE/'verification.json'
ROLES={1:'段バラシ',2:'箱詰めX',3:'箱詰めY',4:'箱詰めZ',5:'コンテナ設置'}

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def fields(l): return dict(s.split('=',1) for s in l[2:].split('\t') if '=' in s)
def decls(t): return {fields(l)['N']:l for l in t.splitlines() if l.startswith('++D=')}
def edit(l,**values):
    parts=l[2:].split('\t')
    for k,v in values.items():
        i=next((i for i,p in enumerate(parts) if p.startswith(k+'=')),None)
        if i is None: parts.append(k+'='+v)
        else: parts[i]=k+'='+v
    return '++'+'\t'.join(parts)
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values(): yield from walk(x)
    elif isinstance(v,list):
        for x in v: yield from walk(x)
def add(t,l,local=False):
    assert fields(l)['N'].lower() not in {n.lower() for n in decls(t)}
    if local:
        mark='+GN=VAR_EXTERNAL'
        assert t.count(mark)==1
        return t.replace(mark,l+'\r\n'+mark,1)
    return t+l+'\r\n'
def ec_update(l,values):
    e=ET.fromstring(fields(l).get('EC','<ECs/>'))
    existing={x.get('EK'):x for x in e}
    for k,v in values.items():
        x=existing.get(k)
        if x is None: x=ET.SubElement(e,'EC',{'EK':k})
        x.set('C',v)
    return edit(l,EC=ET.tostring(e,encoding='unicode'))
def rename(v,axis):
    return v.replace('RCON1_6_',f'RCON2_{axis}_').replace('RCON1_OUT[6]',f'RCON2_OUT[{axis}]').replace('RCON1_IN[6]',f'RCON2_IN[{axis}]')

def build():
    assert digest(SOURCE)==DATA['sha256'],'調査後に原本が更新されています'
    assert not DEST.exists(),'既存の完成版は上書きしません'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
    texts=DATA['texts']
    names={key:next(n for n in texts if n.endswith(suffix)) for key,suffix in {
        'rcon':'7b1666c7-ee97-4210-81b2-fed5a6172074.xml',
        'globals':'f07dd06c-505c-431b-b9fc-098949805b4e.xml',
        'other':'a763b9a0-9d3c-4bfc-a9be-4018e5fd2a10.xml',
        'meta':'20a6b651-4c34-401a-965e-db3e18414d5c.xml'}.items()}
    rows=[json.loads(l) for l in texts[names['rcon']].splitlines() if l.strip()]
    assert len(rows)==249 and 'RCON1_6' in rows[203]['CMT']
    assert '動作完了' in rows[242]['CMT']
    assert all(any(c.get('__type')=='IST' for c in r['CLs']) for r in rows[243:])
    template=rows[203:243]
    assert not any(c.get('__type')=='IST' for r in template for c in r['CLs'])
    g_before=decls(texts[names['globals']]);other_before=decls(texts[names['other']])
    for var in ('RCON2_OUT','RCON2_IN'):
        assert fields(g_before[var])['D'].startswith('ARRAY[1..5]')
    assert not any(re.match(r'RCON2_[1-5]_',v) for v in g_before)
    used={re.split(r'[.\[]',x['Var'],1)[0] for r in template for x in walk(r) if isinstance(x.get('Var'),str) and x['Var'].startswith('RCON1_6_')}
    timer_old={x for x in used if x.endswith(('_TON','_TOF'))}
    global_old=used-timer_old
    assert len(global_old)==26 and timer_old=={'RCON1_6_TON','RCON1_6_TOF'},(len(global_old),used)
    # 未使用のError/Error_Clearや、依頼外のHMI配列・補助回路は新設しない。
    ordered=['RCON1_6_M']+[n for n in g_before if n in global_old and n!='RCON1_6_M']
    new_globals={};new_to_old={};g=texts[names['globals']];o=texts[names['other']]
    for axis,role in ROLES.items():
        for old in ordered:
            new=rename(old,axis)
            l=edit(g_before[old],N=new,Const='0',RO='0')
            if old.endswith('_M'):
                l=edit(l,Com=f'#RCON2_{axis} {role}')
            elif old.endswith('_Auto'):
                l=ec_update(edit(l,Com='自動移動要求'),{f'[{i}]':f'自動要求{i}（未接続）' for i in range(1,4)})
            g=add(g,l);new_globals[new]=l;new_to_old[new]=old
            o=add(o,edit(l,G='VAR_EXTERNAL'))
        for old in sorted(timer_old):
            l=edit(other_before[old],N=rename(old,axis),Const='0',RO='0')
            o=add(o,l,local=True)
    assert len(new_globals)==130
    # 既存通信構造体の5要素に軸用途を表示。型や保持属性はそのまま。
    for var in ('RCON2_OUT','RCON2_IN'):
        old=decls(g)[var]
        new=ec_update(old,{f'[{a}]':f'#RCON2_{a} {role}' for a,role in ROLES.items()})
        g=g.replace(old,new,1)
    # Node5の既存割付ワードは名称・アドレスを変えず、軸先頭だけ用途を追加する。
    physical_comments={}
    for var,l in list(decls(g).items()):
        f=fields(l);m=re.fullmatch(r'E005_(Out_OUT|In_IN)(\d\d)_.*',var)
        if not m or not f.get('AT','').startswith('ECAT://node#5/'): continue
        word=int(m[2])
        if not 8<=word<=47: continue
        axis=(word-8)//8+1
        desc=f.get('Com','')
        desc=re.sub(r'^#?RCON2\s*','',desc)
        desc=re.sub(r'\b'+str(axis)+r'軸目\s*','',desc)
        if (word-8)%8==0: desc=f'#RCON2_{axis} {ROLES[axis]} / '+desc
        updated=edit(l,Com=desc)
        g=g.replace(l,updated,1);physical_comments[var]=desc
    # 既存外部参照がある表だけ、変更したRCON2コメントを同期する。
    changed={names['globals']:g,names['other']:o}
    globals_now=decls(g)
    sync_names={'RCON2_OUT','RCON2_IN'}|set(physical_comments)
    for n,t in texts.items():
        if not t.startswith('[SLWD') or n==names['globals']: continue
        out=changed.get(n,t)
        for var,l in list(decls(out).items()):
            if var not in sync_names: continue
            src=fields(globals_now[var]);update={k:src[k] for k in ('Com','EC') if k in src}
            out=out.replace(l,edit(l,**update),1)
        if out!=t: changed[n]=out
    # 既存6軸と通信6行をそのまま保持し、243行目へ40行×5軸を挿入。
    added=[]
    for axis,role in ROLES.items():
        block=copy.deepcopy(template)
        for i,r in enumerate(block):
            for x in walk(r):
                if isinstance(x.get('Var'),str): x['Var']=rename(x['Var'],axis)
                if 'Id' in x: x['Id']=str(uuid.uuid4())
            if i==0: r['CMT']=f'#RCON2_{axis} {role}\r\n【出力値】\r\n目標位置 [mm]（未接続）'
            if i==5: r['CMT']='【出力信号】\r\n移動開始（条件未定・P_Off）'
            if i==6: r['CMT']='原点復帰（条件未定・P_Off）'
            if i==7: r['CMT']='一時停止（Pause[1]）'
            if i==8: r['CMT']='異常リセット（リセットSW）'
            if i==19:
                r['CLs'][0]['Var']='P_Off'
                r['CLs'][0].pop('Not',None)
                r['CMT']='ブレーキ強制解除（P_Off）'
        assert block[5]['CLs'][1]['Var']=='P_Off'
        assert block[6]['CLs'][0]['Var']==block[6]['CLs'][1]['Var']=='P_Off'
        assert block[7]['CLs'][0]['Var']=='Pause[1]'
        assert block[8]['CLs'][0]['Var']=='In_Sw_RESET'
        assert not block[19]['CLs'][0].get('Not',False)
        assert 'RCON1' not in json.dumps(block,ensure_ascii=False)
        added.extend(block)
    output=rows[:243]+added+rows[243:]
    assert len(output)==449
    changed[names['rcon']]='\r\n'.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in output)+'\r\n'
    # 新規グローバルだけをメタ情報にも登録。既存属性はコメント以外不変。
    mt=texts[names['meta']];root=ET.fromstring(mt);metas={e.get('Name'):e for e in root.iter('Variable')}
    assert len(metas)==len(list(root.iter('Variable')))
    for var in physical_comments:
        if var not in metas: continue
        element=copy.deepcopy(metas[var]);element.set('Comment',physical_comments[var]);element.tail=None
        pattern=r'<Variable\s[^<>]*\bName="'+re.escape(var)+r'"[^<>]*/>'
        mt,count=re.subn(pattern,lambda m:ET.tostring(element,encoding='unicode'),mt)
        assert count==1
    entries=[]
    for new,l in new_globals.items():
        e=copy.deepcopy(metas[new_to_old[new]])
        e.set('Name',new);e.set('Address',e.get('Address').rsplit('.',1)[0]+'.'+new)
        e.set('Id',str(uuid.uuid4()));e.set('Comment',fields(l).get('Com',''))
        for k in ('IsConstant','IsReadOnly','IsReadOnlyNetwork','IsControllerVariable','Retained'): e.set(k,'false')
        e.set('InitialValue','');e.tail=None
        entries.append(ET.tostring(e,encoding='unicode'))
    # グローバルのVariableGroupを既存のName/G属性で確認し、同じグループへ追加。
    target=root.find('.//VariableGroup')
    assert target is not None and all(x.get('Group')=='VAR_GLOBAL' for x in target if x.tag=='Variable')
    marker='  </VariableGroup>'
    assert mt.count(marker)==1
    changed[names['meta']]=mt.replace(marker,''.join('    '+e+'\r\r\n' for e in entries)+marker,1)
    # 外側ファイル名とプロジェクト表示名をBへそろえる。
    for n,t in texts.items():
        if n.endswith(('.oem','.manifest')):
            count=t.count(SOURCE.stem)
            assert count==1,(n,count)
            changed[n]=t.replace(SOURCE.stem,DEST.stem)
    # 型、割付、既存変数属性、既存回路とインラインSTの完全保持。
    for n,t in texts.items():
        if not t.startswith('[SLWD'): continue
        before=decls(t);after=decls(changed.get(n,t))
        assert len(after)==len({v.lower() for v in after})
        for var,l in before.items():
            a=fields(l);b=fields(after[var])
            for k in ('Com','EC'): a.pop(k,None);b.pop(k,None)
            assert a==b,(n,var)
    all_decl=decls(changed[names['other']])
    for r in added:
        for x in walk(r):
            v=x.get('Var','')
            if not v or v in ('P_On','P_Off','TRUE','FALSE') or '#' in v: continue
            base=re.split(r'[.\[]',v,1)[0]
            assert base in all_decl,v
    existing_ids={x['Id'] for r in rows for x in walk(r) if 'Id' in x}
    ids=[x['Id'] for r in added for x in walk(r) if 'Id' in x]
    assert len(ids)==15 and len(set(ids))==15 and not existing_ids.intersection(ids)
    assert output[:243]==rows[:243] and output[443:]==rows[243:]
    ladder_counts={}
    for n,t in texts.items():
        if not t.lstrip().startswith('{'): continue
        try: rr=[json.loads(l) for l in changed.get(n,t).splitlines() if l.strip()]
        except Exception: continue
        if rr and all(isinstance(r,dict) and 'CLs' in r for r in rr): ladder_counts[n]=len(rr)
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=comment
        for info in infos:
            raw=original[info.filename]
            if info.filename in changed:
                raw=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changed[info.filename].encode('utf-8')
            z.writestr(info,raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        assert all(z.read(n)==v for n,v in original.items() if n not in changed)
    assert digest(SOURCE)==DATA['sha256']
    report={'source':str(SOURCE),'source_sha256':DATA['sha256'],'staged':str(STAGED),'destination':str(DEST),
        'output_sha256':digest(STAGED),'roles':ROLES,'changed_entries':list(changed),'global_added':list(new_globals),
        'global_added_count':130,'external_added_count':130,'local_timers_added':10,'rcon_rows_before':249,'rcon_rows_after':449,
        'insert_rows':[243,442],'common_st_rows_after':[443,448],'physical_comments_updated':len(physical_comments),
        'original_rcon_rows_preserved':True,'common_st_unchanged':True,'existing_variables_preserved_except_comments':True,
        'ladder_counts':ladder_counts,'native_validation':None,'native_connections':None,'native_variables':None,'independent_audit':None,
        'application_build_verified':False,'plc_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('global_added','ladder_counts')},ensure_ascii=False,indent=2))

def publish():
    r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert all(r[k] for k in ('native_validation','native_connections','native_variables','independent_audit'))
    assert digest(SOURCE)==r['source_sha256'] and digest(STAGED)==r['output_sha256']
    assert not DEST.exists()
    DEST.parent.mkdir(exist_ok=True)
    # 別コントローラの既存SUB版には手を触れない。旧NSUB Codex版があれば明示確認が必要。
    old=list(DEST.parent.glob(SOURCE.stem.rsplit('20261030A',1)[0]+'*.smc2'))
    assert not old,'旧NSUB版が存在するため、履歴先との照合を先に行ってください'
    with STAGED.open('rb') as src,DEST.open('xb') as out: shutil.copyfileobj(src,out)
    assert digest(DEST)==r['output_sha256']
    r['published']=True;REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)

if __name__=='__main__': publish() if '--publish' in sys.argv else build()
