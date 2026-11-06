"""入力セルと計算順だけを限定反映し、既存グラフや元データを保持する。"""
raise SystemExit('使用禁止：セル置換の正規表現に破損原因あり。repair_encoder.pyとaudit_repair.pyを参照。')
from pathlib import Path
import hashlib
import json
import posixpath
import re
import shutil
import zipfile
import xml.etree.ElementTree as E
import openpyxl

base=Path(__file__).resolve().parent
info=json.loads((base/'inspection.json').read_text(encoding='utf-8'))
src=Path(info['source'])
backup=base/'編集前バックアップ.xlsx'
out=base.parent.parent/'outputs/encoder-360-20261102'/src.name
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(src)==sha(backup)==info['sha256'],'原本が更新されたため停止'
assert not src.with_name('~$'+src.name).exists(),'Excelが開いているため停止'
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
q=lambda x:'{'+ns['m']+'}'+x
target=next(s for s in info['sheets'] if s['name']=='Sheet1')
source_rows=[x for x in target['E_all'] if x['row']>=14]
assert len(source_rows)==360
authored_values=json.loads((base/'authored-values.json').read_text(encoding='utf-8'))['values']
with zipfile.ZipFile(backup) as z:
    infos=z.infolist();original={i.filename:z.read(i) for i in infos};comment=z.comment
    wb=E.fromstring(original['xl/workbook.xml'])
    sheet=next(x for x in wb.find('m:sheets',ns) if x.get('name')=='Sheet1')
    rid=sheet.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
    path=next(x.get('Target') for x in E.fromstring(original['xl/_rels/workbook.xml.rels']) if x.get('Id')==rid)
    path=path.lstrip('/') if path.startswith('/') else posixpath.normpath('xl/'+path)
result=dict(original)
xml=original[path].decode('utf-8')
style=E.fromstring(original[path]).find(".//m:c[@r='G5']",ns).get('s','0')
checks=[]
for i,item in enumerate(source_rows):
    addr=f'G{i+5}';formula=f'E{item["row"]}';value=item['cached']
    assert item['D']==i+1 and item['row']==14+i*10
    assert isinstance(value,(int,float)) and abs(value-authored_values[i])<1e-9
    value_text=str(int(value)) if value==int(value) else repr(value)
    new=f'<c r="{addr}" s="{style}"><f>{formula}</f><v>{value_text}</v></c>'
    pat=re.compile(r'<c\b(?=[^>]*\br="'+addr+r'")[^>]*(?:/>|>.*?</c>)',re.S)
    matches=list(pat.finditer(xml))
    if matches:
        assert len(matches)==1
        m=matches[0];xml=xml[:m.start()]+new+xml[m.end():]
    else:
        rp=re.compile(r'<row\b(?=[^>]*\br="'+str(i+5)+r'")[^>]*>.*?</row>',re.S)
        rm=rp.search(xml);assert rm is not None,addr
        raw=rm.group()
        next_cell=re.search(r'<c\b[^>]*\br="([H-Z]|[A-Z]{2,})\d+"',raw)
        insert=next_cell.start() if next_cell else raw.rfind('</row>')
        raw=raw[:insert]+new+raw[insert:]
        xml=xml[:rm.start()]+raw+xml[rm.end():]
    checks.append({'number':i+1,'source':formula,'target':addr,'value':value})
result[path]=xml.encode('utf-8')
# 元の数式の計算順を保持し、新しい参照式だけを計算順の末尾へ追加する。
chain_path='xl/calcChain.xml'
chain=E.fromstring(original[chain_path])
current=None;registered=set()
for c in chain:
    if c.get('i') is not None:current=c.get('i')
    if current==sheet.get('sheetId'):registered.add(c.get('r'))
missing=[x['target'] for x in checks if x['target'] not in registered]
raw=original[chain_path].decode('utf-8')
addition=''.join(f'<c r="{addr}" i="{sheet.get("sheetId")}"/>' for addr in missing)
raw=raw.replace('</calcChain>',addition+'</calcChain>')
result[chain_path]=raw.encode('utf-8')
out.parent.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out,'w') as z:
    z.comment=comment
    for item in infos:z.writestr(item,result[item.filename])
with zipfile.ZipFile(out) as z:
    assert z.testzip() is None
    changed=[p for p in original if original[p]!=z.read(p)]
    assert set(changed)=={path,chain_path}
    # G5:G364を除く元シートのXMLが完全に不変であることを確認。
    remove=re.compile(r'<c\b(?=[^>]*\br="G(?:[5-9]|[1-9]\d|[12]\d\d|3[0-5]\d|36[0-4])")[^>]*(?:/>|>.*?</c>)',re.S)
    assert remove.sub('',original[path].decode('utf-8'))==remove.sub('',z.read(path).decode('utf-8'))
final_f=openpyxl.load_workbook(out,data_only=False)
final_v=openpyxl.load_workbook(out,data_only=True)
old_v=openpyxl.load_workbook(backup,data_only=True)
assert final_f.sheetnames==old_v.sheetnames
ws=final_f['Sheet1'];values=final_v['Sheet1']
for check in checks:
    assert ws[check['target']].value=='='+check['source']
    assert values[check['target']].value==check['value']
    assert old_v['Sheet1'][check['source']].value==check['value']
    assert values[f'F{check["number"]+4}'].value==check['number']
assert values['G4'].value==old_v['Sheet1']['G4'].value==0
verification={'source':str(src),'output':str(out),'backup':str(backup),'count':360,'target_range':'Sheet1!G5:G364','source_range':'Sheet1!E14,E24,...,E3604','zero_degree_G4_preserved':True,'all_values_match':True,'all_numbers_in_order':True,'changed_zip_entries':changed,'all_other_entries_byte_identical':True,'all_sheet_names_preserved':final_f.sheetnames,'calc_chain_added':len(missing),'before_sha256':info['sha256'],'after_sha256':sha(out),'native_excel_opened':False,'first':checks[:3],'last':checks[-3:]}
(base/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
(base/'all_360_checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
assert sha(src)==info['sha256'],'保存直前に原本が変わったため停止'
assert not src.with_name('~$'+src.name).exists(),'保存直前にExcelで開かれたため停止'
shutil.copy2(out,src)
assert sha(src)==sha(out)
print(json.dumps(verification,ensure_ascii=False))
