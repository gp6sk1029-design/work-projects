"""ST3工程の欠番11を詰め、原本を保持した確認用smc2を生成する。"""
import collections,copy,hashlib,json,re,sys
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
sys.stdout.reconfigure(encoding='utf-8')
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_2026102B.smc2')
dst=src.with_name(src.stem+'_ST3欠番修正_確認用.smc2')
report=dst.with_suffix('.変更内容.txt')
assert not dst.exists() and not report.exists(),'既存出力を上書きしない'
original_hash=hashlib.sha256(src.read_bytes()).hexdigest()
assert original_hash=='926bdc748bf1d53322862ccd2d704a25d59c378defd50502083076124e94387e','確認後に原本が更新されています'
pat=re.compile(r'ST3_A_Dis1_M\[(\d+)\]')
pair=re.compile(r'("Var"\s*:\s*")(ST3_A_Dis1_M\[(\d+)\])(")')
with ZipFile(src) as zin:
    assert zin.testzip() is None
    payload={i.filename:zin.read(i) for i in zin.infolist()}
    targets=[]
    for name,raw in payload.items():
        try:t=raw.decode('utf-8-sig')
        except UnicodeError:continue
        if 'ST3_A_Dis1_M' in t:targets.append((name,t))
    assert len(targets)==2,'想定外の別箇所に参照があります'
    ladder,old_ladder=next((n,t) for n,t in targets if t.lstrip().startswith('{'))
    variables,old_vars=next((n,t) for n,t in targets if t.startswith('[SLWD'))
    old_rungs=[json.loads(line) for line in old_ladder.splitlines() if line.strip()]
    assert not any(int(m[1])==11 for m in pat.finditer(old_ladder))
    assert max(int(m[1]) for m in pat.finditer(old_ladder))==25
    changes=[]
    def replace(m):
        n=int(m[3])
        if n<12:return m[0]
        assert n<=25
        changes.append((n,n-1))
        return m[1]+f'ST3_A_Dis1_M[{n-1}]'+m[4]
    new_ladder=pair.sub(replace,old_ladder)
    new_rungs=[json.loads(line) for line in new_ladder.splitlines() if line.strip()]
    def transform(obj):
        if isinstance(obj,dict):
            result={k:transform(v) for k,v in obj.items()}
            if isinstance(result.get('Var'),str):
                m=pat.fullmatch(result['Var'])
                if m and int(m[1])>=12:result['Var']=f'ST3_A_Dis1_M[{int(m[1])-1}]'
            return result
        if isinstance(obj,list):return [transform(v) for v in obj]
        return obj
    assert transform(old_rungs)==new_rungs,'想定外の命令/条件/配置/コメント変更'
    assert old_rungs[:8]==new_rungs[:8],'前半工程に変更が発生'
    def writers(rungs):
        return [int(pat.fullmatch(c['Var'])[1]) for r in rungs for c in r['CLs'] if c.get('__type')=='ST' and pat.fullmatch(c.get('Var',''))]
    old_writers=writers(old_rungs)
    new_writers=writers(new_rungs)
    assert sorted(old_writers)==list(range(1,11))+list(range(12,25))
    assert sorted(new_writers)==list(range(1,24))
    assert len(new_writers)==len(set(new_writers))==len(old_writers)==23
    decl=re.search(r'(?m)^.*\bN=ST3_A_Dis1_M\t[^\r\n]*',old_vars)
    assert decl and 'ARRAY[0..99] OF Bool' in decl[0]
    comments=re.search(r'(<ECs>)(.*?)(</ECs>)',decl[0])
    assert comments
    old_root=ET.fromstring(comments[0])
    old_comments={int(e.attrib['EK'][1:-1]):e.attrib['C'] for e in old_root}
    assert 11 not in old_comments and len(old_root)==len(old_comments)
    shifted=re.sub(r'EK="\[(\d+)\]"',lambda m:f'EK="[{int(m[1])-(1 if int(m[1])>=12 else 0)}]"',comments[2])
    new_root=ET.fromstring('<ECs>'+shifted+'</ECs>')
    new_comments={int(e.attrib['EK'][1:-1]):e.attrib['C'] for e in new_root}
    assert len(new_comments)==len(new_root)==len(old_comments)
    assert new_comments=={n-(1 if n>=12 else 0):c for n,c in old_comments.items()}
    new_decl=decl[0][:comments.start(2)]+shifted+decl[0][comments.end(2):]
    new_vars=old_vars[:decl.start()]+new_decl+old_vars[decl.end():]
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
    for n in changed:assert zin.read(n).startswith(b'\xef\xbb\xbf')==zout.read(n).startswith(b'\xef\xbb\xbf')
    assert [json.loads(l) for l in zout.read(ladder).decode('utf-8-sig').splitlines() if l.strip()]==new_rungs
    unchanged=len(zin.namelist())-2
assert hashlib.sha256(src.read_bytes()).hexdigest()==original_hash
counts=collections.Counter(changes)
summary='\n'.join([
    'ST3_A_Dis1_M 欠番[11]の解消（オフライン確認用）',
    '原本：'+str(src),'修正版：'+str(dst),
    'ユーザー確認済み：新しい動作回路は追加せず、番号を詰める。',
    '[1]～[10]は維持。[12]→[11]から[25]→[24]まで全参照を1つずつ繰上げ。',
    '既存コイルは旧[12]～[24]→新[11]～[23]。合計23個は不変、[1]～[23]の重複・欠番なし。',
    '先行回路の後続参照、自己保持、判定分岐なども同じ対応で修正。',
    '要素コメントは本文を保持して番号だけ対応。旧[14]のピックアップ戻コメント→新[13]。',
    'もともとコメントがない要素へ説明は追加していません。',
    f'変数参照変更：{len(changes)}か所。コメント移動：{sum(n>=12 for n in old_comments)}件。',
    '変更番号別の件数：'+', '.join(f'[{a}]→[{b}] {n}件' for (a,b),n in sorted(counts.items())),
    f'ZIP内はラダーと要素コメントの2件のみ変更。対象外{unchanged}件の内容は全バイト一致。',
    'JSON構造比較、ZIP検査、UTF-8 BOM、配列型ARRAY[0..99] OF Bool保持を確認。',
    '元から旧[25]は接点参照のみで、対応コイルは存在しません。新[24]へ番号のみ変更し、動作回路は創作していません。',
    'I/O割付、他の変数、命令、配置、回路コメント本文は変更していません。',
    'Sysmac Studioでの読込み・ビルド・実機動作は未検証。実機転送は行っていません。',
    '原本SHA256：'+original_hash,'出力SHA256：'+hashlib.sha256(dst.read_bytes()).hexdigest(),
])
report.write_text(summary+'\n',encoding='utf-8-sig')
print(summary)
