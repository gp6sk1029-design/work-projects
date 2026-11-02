from pathlib import Path
import sys, json, hashlib, zipfile, io
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')
D = Path(__file__).parent
BASE = Path(r'\\nas-ime5\生産技術部\1.注文書\_内作設備\_1.製作中注文書')
OLD = '2717-2610A インナー巻線機 (AIW-1100T) 〈2台〉【マーレOH】'
NEW = OLD.replace('AIW-1100T', 'AIW-1200T')
source = BASE / OLD / (OLD + '.xlsx')
target = BASE / NEW / (NEW + '.xlsx')

def digest(data):
    return hashlib.sha256(data).hexdigest()

if sys.argv[1] == 'prepare':
    assert not target.parent.exists(), '変更先が既に存在します'
    assert list(source.parent.iterdir()) == [source], '対象フォルダの内容を再確認してください'
    data = source.read_bytes()
    (D / 'before.xlsx').write_bytes(data)
    w = openpyxl.load_workbook(io.BytesIO(data), read_only=True)
    value = w['集計表']['C4'].value
    assert 'AIW-1100T' in value
    w.close()
    (D / 'manifest.json').write_text(json.dumps({'hash':digest(data), 'old':value, 'new':value.replace('AIW-1100T','AIW-1200T')},ensure_ascii=False),encoding='utf-8')
    print(value)
elif sys.argv[1] == 'publish':
    m = json.loads((D / 'manifest.json').read_text(encoding='utf-8'))
    before = (D / 'before.xlsx').read_bytes()
    assert digest(source.read_bytes()) == m['hash'], '作業中に原本が変更されています'
    assert not list(source.parent.glob('~$*')), 'Excelで開かれています'
    assert not target.parent.exists()
    candidate = openpyxl.load_workbook(D / 'candidate.xlsx', read_only=True)
    assert candidate['集計表']['C4'].value == m['new']
    candidate.close()
    # 原本の印刷設定・図形・外部リンク・書式を保持し、型式文字列だけ更新する。
    old_bytes, new_bytes = b'AIW-1100T', b'AIW-1200T'
    out = io.BytesIO()
    changed = {}
    with zipfile.ZipFile(io.BytesIO(before)) as zin, zipfile.ZipFile(out,'w') as zout:
        for info in zin.infolist():
            data = zin.read(info.filename)
            if old_bytes in data:
                assert info.filename.endswith('.xml')
                changed[info.filename] = data.count(old_bytes)
                data = data.replace(old_bytes, new_bytes)
            zout.writestr(info, data)
    result = out.getvalue()
    with zipfile.ZipFile(io.BytesIO(before)) as z0, zipfile.ZipFile(io.BytesIO(result)) as z1:
        assert z0.namelist() == z1.namelist()
        for n in z0.namelist():
            assert z1.read(n) == z0.read(n).replace(old_bytes,new_bytes)
    for data_only in [False, True]:
        a = openpyxl.load_workbook(io.BytesIO(before),read_only=True,data_only=data_only)
        b = openpyxl.load_workbook(io.BytesIO(result),read_only=True,data_only=data_only)
        assert a.sheetnames == b.sheetnames
        for sa,sb in zip(a,b):
            for ra,rb in zip(sa.iter_rows(),sb.iter_rows()):
                for ca,cb in zip(ra,rb):
                    expected=ca.value.replace('AIW-1100T','AIW-1200T') if isinstance(ca.value,str) else ca.value
                    assert cb.value == expected, (sa.title,getattr(ca,'coordinate',''),ca.value,cb.value)
                    assert getattr(ca,'_style_id',None) == getattr(cb,'_style_id',None)
        if data_only:
            assert b['電気部品']['G41'].value == 1398000
            assert b['巻線']['G41'].value == 712000
        a.close();b.close()
    (D/'verified.xlsx').write_bytes(result)
    # 同じ親フォルダ内の単純な名前変更。既存の移動先には上書きしない。
    assert source.parent.parent.resolve() == BASE.resolve()
    assert target.parent.parent.resolve() == BASE.resolve()
    assert digest(source.read_bytes()) == m['hash']
    source.write_bytes(result)
    renamed_file = source.with_name(NEW+'.xlsx')
    assert not renamed_file.exists()
    source.rename(renamed_file)
    source.parent.rename(target.parent)
    assert target.is_file() and not (BASE/OLD).exists()
    assert digest(target.read_bytes()) == digest(result)
    (D/'verification.json').write_text(json.dumps({'target':str(target),'changed_xml':changed,'sha256':digest(result),'totals':[1398000,712000]},ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'target':str(target),'changed_xml_count':len(changed),'total_replacements':sum(changed.values()),'totals':[1398000,712000]},ensure_ascii=False))
