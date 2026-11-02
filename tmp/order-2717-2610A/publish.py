import copy
import hashlib
import json
import re
import shutil
import sys
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.sax.saxutils import escape
import openpyxl

sys.stdout.reconfigure(encoding='utf-8')
local = Path(__file__).parent
meta = json.loads((local/'manifest.json').read_text(encoding='utf-8'))
backup = local/'原紙バックアップ.xlsx'
candidate = local/'candidate.xlsx'
ns = {'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
q = '{'+ns['s']+'}'

def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def strings(z):
    if 'xl/sharedStrings.xml' not in z.namelist(): return []
    return [''.join(n.itertext()) for n in ET.fromstring(z.read('xl/sharedStrings.xml'))]
def text_of(c, ss):
    t = c.get('t')
    if t == 'inlineStr': return ''.join(c.find(q+'is').itertext())
    v = c.find(q+'v')
    if v is None: return None
    return ss[int(v.text)] if t == 's' else v.text

expected = {'C3':'2717-2610A','C4':'インナー巻線機 (AIW-1100T) 〈2台〉【マーレOH】'}
outdir = local.parents[1]/'outputs'/'order-2717-2610A-20261021'
outdir.mkdir(parents=True, exist_ok=True)
result = outdir/(meta['name']+'.xlsx')
assert not result.exists()
changes = []
with zipfile.ZipFile(backup) as a, zipfile.ZipFile(candidate) as b:
    print('原紙/候補ZIP要素数',len(a.namelist()),len(b.namelist()))
    print('候補で失われる原紙要素',sorted(set(a.namelist())-set(b.namelist())))
    sa,sb = strings(a),strings(b)
    ca = {c.get('r'):c for c in ET.fromstring(a.read('xl/worksheets/sheet1.xml')).findall('.//s:c',ns)}
    cb = {c.get('r'):c for c in ET.fromstring(b.read('xl/worksheets/sheet1.xml')).findall('.//s:c',ns)}
    for addr,value in expected.items(): assert text_of(cb[addr],sb)==value
    # 専用ツールで生成した2セルの値だけを反映し、原紙の全印刷設定・拡張入力規則等は保持する。
    with zipfile.ZipFile(result,'x') as z:
        for info in a.infolist():
            raw = a.read(info.filename)
            if info.filename=='xl/worksheets/sheet1.xml':
                xml=raw.decode('utf-8')
                for addr,value in expected.items():
                    pattern=r'(<c\b[^>]*\br="'+addr+r'"[^>]*>).*?</c>'
                    def replace(m):
                        head=re.sub(r'\s+t="[^"]*"','',m.group(1))
                        return head[:-1]+' t="inlineStr"><is><t>'+escape(value)+'</t></is></c>'
                    xml,n=re.subn(pattern,replace,xml,count=1,flags=re.S)
                    assert n==1
                raw=xml.encode('utf-8'); changes.append(info.filename)
            if info.filename=='xl/workbook.xml':
                xml=raw.decode('utf-8')
                def recalc(m):
                    tag=m.group(0)
                    for attr in ('fullCalcOnLoad','forceFullCalc'):
                        tag=re.sub(r'\s+'+attr+r'="[^"]*"','',tag)
                    return tag[:-2]+' fullCalcOnLoad="1" forceFullCalc="1"/>'
                xml,n=re.subn(r'<calcPr\b[^>]*/>',recalc,xml,count=1)
                assert n==1
                raw=xml.encode('utf-8');changes.append(info.filename)
            z.writestr(info,raw)

# セル内容/数式/書式を全シート照合。原紙の数式・入力規則等はXMLでも照合する。
with zipfile.ZipFile(backup) as a,zipfile.ZipFile(result) as z:
    assert a.namelist()==z.namelist()
    assert z.testzip() is None
    assert [n for n in a.namelist() if a.read(n)!=z.read(n)]==changes
    before=ET.fromstring(a.read('xl/worksheets/sheet1.xml'))
    after=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
    for root in [before,after]:
        for c in root.findall('.//s:c',ns):
            if c.get('r') in expected:
                c.clear()
    assert ET.tostring(before)==ET.tostring(after)
w=openpyxl.load_workbook(result,read_only=True,data_only=False)
assert w['集計表']['C3'].value==expected['C3'] and w['集計表']['C4'].value==expected['C4']
sheet_count=len(w.sheetnames)
formula_count=sum(c.data_type=='f' for s in w for row in s.iter_rows() for c in row)
w.close()
assert digest(Path(meta['book']))==meta['sha256'], '原紙が外部変更された'
base=Path(meta['source']).parent
assert not list(base.glob('2717-2610A*')), '同番号フォルダが既にある'
dest=Path(meta['destination'])
shutil.copytree(meta['source'],dest)
old=dest/Path(meta['book']).name
assert digest(old)==meta['sha256']
new=dest/result.name
assert not new.exists()
# 作業前の原紙コピーはローカルに保持済み。コピー先だけを完成版に更新して改名する。
shutil.copyfile(result,old)
old.rename(new)
assert digest(new)==digest(result)
assert digest(Path(meta['book']))==meta['sha256']
report={'folder':str(dest),'file':str(new),'cells':expected,'sheets':sheet_count,
        'formulas_preserved':formula_count,'changed_zip_entries':changes,'template_unchanged':True,
        'sha256':digest(new),'note':'数式キャッシュは原紙を維持。Excelで開いた際に全再計算する設定。図番台帳は未変更。'}
(local/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
