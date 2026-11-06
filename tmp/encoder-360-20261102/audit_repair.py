"""元セル・数式・順序・パッケージ参照を独立して全件照合する。"""
from pathlib import Path
import json
import zipfile
from lxml import etree as E
import openpyxl

base=Path(__file__).resolve().parent
backup=base/'編集前バックアップ.xlsx'
out=base.parent.parent/'outputs/encoder-360-20261102/1029_1332エンコーダ基準_修正版.xlsx'
old=openpyxl.load_workbook(backup,data_only=False)
new=openpyxl.load_workbook(out,data_only=False)
values=openpyxl.load_workbook(out,data_only=True)
assert old.sheetnames==new.sheetnames
targets={f'G{i}' for i in range(5,365)}
count=0;formula_count=0
for ws in old:
    nw=new[ws.title]
    for row in ws:
        for cell in row:
            if ws.title=='Sheet1' and cell.coordinate in targets:continue
            a=cell.value;b=nw[cell.coordinate].value
            if hasattr(a,'text'):assert hasattr(b,'text') and vars(a)==vars(b),(ws.title,cell.coordinate)
            else:assert a==b,(ws.title,cell.coordinate,a,b)
            if cell.data_type=='f':formula_count+=1
            if a is not None:count+=1
ws=new['Sheet1'];vs=values['Sheet1']
checks=[]
for i in range(360):
    dest=f'G{i+5}';src=f'E{i*10+14}'
    assert ws[dest].value=='='+src
    assert vs[dest].value==vs[src].value,(dest,src)
    assert vs[f'F{i+5}'].value==i+1
    checks.append({'number':i+1,'source':src,'destination':dest,'value':vs[dest].value,'match':True})
q=lambda s:'{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'+s
with zipfile.ZipFile(backup) as oz,zipfile.ZipFile(out) as nz:
    assert nz.testzip() is None
    differences=[p for p in oz.namelist() if p not in nz.namelist() or oz.read(p)!=nz.read(p)]
    assert set(differences)=={'xl/worksheets/sheet8.xml','xl/calcChain.xml','xl/_rels/workbook.xml.rels','xl/workbook.xml','[Content_Types].xml'}
    for p in nz.namelist():
        if p.endswith(('.xml','.rels')):E.fromstring(nz.read(p))
    tree=E.fromstring(nz.read('xl/worksheets/sheet8.xml'))
    for row in tree.find(q('sheetData')):
        for c in row:
            assert int(''.join(filter(str.isdigit,c.get('r'))))==int(row.get('r'))
result={'file':str(out),'original_nonempty_cells_preserved_outside_target':count,'original_formulas_preserved_outside_target':formula_count,'sheet_count_including_charts':len(new.sheetnames),'missing_original_values':0,'target_count':360,'all_target_values_match':True,'all_target_numbers_in_order':True,'all_XML_parts_parse':True,'row_cell_address_mismatch':0,'changed_entries':differences,'native_excel_warning_check':'利用者の開き直し確認待ち','native_excel_verification_not_claimed':True}
(base/'repair_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(base/'repair_360_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
