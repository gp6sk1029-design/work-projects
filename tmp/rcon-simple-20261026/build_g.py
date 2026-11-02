"""完了信号を独立BOOLへ置換し、RCON関連のコメントを短くする。"""
from pathlib import Path
import collections,copy,hashlib,json,re,shutil,sys,uuid,zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape

sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
DATA=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
SOURCE=Path(DATA['source'])
DEST=SOURCE.with_name(SOURCE.name.replace('20261026F_1','20261026G'))
STAGED=BASE/DEST.name
REPORT=BASE/'verification.json'
PAT=re.compile(r'(?<![A-Za-z0-9_])RCON1_([1-6])_M\[\s*2\s*\]')
ROLES={1:('A(左側)','NG1排出(上下)'),2:('B(右側)','NG1排出(上下)'),
       3:('A(左側)','SF/NG2排出(送り)'),4:('B(右側)','SF/NG2排出(送り)'),
       5:('A(左側)','SF/NG2排出(上下)'),6:('B(右側)','SF/NG2排出(上下)')}
ROW_TITLES=['目標位置 [mm]（未接続）','位置決め幅 [mm]（未接続）','指令速度 [mm/s]（未接続）',
 '加減速度 [G]（未接続）','押付け制限 [%]（未使用）','移動開始（100ms保持）','原点復帰（未接続）',
 '一時停止（未接続）','異常リセット','サーボON（非常停止時OFF）','インチング選択',
 'ジョグ速度切替（未接続）','原点方向ジョグ（未接続）','反原点方向ジョグ（未接続）',
 'ゲイン選択0（未使用）','ゲイン選択1（未使用）','押付け選択（未使用）','押付け方向（未使用）',
 '相対移動（未使用）','ブレーキ強制解除（非非常停止中ON・落下注意）','現在位置 [mm]（未接続）',
 '指令電流 [mA]（未接続）','現在速度 [mm/s]（未接続）','異常コード（未接続）','入力有効（未接続）',
 '位置決め完了','原点復帰完了','移動中','軸異常','サーボON状態','押付け空振り（未使用）','過負荷警告',
 '指令完了','ゾーン1内','ゾーン2内','準備完了','非常停止状態（監視）','動作準備（安全許可とは別）',
 '開始指令保持','動作完了（100ms保持）']
MEMBER={
 'TargetPos_mm':'目標位置 [mm]','PositionBand_mm':'位置決め幅 [mm]','Speed_mm_s':'指令速度 [mm/s]',
 'AccDec_G':'加減速度 [G]','PushLimit_pct':'押付け制限 [%]','Control':'出力信号','ActualPos_mm':'現在位置 [mm]',
 'Current_mA':'指令電流 [mA]','ActualSpeed_mm_s':'現在速度 [mm/s]','AlarmCode':'異常コード','Status':'入力信号',
 'DataValid':'入力有効（安全許可とは別）','Start':'移動開始','Home':'原点復帰','Pause':'一時停止（安全停止とは別）',
 'Reset':'異常リセット','ServoOn':'サーボON','InchingSelect':'インチング選択（OFF=ジョグ）',
 'JogSpeedSelect':'ジョグ速度切替','JogMinus':'原点方向ジョグ','JogPlus':'反原点方向ジョグ',
 'GainSelect0':'ゲイン選択0','GainSelect1':'ゲイン選択1','PushEnable':'押付け選択（OFF=位置決め）',
 'PushDirection':'押付け方向','RelativeMove':'相対移動（OFF=絶対）','BrakeRelease':'ブレーキ強制解除（落下注意）',
 'PositionDone':'位置決め完了','HomeDone':'原点復帰完了','Moving':'移動中','Alarm':'軸異常','ServoReady':'サーボON状態',
 'PushMiss':'押付け空振り','OverloadWarning':'過負荷警告','CommandDone':'指令完了（空振り含む）',
 'Zone1':'ゾーン1内','Zone2':'ゾーン2内','ControllerReady':'準備完了','EmergencyStop':'非常停止状態（監視）'}
