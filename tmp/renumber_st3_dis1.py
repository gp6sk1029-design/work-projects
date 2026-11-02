"""ST3左NG1排出の工程番号を確認し、指定範囲だけ修正する。"""
import hashlib,json,re,sys,collections
from pathlib import Path
from zipfile import ZipFile
sys.stdout.reconfigure(encoding='utf-8')
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261022A.smc2')
pat=re.compile(r'ST3_A_Dis1_M\[(\d+)\]')
if '--build' in sys.argv:
    import copy
    from xml.sax.saxutils import escape
    dst=src.with_name(src.stem+'_ST3工程番号修正_確認用.smc2')
    report=dst.with_suffix('.変更内容.txt')
    assert not dst.exists() and not report.exists(),'既存出力を上書きしない'
    before_hash=hashlib.sha256(src.read_bytes()).hexdigest()
    with ZipFile(src) as zin:
        payload={i.filename:zin.read(i) for i in zin.infolist()}
        targets=[]
        for name,raw in payload.items():
            try:t=raw.decode('utf-8-sig')
            except UnicodeError:continue
            if 'ST3_A_Dis1_M' in t:targets.append((name,t))
        assert len(targets)==2, '対象変数の参照範囲が想定と違う'
        ladder,old_ladder=next((n,t) for n,t in targets if t.lstrip().startswith('{'))
        variables,old_vars=next((n,t) for n,t in targets if t.startswith('[SLWD'))
        rungs=[json.loads(line) for line in old_ladder.splitlines() if line.strip()]
        assert len(rungs)==10
        writes5=[(rn,cn) for rn,r in enumerate(rungs) for cn,c in enumerate(r['CLs']) if c.get('__type')=='ST' and c.get('Var')=='ST3_A_Dis1_M[5]']
        assert writes5==[(5,5),(6,6)]
        assert rungs[6]['CLs'][0]['Var']=='ST3_A_Dis1_M[5]'
        assert rungs[5]['CLs'][4]['Var']=='ST3_A_Dis1_M[6]'
        assert 'ストッパー戻' in rungs[5]['CMT'] and 'データ転送' in rungs[6]['CMT']
        changes=[]
        # Var文字列だけを置換し、配置・条件・書式を保持する。
        pair=re.compile(r'("Var"\s*:\s*")(ST3_A_Dis1_M\[(\d+)\])(")')
        lines=old_ladder.splitlines(keepends=True)
        nonempty=[i for i,line in enumerate(lines) if line.strip()]
        for rn,ln in enumerate(nonempty):
            occurrence=[0]
            def replace(m):
                ix=occurrence[0];occurrence[0]+=1
                n=int(m[3])
                # データ転送工程の先頭a接点は、直前のストッパー戻[5]の参照。
                if rn<6 or (rn==6 and ix==0):return m[0]
                assert 5<=n<=11
                changes.append((rn,ix,n,n+1))
                return m[1]+f'ST3_A_Dis1_M[{n+1}]'+m[4]
            lines[ln]=pair.sub(replace,lines[ln])
        new_ladder=''.join(lines)
        after=[json.loads(line) for line in new_ladder.splitlines() if line.strip()]
        expected=copy.deepcopy(rungs)
        for rn,r in enumerate(expected):
            for cn,c in enumerate(r['CLs']):
                m=pat.fullmatch(c.get('Var',''))
                if m and rn>=6 and (rn,cn)!=(6,0):c['Var']=f'ST3_A_Dis1_M[{int(m[1])+1}]'
        assert expected==after,'想定外の回路変更'
        assert rungs[:6]==after[:6],'上側の工程を変更しない'
        assert after[6]['CLs'][0]['Var']=='ST3_A_Dis1_M[5]'
        assert after[6]['CLs'][2]['Var']=='ST3_A_Dis1_M[6]'
        assert after[6]['CLs'][4]['Var']=='ST3_A_Dis1_M[7]'
        assert after[6]['CLs'][6]['Var']=='ST3_A_Dis1_M[6]'
        assert after[7]['CLs'][0]['Var']=='ST3_A_Dis1_M[6]'
        writers=[int(pat.fullmatch(c['Var'])[1]) for r in after for c in r['CLs'] if c.get('__type')=='ST' and pat.fullmatch(c.get('Var',''))]
        assert sorted(writers)==list(range(1,13)),'工程コイルの欠番または重複'
        decl=re.search(r'(?m)^.*\bN=ST3_A_Dis1_M\t[^\r\n]*',old_vars)
        assert decl and 'ARRAY[0..99] OF Bool' in decl[0]
        comments=re.search(r'(<ECs>)(.*?)(</ECs>)',decl[0])
        assert comments
        import xml.etree.ElementTree as ET
        old_comment_root=ET.fromstring(comments[0])
        old_comments={int(e.attrib['EK'][1:-1]):e.attrib['C'] for e in old_comment_root}
        assert old_comments=={6:'原点位置 移動開始',5:'原点位置移動 データ転送'}
        shifted=re.sub(r'EK="\[(\d+)\]"',lambda m:f'EK="[{int(m[1])+1}]"',comments[2])
        first_comment=escape(rungs[5]['CMT'],{'"':'&quot;'})
        shifted+=f'<EC EK="[5]" C="{first_comment}" />'
        new_decl=decl[0][:comments.start(2)]+shifted+decl[0][comments.end(2):]
        new_vars=old_vars[:decl.start()]+new_decl+old_vars[decl.end():]
        new_comment_root=ET.fromstring('<ECs>'+shifted+'</ECs>')
        new_comments={int(e.attrib['EK'][1:-1]):e.attrib['C'] for e in new_comment_root}
        assert len(new_comment_root)==len(new_comments)==3
        assert new_comments=={5:rungs[5]['CMT'],6:old_comments[5],7:old_comments[6]}
        assert old_vars.replace(decl[0],'<対象宣言>')==new_vars.replace(new_decl,'<対象宣言>')
        for name,text in ((ladder,new_ladder),(variables,new_vars)):
            enc='utf-8-sig' if payload[name].startswith(b'\xef\xbb\xbf') else 'utf-8'
            payload[name]=text.encode(enc)
        with ZipFile(dst,'w') as zout:
            zout.comment=zin.comment
            for info in zin.infolist():zout.writestr(info,payload[info.filename])
    with ZipFile(src) as zin,ZipFile(dst) as zout:
        assert zout.testzip() is None
        assert zin.namelist()==zout.namelist()
        changed=[n for n in zin.namelist() if zin.read(n)!=zout.read(n)]
        assert set(changed)=={ladder,variables}
        unchanged=len(zin.namelist())-len(changed)
        for name in changed:
            assert zin.read(name).startswith(b'\xef\xbb\xbf')==zout.read(name).startswith(b'\xef\xbb\xbf')
    assert hashlib.sha256(src.read_bytes()).hexdigest()==before_hash
    summary='\n'.join([
        'ST3_A_Dis1_M 工程番号修正（確認用コピー）',
        '原本：'+str(src),'出力：'+str(dst),
        '上側[5]（ストッパー戻）のコイル・自己保持接点は維持。',
        '下側[5]（原点位置移動 データ転送）→[6]。従来[6]→[7]から[11]→[12]まで繰下げ。',
        '下側データ転送工程の先頭a接点[5]は直前工程参照のため維持。',
        '上側ストッパー戻のb接点[6]は新しい次工程[6]を参照するため維持。',
        '自己保持・後続工程条件・判定分岐の接点/コイルも対応して修正。',
        'コメント：旧[5]データ転送→[6]、旧[6]移動開始→[7]。',
        '残す[5]には回路見出し「'+rungs[5]['CMT']+'」を設定。',
        '元からコメントがない他の配列要素へ説明は追加しない。回路コメントの本文は変更なし。',
        f'変数参照変更：{len(changes)}か所。工程コイル[1]～[12]の重複/欠番なし。',
        f'変更エントリ2件、対象外{unchanged}件の内容は全バイト一致。ZIP検査・JSON構造比較・BOM保持を確認。',
        'ARRAY[0..99] OF Bool、I/O割付、他の変数、命令・回路条件・配置は変更なし。',
        'Sysmac Studioでの読込み・ビルド・実機動作は未検証。実機転送は行っていません。',
        '使用前にオフラインで開き、差分確認・ビルドと工程動作の確認を行ってください。',
        '原本SHA256：'+before_hash,'出力SHA256：'+hashlib.sha256(dst.read_bytes()).hexdigest(),
    ])
    report.write_text(summary+'\n',encoding='utf-8-sig')
    print(summary)
    sys.exit()
with ZipFile(src) as z:
    assert z.testzip() is None
    print('原本SHA256',hashlib.sha256(src.read_bytes()).hexdigest())
    for name in z.namelist():
        raw=z.read(name)
        try:t=raw.decode('utf-8-sig')
        except UnicodeError:continue
        if 'ST3_A_Dis1_M' not in t:continue
        print('\nENTRY',name,'BYTES',len(raw))
        if t.lstrip().startswith('{'):
            for rn,line in enumerate(t.splitlines()):
                if not line.strip():continue
                rung=json.loads(line)
                print('RUNG',rn,'META',{k:v for k,v in rung.items() if k!='CLs'})
                for cn,c in enumerate(rung.get('CLs',[])):
                    if rn in (5,6,7,8,9):print('CELL',cn,json.dumps(c,ensure_ascii=False))
        else:
            for line in t.splitlines():
                if 'ST3_A_Dis1_M' in line:print('DECL',line)
