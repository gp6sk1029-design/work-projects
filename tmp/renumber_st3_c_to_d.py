"""C版の下側工程11以降を繰下げ、D版へ別名保存する。"""
import copy,hashlib,json,re,sys,collections
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
sys.stdout.reconfigure(encoding='utf-8')
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_2026102C.smc2')
dst=src.with_name(src.stem[:-1]+'D.smc2')
report=dst.with_suffix('.変更内容.txt')
assert not dst.exists() and not report.exists(),'既存D版または変更記録を上書きしない'
source_hash=hashlib.sha256(src.read_bytes()).hexdigest()
assert source_hash=='6c6f3c82a0dd4785174cebd53b0f5b1ea3da99a827792fafa8d9c465029d378c','確認後にC版が更新されました'
pat=re.compile(r'ST3_A_Dis1_M\[(\d+)\]')
pair=re.compile(r'("Var"\s*:\s*")(ST3_A_Dis1_M\[(\d+)\])(")')
with ZipFile(src) as zin:
    assert zin.testzip() is None
    payload={info.filename:zin.read(info) for info in zin.infolist()}
    texts={}
    for n,b in payload.items():
        try:t=b.decode('utf-8-sig')
        except UnicodeError:continue
        if 'ST3_A_Dis1_M' in t:texts[n]=t
    assert len(texts)==4
    ladder,old_ladder=next((n,t) for n,t in texts.items() if t.lstrip().startswith('{'))
    declarations=[(n,t) for n,t in texts.items() if t.startswith('[SLWD')]
    assert len(declarations)==2
    rungs=[json.loads(l) for l in old_ladder.splitlines() if l.strip()]
    assert len(rungs)==17
    writes11=[(rn,cn,c.get('RS',False)) for rn,r in enumerate(rungs) for cn,c in enumerate(r['CLs']) if c.get('__type')=='ST' and c.get('Var')=='ST3_A_Dis1_M[11]']
    assert writes11==[(8,21,True),(9,3,False)]
    assert all(int(m[1])<=23 for m in pat.finditer(old_ladder))
    changes=[]
    lines=old_ladder.splitlines(keepends=True)
    nonempty=[i for i,line in enumerate(lines) if line.strip()]
    for rn,ln in enumerate(nonempty):
        def replace(m):
            n=int(m[3])
            # 上側の判定分岐出力[11]は新しい番号枠として残す。
            if n<11 or (rn==8 and n==11):return m[0]
            changes.append((rn,n,n+1))
            return m[1]+f'ST3_A_Dis1_M[{n+1}]'+m[4]
        lines[ln]=pair.sub(replace,lines[ln])
    new_ladder=''.join(lines)
    after=[json.loads(l) for l in new_ladder.splitlines() if l.strip()]
    expected=copy.deepcopy(rungs)
    for rn,r in enumerate(expected):
        for cn,c in enumerate(r['CLs']):
            m=pat.fullmatch(c.get('Var',''))
            if m and int(m[1])>=11 and (rn,cn)!=(8,21):c['Var']=f'ST3_A_Dis1_M[{int(m[1])+1}]'
    assert after==expected,'想定外の命令/配置/回路条件の変更'
    assert rungs[:8]==after[:8]
    assert rungs[8]['CLs'][21]==after[8]['CLs'][21]
    assert after[9]['CLs'][1]['Var']=='ST3_A_Dis1_M[12]'
    assert after[9]['CLs'][3]['Var']=='ST3_A_Dis1_M[12]'
    assert after[10]['CLs'][0]['Var']=='ST3_A_Dis1_M[12]'
    writers=[int(pat.fullmatch(c['Var'])[1]) for r in after for c in r['CLs'] if c.get('__type')=='ST' and pat.fullmatch(c.get('Var',''))]
    assert sorted(writers)==list(range(1,25))
    assert len(writers)==len(set(writers))==24
    replacements={ladder:new_ladder}
    comment_counts={}
    for n,t in declarations:
        decl=re.search(r'(?m)^.*\bN=ST3_A_Dis1_M\t[^\r\n]*',t)
        assert decl and 'ARRAY[0..99] OF Bool' in decl[0]
        comments=re.search(r'(<ECs>)(.*?)(</ECs>)',decl[0])
        assert comments
        old_root=ET.fromstring(comments[0])
        old_comments={int(e.attrib['EK'][1:-1]):e.attrib['C'] for e in old_root}
        assert len(old_comments)==len(old_root) and 11 not in old_comments
        shifted=re.sub(r'EK="\[(\d+)\]"',lambda m:f'EK="[{int(m[1])+(1 if int(m[1])>=11 else 0)}]"',comments[2])
        new_root=ET.fromstring('<ECs>'+shifted+'</ECs>')
        new_comments={int(e.attrib['EK'][1:-1]):e.attrib['C'] for e in new_root}
        assert len(new_comments)==len(new_root)==len(old_comments)
        assert new_comments=={k+(1 if k>=11 else 0):v for k,v in old_comments.items()}
        new_decl=decl[0][:comments.start(2)]+shifted+decl[0][comments.end(2):]
        new_text=t[:decl.start()]+new_decl+t[decl.end():]
        assert t.replace(decl[0],'<対象>')==new_text.replace(new_decl,'<対象>')
        replacements[n]=new_text
        comment_counts[n.rsplit('/',1)[-1]]=sum(k>=11 for k in old_comments)
    assert len(replacements)==3
    for n,t in replacements.items():
        enc='utf-8-sig' if payload[n].startswith(b'\xef\xbb\xbf') else 'utf-8'
        payload[n]=t.encode(enc)
    with ZipFile(dst,'w') as zout:
        zout.comment=zin.comment
        for info in zin.infolist():zout.writestr(info,payload[info.filename])