TYPE_COM={'ST_RCON_Direct_OUT_Control':'#RCON 出力信号','ST_RCON_Direct_IN_Status':'#RCON 入力信号',
          'ST_RCON_Direct_OUT_Axis':'#RCON 軸出力','ST_RCON_Direct_IN_Axis':'#RCON 軸入力'}

def fields(line):return dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p)
def decls(t):return {fields(l)['N']:l for l in t.splitlines() if l.startswith('++D=')}
def edit(line,**values):
    parts=line[2:].split('\t')
    for k,v in values.items():
        i=next((i for i,p in enumerate(parts) if p.startswith(k+'=')),None)
        if i is None:parts.append(k+'='+v)
        else:parts[i]=k+'='+v
    return '++'+'\t'.join(parts)
def walk(v):
    if isinstance(v,dict):
        yield v
        for x in v.values():yield from walk(x)
    elif isinstance(v,list):
        for x in v:yield from walk(x)
def rename(s):return PAT.sub(lambda m:f'RCON1_{m[1]}_MoveDone',s)
def ecxml(root):return ET.tostring(root,encoding='unicode',short_empty_elements=True)
def heading(axis):return f'#{ROLES[axis][0]} RCON1_{axis} {ROLES[axis][1]}'
def short(c):
    c=re.sub(r'^[AB]\((?:左側|右側)\) RCON1_[1-6] (?:NG1上下降|SF/NG2送り|SF/NG2上下降)[ ／]*','',c)
    c=re.sub(r'^RCON[12](?:/Node[15])?\s*','',c)
    for a,b in [('共通加減速度','加減速度'),('非常停止状態（入力）','非常停止状態（監視）'),
                ('入力有効（安全許可ではない）','入力有効（安全許可とは別）'),
                ('異常管理用予備（未接続）','異常予備（未接続）'),('異常解除用予備（未接続）','解除予備（未接続）'),
                ('（監視転送未接続：P_Off）','（未接続）'),('（転送未接続：P_Off）','（未接続）'),
                ('（未接続：P_Off）','（未接続）'),('（未使用・読取無効）','（未使用）'),
                ('（非常停止でない間ON）','（非非常停止中ON・落下注意）'),
                ('現在速度 [mm/s・符号付き]','現在速度 [mm/s]'),('コントローラ準備完了','準備完了'),
                ('コントローラー準備完了','準備完了'),('開始・完了保持','動作管理')]:c=c.replace(a,b)
    return c

