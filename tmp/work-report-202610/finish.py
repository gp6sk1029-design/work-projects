"""検算済みの値だけを元構造へ限定反映し、全日を照合してから保存する。"""
from pathlib import Path
import sys
sys.path=[p for p in sys.path if Path(p or '.').resolve()!=Path(__file__).parent.resolve()]
import hashlib
import html
import json
import re
import shutil
import zipfile
import xml.etree.ElementTree as E
import openpyxl
from openpyxl.utils.cell import range_boundaries, get_column_letter

base=Path(__file__).parent.resolve()
src=Path(r'C:\Users\SEIGI-N13\Desktop\【業務報告2026 Ver2.7】幸田.xlsx')
backup=base/'backup'/'【業務報告2026 Ver2.7】幸田_編集前.xlsx'
out=base.parent.parent/'outputs'/'work-report-202610'/src.name
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert digest(src)==digest(backup),'作業中に原本が更新されたため停止'
assert not src.with_name('~$'+src.name).exists(),'対象ブックが開かれているため停止'
old_values=openpyxl.load_workbook(backup,data_only=True)
old_formulas=openpyxl.load_workbook(backup,data_only=False)
authored=openpyxl.load_workbook(base/'artifact-edited.xlsx',data_only=True)
diffs=json.loads((base/'value_differences.json').read_text(encoding='utf-8'))
assert len(diffs)==18
assert {(d['sheet'],d['cell']) for d in diffs if d['sheet']=='10月' and not old_formulas['10月'][d['cell']].data_type=='f'}=={('10月','T8'),('10月','T16')}
assert authored['10月']['AK8'].value==196
assert authored['10月']['AK10'].value==28
assert authored['10月']['AK16'].value==0
assert authored['10月']['AK17'].value==224
assert authored['10月']['AK38'].value==224

with zipfile.ZipFile(backup) as z:
    infos=z.infolist();original={i.filename:z.read(i) for i in infos};comment=z.comment
result=dict(original)
paths={'年間集計':'xl/worksheets/sheet1.xml','10月':'xl/worksheets/sheet8.xml'}
def valtext(x):
    assert isinstance(x,(int,float))
    return str(int(x)) if x==int(x) else repr(x)

# 数式本文・共有式属性・セル書式は一字も変更せず、数値部分だけ更新する。
for title,path in paths.items():
    xml=original[path].decode('utf-8')
    for d in (d for d in diffs if d['sheet']==title):
        addr=d['cell'];new=d['after']
        assert authored[title][addr].value==new
        pat=re.compile(r'<c\b(?=[^>]*\br="'+re.escape(addr)+r'")[^>]*(?:/>|>.*?</c>)',re.S)
        matches=list(pat.finditer(xml));assert len(matches)==1,addr
        raw=matches[0].group()
        assert re.search(r'<v>[^<]*</v>',raw),addr
        changed=re.sub(r'<v>[^<]*</v>','<v>'+valtext(new)+'</v>',raw,count=1)
        xml=xml[:matches[0].start()]+changed+xml[matches[0].end():]
    result[path]=xml.encode('utf-8')

# 年間と10月の円グラフも、参照式を保持して数値キャッシュだけ更新する。
chart_changes=[]
for path in ('xl/charts/chart1.xml','xl/charts/chart15.xml'):
    text=original[path].decode('utf-8')
    def update_numref(match):
        fragment=match.group()
        f=re.search(r'<(?:\w+:)?f>(.*?)</(?:\w+:)?f>',fragment,re.S)
        if f is None:return fragment
        formula=html.unescape(f.group(1))
        tab,rng=formula.rsplit('!',1);tab=tab.strip("'").replace("''", "'")
        c1,r1,c2,r2=range_boundaries(rng)
        addresses=[f'{get_column_letter(c)}{r}' for r in range(r1,r2+1) for c in range(c1,c2+1)]
        def update_point(pm):
            raw=pm.group();idx=int(re.search(r'\bidx="(\d+)"',raw).group(1))
            addr=addresses[idx];value=authored[tab][addr].value
            if old_values[tab][addr].value==value:return raw
            chart_changes.append({'chart':path,'sheet':tab,'cell':addr,'value':value})
            return re.sub(r'(<(?:\w+:)?v>)[^<]*(</(?:\w+:)?v>)',lambda vm:vm[1]+valtext(value)+vm[2],raw,count=1)
        return re.sub(r'<(?:\w+:)?pt\b[^>]*>.*?</(?:\w+:)?pt>',update_point,fragment,flags=re.S)
    result[path]=re.sub(r'<(?:\w+:)?numRef>.*?</(?:\w+:)?numRef>',update_numref,text,flags=re.S).encode('utf-8')