with ZipFile(src) as zin,ZipFile(dst) as zout:
    assert zout.testzip() is None
    assert zin.namelist()==zout.namelist()
    changed=[n for n in zin.namelist() if zin.read(n)!=zout.read(n)]
    assert set(changed)==set(replacements)
    for n in changed:assert zin.read(n).startswith(b'\xef\xbb\xbf')==zout.read(n).startswith(b'\xef\xbb\xbf')
    assert [json.loads(l) for l in zout.read(ladder).decode('utf-8-sig').splitlines() if l.strip()]==expected
    unchanged=len(zin.namelist())-3
assert hashlib.sha256(src.read_bytes()).hexdigest()==source_hash
summary='\n'.join([
    'ST3_A_Dis1_M 下側[11]以降の繰下げ（C版→D版）',
    '原本：'+str(src),'出力：'+str(dst),
    '判定分岐の上側[11]出力は保持。下側NG回収工程[11]→[12]から[23]→[24]まで変更。',
    '上側回路にある後続工程参照も含め、接点・自己保持・コイルを同じ対応で変更。',
    f'ラダー変数参照変更：{len(changes)}か所。工程出力[1]～[24]の重複・欠番なし。',
    'グローバル変数と外部変数の既存要素コメントを、本文を変えず対応番号へ移動。',
    'コメント移動件数：'+json.dumps(comment_counts,ensure_ascii=False),
    '元から未記入の[11]等には説明を追加していません。命令のRS属性・配置・回路見出しは保持。',
    f'変更は対象ラダー/外部変数コメント/グローバル変数コメントの3エントリ。対象外{unchanged}件の内容は全バイト一致。',
    'ZIP検査・JSON構造比較・UTF-8 BOM・配列範囲保持を確認。I/O割付・他変数は変更なし。',
    'ファイル名のみ日付末尾をC→Dへ変更。プロジェクト内部の名称は変更していません。',
    'Sysmac Studioでの読込み・ビルド・実機動作は未検証。実機転送なし。',
    '使用前にオフラインで差分確認・ビルドを行ってください。',
    '原本SHA256：'+source_hash,'出力SHA256：'+hashlib.sha256(dst.read_bytes()).hexdigest(),
])
report.write_text(summary+'\n',encoding='utf-8-sig')
print(summary)