def build():
    assert not DEST.exists(),'既存G版は上書きしません'
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==DATA['sha256'],'F_1版が調査後に更新されています'
    with zipfile.ZipFile(SOURCE) as z:
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();archive_comment=z.comment
    texts=DATA['texts'];changes={};ladder_counts={};ref_counts=collections.Counter();rowchanges=0
    global_name=next(n for n,t in texts.items() if t.startswith('[SLWD') and '+GN=VAR_GLOBAL' in t)
    before_globals=decls(texts[global_name]);after_globals={}
    assert all(f'RCON1_{i}_MoveDone' not in before_globals for i in ROLES)
    # ラダーはVar文字列のみ置換。CMT以外の構造と全動作条件を逆変換で検証する。
    for n,t in texts.items():
        if not t.lstrip().startswith('{'):continue
        try:old=[json.loads(l) for l in t.splitlines() if l.strip()]
        except Exception:continue
        if not old or not all('CLs' in r for r in old):continue
        ladder_counts[n]=len(old);new=copy.deepcopy(old)
        for i,row in enumerate(new):
            for node in walk(row):
                for key in ('Var','TXT'):
                    if isinstance(node.get(key),str):
                        for match in PAT.finditer(node[key]):ref_counts[int(match[1])]+=1
                        node[key]=rename(node[key])
            if n.endswith('7b1666c7-ee97-4210-81b2-fed5a6172074.xml'):
                assert len(old)==246
                if i<240:
                    axis,local=i//40+1,i%40
                    com=ROW_TITLES[local]
                    if local==5:com+='／NG1戻条件' if axis<=2 else '（条件未定・禁止）'
                    group={0:'出力値',5:'出力信号',20:'入力値',25:'入力信号',37:'動作管理'}.get(local)
                    row['CMT']=(heading(axis)+'\r\n' if local==0 else '')+(f'【{group}】\r\n' if group else '')+com
                else:
                    shared=['#RCON1/Node1 共通通信\r\n入力変換','出力変換','実I/O書込み（許可OFF=前値保持）',
                            '#RCON2/Node5 共通通信\r\n入力変換','出力変換','実I/O書込み（許可OFF=前値保持）']
                    row['CMT']=shared[i-240]
            rowchanges+=row.get('CMT')!=old[i].get('CMT')
        def normalized(rows):
            x=copy.deepcopy(rows)
            for row in x:
                row.pop('CMT',None)
                for node in walk(row):
                    for key in ('Var','TXT'):
                        if isinstance(node.get(key),str):node[key]=rename(node[key])
            return x
        assert normalized(new)==normalized(old),(n,'動作条件の差異')
        if new!=old:
            ending='\r\n' if '\r\n' in t else '\n'
            changes[n]=ending.join(json.dumps(r,ensure_ascii=False,separators=(',',':')) for r in new)+ending
    assert ref_counts=={1:6,2:3,3:3,4:3,5:3,6:3},ref_counts
    # グローバルと全外部参照のコメントを同じ規則で短縮する。
    var_comment_changes=ec_changes=0;new_declarations=[]
    for n,t in texts.items():
        if not t.startswith('[SLWD'):continue
        table=decls(t);newlines=[]
        for line in t.splitlines(keepends=True):
            if not line.startswith('++D='):newlines.append(line);continue
            ending=line[len(line.rstrip('\r\n')):];line=line.rstrip('\r\n');p=fields(line);name=p['N']
            relevant=name.startswith(('RCON1_','RCON2_','HMI_RCON')) or ('RCON' in p.get('Com','') and name.startswith(('E001_','E005_')))
            if relevant:
                old_com=p.get('Com','');com=short(old_com)
                axis_m=re.fullmatch(r'RCON1_([1-6])_M',name)
                if axis_m:com=heading(int(axis_m[1]))
                if re.fullmatch('RCON[12]_(IN|OUT)',name):com='#'+name.replace('_IN',' 入力値').replace('_OUT',' 出力値')
                line=edit(line,Com=com);var_comment_changes+=com!=old_com
                if p.get('EC'):
                    root=ET.fromstring(p['EC'])
                    for el in root:
                        ek,c=el.get('EK'),el.get('C','');nc=short(c)
                        if axis_m and ek=='[2]':nc='予備'
                        if name in ('RCON1_OUT','RCON1_IN'):
                            am=re.fullmatch(r'\[([1-6])\]',ek)
                            if am:nc='#'+ROLES[int(am[1])][0]+' '+ROLES[int(am[1])][1]
                            elif '.' in ek:
                                member=ek.rsplit('.',1)[-1]
                                nc=MEMBER.get(member,nc)
                                if any(x in c for x in ('未使用','未接続')):nc+='（未使用）' if '未使用' in c else '（未接続）'
                        if nc!=c:el.set('C',nc);ec_changes+=1
                    line=edit(line,EC=ecxml(root))
            newlines.append(line+ending)
            am=re.fullmatch(r'RCON1_([1-6])_M',name)
            if am:
                newname=f'RCON1_{am[1]}_MoveDone'
                assert newname not in table
                # 元配列は残し、使われていた[2]だけを同属性の独立BOOLへ置換する。
                template=table[f'RCON1_{am[1]}_Ready'] if f'RCON1_{am[1]}_Ready' in table else table[name]
                extra=edit(template,D='BOOL',N=newname,Com='動作完了',Const='0',RO='0')
                extra='++'+'\t'.join(x for x in extra[2:].split('\t') if not x.startswith(('EC=','AT=')))
                newlines.append(extra+(ending or '\r\n'));new_declarations.append((n,newname,p['G']))
        newtext=''.join(newlines)
        if newtext!=t:changes[n]=newtext
        after=decls(newtext)
        assert len(after)==len([l for l in newtext.splitlines() if l.startswith('++D=')])
        assert len(after)==len(set(v.lower() for v in after))
        for name,line in table.items():
            a,b=fields(line),fields(after[name])
            for key in ('Com','EC'):a.pop(key,None);b.pop(key,None)
            assert a==b,(n,name,'既存の変数属性が変化')
        if n==global_name:after_globals=after
    assert collections.Counter(g for _,_,g in new_declarations)=={'VAR_GLOBAL':6,'VAR_EXTERNAL':7},new_declarations
    # 利用者が更新したグローバル側の説明を正とし、古い外部参照側の説明と揃える。
    for n,t in texts.items():
        if not t.startswith('[SLWD'):continue
        current=changes.get(n,t);lines=[]
        for line in current.splitlines(keepends=True):
            if line.startswith('++D='):
                ending=line[len(line.rstrip('\r\n')):];bare=line.rstrip('\r\n');p=fields(bare);name=p['N']
                if p['G']=='VAR_EXTERNAL' and name in after_globals and name.startswith(('RCON1_','RCON2_','HMI_RCON')):
                    gp=fields(after_globals[name]);updates={'Com':gp.get('Com','')}
                    if 'EC' in gp:updates['EC']=gp['EC']
                    bare=edit(bare,**updates);line=bare+ending
            lines.append(line)
        synced=''.join(lines)
        if synced!=t:changes[n]=synced
    for n,t in texts.items():
        if not t.startswith('[SLWD'):continue
        for name,line in decls(changes.get(n,t)).items():
            p=fields(line)
            if re.fullmatch('RCON1_[1-6]_MoveDone',name):
                assert p['D']=='BOOL' and p['Const']=='0' and p['RO']=='0' and 'AT' not in p and p.get('R','0')=='0'
            if name in after_globals and p['G']=='VAR_EXTERNAL':
                gp=fields(after_globals[name]);assert p['D'].upper()==gp['D'].upper()
                if name.startswith(('RCON1_','RCON2_','HMI_RCON')):assert p.get('Com')==gp.get('Com') and p.get('EC')==gp.get('EC'),name
    # HMI用メタデータはコメントと新規６BOOLだけを変更する。
    meta_name=next(n for n in texts if n.endswith('20a6b651-4c34-401a-965e-db3e18414d5c.xml'))
    meta=texts[meta_name];old_meta={e.get('Name'):e for e in ET.fromstring(meta).iter('Variable')}
    def update_meta(m):
        el=ET.fromstring(m[0]);name=el.get('Name')
        if name not in after_globals:return m[0]
        c=fields(after_globals[name]).get('Com','')
        if c==el.get('Comment'):return m[0]
        return re.sub(r'\bComment="[^"]*"','Comment="'+escape(c,{'"':'&quot;'})+'"',m[0],count=1)
    meta=re.sub(r'<Variable\b[^>]*?/>',update_meta,meta)
    added=[]
    for i in ROLES:
        el=copy.deepcopy(old_meta[f'RCON1_{i}_Ready']);name=f'RCON1_{i}_MoveDone'
        el.set('Name',name);el.set('Address','new_Controller_0.'+name);el.set('Id',str(uuid.uuid4()))
        el.set('DataTypeName','Boolean');el.set('Comment','動作完了');el.set('IsConstant','false');el.set('IsReadOnly','false')
        el.set('Retained','false');el.set('InitialValue','');el.tail=None
        added.append(ET.tostring(el,encoding='unicode'))
    marker='  </VariableGroup>';assert marker in meta
    meta=meta.replace(marker,''.join('    '+s+'\r\r\n' for s in added)+marker,1)
    new_meta={e.get('Name'):e for e in ET.fromstring(meta).iter('Variable')}
    assert len(new_meta)==len(old_meta)+6
    for name,el in old_meta.items():
        a,b=dict(el.attrib),dict(new_meta[name].attrib);a.pop('Comment',None);b.pop('Comment',None);assert a==b,name
    changes[meta_name]=meta
    # RCONの４構造体のみ、コメント以外の型・順序・配列・初期値は保持する。
    type_name=next(n for n in texts if n.endswith('4bdcdc10-734d-4589-b299-075e93db9b10.xml'))
    type_text=texts[type_name];tree=ET.fromstring(type_text);type_comments={}
    for el in tree.iter('DataType'):
        if el.get('Name') in TYPE_COM:
            type_comments[el.get('Name')]=TYPE_COM[el.get('Name')]
            for child in el:type_comments[child.get('Name')]=MEMBER[child.get('Name')]
    def type_block(m):
        block=m[0]
        def attr(a):
            tag=a[0];name=re.search(r'\bName="([^"]*)"',tag)[1]
            return re.sub(r'\bComment="[^"]*"','Comment="'+escape(type_comments[name],{'"':'&quot;'})+'"',tag,count=1)
        return re.sub(r'<DataType\b[^>]*>',attr,block)
    type_text=re.sub(r'<DataType\b[^>]*\bName="ST_RCON_[^"]*"[^>]*>.*?</DataType>',type_block,type_text,flags=re.S)
    def clean_types(t):
        tree=ET.fromstring(t)
        for el in tree.iter():el.attrib.pop('Comment',None)
        return ET.tostring(tree)
    assert clean_types(type_text)==clean_types(texts[type_name])
    changes[type_name]=type_text
    # 未変更のバイナリや設定を含めて保持し、旧[2]参照の残りがないことを確認する。
    assert not any(n.endswith(('.dat','.oem')) for n in changes)
    for n,t in texts.items():assert not PAT.search(changes.get(n,t)),('置換漏れ',n)
    for n,raw in original.items():
        if n not in texts:
            assert not re.search(rb'RCON1_[1-6]_M\[2\]',raw),('バイナリ内の旧参照',n)
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=archive_comment
        for info in infos:
            raw=original[info.filename]
            if info.filename in changes:raw=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changes[info.filename].encode('utf-8')
            z.writestr(info,raw)
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        assert all(z.read(n)==raw for n,raw in original.items() if n not in changes)
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':DATA['sha256'],
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'changed_entries':list(changes),'entries':len(original),
            'renamed_references':dict(ref_counts),'global_added':6,'external_added':7,'row_comments_changed':rowchanges,
            'declaration_comments_changed':var_comment_changes,'element_comments_changed':ec_changes,
            'ladder_counts':ladder_counts,'native_validation':None,'native_variable_attributes':None,
            'logic_identical_after_reference_mapping':True,'existing_declaration_attributes_unchanged':True,
            'type_structure_unchanged':True,'network_and_dat_unchanged':True,'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='ladder_counts'},ensure_ascii=False,indent=2))

def publish():
    report=json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert report['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in x for x in report['native_validation'].values())
    assert report['native_variable_attributes']
    assert report['independent_audit']['all_ladders_equal_except_comments_and_requested_rename']
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==report['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==report['output_sha256']
    with STAGED.open('rb') as a,DEST.open('xb') as b:shutil.copyfileobj(a,b)
    report['published']=True
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)

if __name__=='__main__':publish() if '--publish' in sys.argv else build()
