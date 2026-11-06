"""バックアップからセル単位で再作成し、元セル全件の保持を確認する。"""
from pathlib import Path
import copy
import hashlib
import json
import zipfile
from lxml import etree as E

base=Path(__file__).resolve().parent
backup=base/'編集前バックアップ.xlsx'
out=base.parent.parent/'outputs/encoder-360-20261102/1029_1332エンコーダ基準_修正版.xlsx'
info=json.loads((base/'inspection.json').read_text(encoding='utf-8'))
assert hashlib.sha256(backup.read_bytes()).hexdigest()==info['sha256']
source=next(s for s in info['sheets'] if s['name']=='Sheet1')
source_rows=[x for x in source['E_all'] if x['row']>=14]
authored=json.loads((base/'authored-values.json').read_text(encoding='utf-8'))['values']
assert len(source_rows)==len(authored)==360
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
q=lambda name:'{'+ns['m']+'}'+name
parser=E.XMLParser(remove_blank_text=False,resolve_entities=False,no_network=True)
with zipfile.ZipFile(backup) as z:
    infos=z.infolist();original={i.filename:z.read(i) for i in infos};comment=z.comment
result=dict(original)
path='xl/worksheets/sheet8.xml'
root=E.fromstring(original[path],parser)
old=copy.deepcopy(root)
data=root.find(q('sheetData'))
rows={int(r.get('r')):r for r in data}
cells={c.get('r'):c for c in root.iter(q('c'))}
style=cells['G5'].get('s','0')
def colnumber(address):
    n=0
    for c in address:
        if not c.isalpha():break
        n=n*26+ord(c.upper())-64
    return n
for i,item in enumerate(source_rows):
    rownum=i+5;address=f'G{rownum}'
    assert item['row']==i*10+14 and item['D']==i+1
    assert abs(item['cached']-authored[i])<1e-9
    row=rows[rownum]
    cell=cells.get(address)
    if cell is None:
        cell=E.Element(q('c'),r=address)
        index=next((j for j,c in enumerate(row) if colnumber(c.get('r',''))>7),len(row))
        row.insert(index,cell)
    # 操作するのは指定したGセルの属性と子要素のみ。
    cell.attrib.clear();cell.set('r',address);cell.set('s',style)
    for child in list(cell):cell.remove(child)
    E.SubElement(cell,q('f')).text=f'E{item["row"]}'
    value=item['cached']
    E.SubElement(cell,q('v')).text=str(int(value)) if value==int(value) else repr(value)
result[path]=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)

# 計算順の手修正はせず、任意の計算チェーンを外してExcelに再構築させる。
result.pop('xl/calcChain.xml',None)
rels_path='xl/_rels/workbook.xml.rels'
rels=E.fromstring(original[rels_path],parser)
for node in list(rels):
    if node.get('Type','').endswith('/calcChain'):rels.remove(node)
result[rels_path]=E.tostring(rels,encoding='UTF-8',xml_declaration=True,standalone=True)
ct_path='[Content_Types].xml'
ct=E.fromstring(original[ct_path],parser)
for node in list(ct):
    if node.get('PartName')=='/xl/calcChain.xml':ct.remove(node)
result[ct_path]=E.tostring(ct,encoding='UTF-8',xml_declaration=True,standalone=True)
workbook=E.fromstring(original['xl/workbook.xml'],parser)
calc=workbook.find(q('calcPr'))
if calc is not None:
    calc.set('fullCalcOnLoad','1');calc.set('forceFullCalc','1')
result['xl/workbook.xml']=E.tostring(workbook,encoding='UTF-8',xml_declaration=True,standalone=True)

def sig(node):
    return (node.tag,tuple(sorted(node.attrib.items())),node.text,tuple(sig(c) for c in node))
oldcells={c.get('r'):c for c in old.iter(q('c'))}
newcells={c.get('r'):c for c in root.iter(q('c'))}
targets={f'G{i}' for i in range(5,365)}
assert set(oldcells).issubset(newcells),'元セルが欠落'
for address,cell in oldcells.items():
    if address not in targets:assert sig(cell)==sig(newcells[address]),address
for row in data:
    seen=[]
    for cell in row:
        addr=cell.get('r')
        assert int(''.join(filter(str.isdigit,addr)))==int(row.get('r')),(row.get('r'),addr)
        seen.append(colnumber(addr))
    assert seen==sorted(set(seen)),row.get('r')
for i,item in enumerate(source_rows):
    cell=newcells[f'G{i+5}']
    assert cell.find(q('f')).text==f'E{item["row"]}'
    assert float(cell.find(q('v')).text)==item['cached']
out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w') as z:
    z.comment=comment
    for item in infos:
        if item.filename in result:z.writestr(item,result[item.filename])
with zipfile.ZipFile(out) as z:assert z.testzip() is None
verification={'output':str(out),'backup_cells':len(oldcells),'fixed_cells':len(newcells),'missing_original_cells':0,'unchanged_original_cells_outside_G5_G364':len(oldcells)-len(set(oldcells)&targets),'row_addresses_and_column_order_valid':True,'G_values_verified':360,'restored_previous_missing_cells':36,'calc_chain_removed_for_native_rebuild':True,'before_native_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'desktop_original_untouched':True}
(base/'repair_pre_native_verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(verification,ensure_ascii=False))