assert len(chart_changes)==4,chart_changes
out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w') as z:
    z.comment=comment
    for info in infos:z.writestr(info,result[info.filename])
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    changed_entries=[n for n in original if original[n]!=z.read(n)]
    assert set(changed_entries)=={*paths.values(),'xl/charts/chart1.xml','xl/charts/chart15.xml'}

final_values=openpyxl.load_workbook(out,data_only=True)
final_formulas=openpyxl.load_workbook(out,data_only=False)
assert final_values.sheetnames==old_values.sheetnames
formula_total=0
for ws in old_formulas:
    nws=final_formulas[ws.title]
    for row in ws:
        for cell in row:
            other=nws[cell.coordinate]
            a=cell.value;b=other.value
            if hasattr(a,'text'):
                assert hasattr(b,'text') and vars(a)==vars(b),(ws.title,cell.coordinate)
                formula_total+=1
            elif cell.data_type=='f':
                assert a==b,(ws.title,cell.coordinate)
                formula_total+=1
            elif (ws.title,cell.coordinate) not in {('10月','T8'),('10月','T16')}:
                assert a==b,(ws.title,cell.coordinate,a,b)
            assert cell.style_id==other.style_id
expected={1:10,2:10,5:8,6:10.5,7:8,8:11,9:10,12:8,13:10,14:10.5,15:10.75,16:9.5,19:11,20:10.5,21:10.5,22:11.75,23:10,24:6,26:10.5,27:10,28:10.5,29:9,30:8}
audit=[]
ws=final_values['10月']
for day in range(1,32):
    col=get_column_letter(day+4)
    upper=sum(ws[f'{col}{r}'].value or 0 for r in range(8,17))
    lower=sum(ws[f'{col}{r}'].value or 0 for r in range(20,38))
    want=expected.get(day,0)
    assert upper==lower==want,(day,upper,lower,want)
    assert ws[f'{col}10'].value==old_values['10月'][f'{col}10'].value
    assert ws[f'{col}8'].value==want-(ws[f'{col}10'].value or 0) if want else ws[f'{col}8'].value in (None,0)
    if day==24:assert ws[f'{col}21'].value==6 and not ws[f'{col}23'].value
    else:assert (ws[f'{col}23'].value or 0)==want
    audit.append({'day':day,'new':ws[f'{col}8'].value or 0,'repair':ws[f'{col}10'].value or 0,'work_total':upper,'koto':ws[f'{col}23'].value or 0,'servo':ws[f'{col}21'].value or 0,'expected':want,'match':True})
assert ws['U7'].value==1 and ws['AI7'].value==1
assert ws['AK8'].value==196 and ws['AK10'].value==28 and ws['AK17'].value==224
assert ws['AK23'].value==218 and ws['AK21'].value==6 and ws['AK38'].value==224
assert ws['AJ3'].value.startswith('OK')
assert final_values['年間集計']['K8'].value==196 and final_values['年間集計']['K16'].value==0
verification={'source':str(src),'backup':str(backup),'output':str(out),'source_before_sha256':digest(backup),'final_sha256':digest(out),'input_changes':2,'cache_changes':16,'chart_points_updated':chart_changes,'changed_entries':changed_entries,'preserved_formulas':formula_total,'daily_audit':audit,'totals':{'new':196,'repair':28,'all':224,'koto':218,'servo':6},'status':ws['AJ3'].value,'native_excel_recalculation':False,'method':'元の数式と書式を保持。編集ツールの確認用コピーでは互換式で再計算し、別途日別加算で照合。'}
(base/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
assert digest(src)==digest(backup),'保存前に原本が更新されたため停止'
shutil.copy2(out,src)
assert digest(src)==digest(out)
print(json.dumps({k:v for k,v in verification.items() if k!='daily_audit'},ensure_ascii=False))
