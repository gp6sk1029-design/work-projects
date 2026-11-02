"""成果物を読み取り専用で再確認し、検証用プレビューの一覧画像を作る。"""
from pathlib import Path
from collections import Counter
import json
import re
import xml.etree.ElementTree as ET
from openpyxl import load_workbook
from PIL import Image, ImageOps, ImageDraw

work=Path(r'C:\Users\SEIGI-N13\work-projects\tmp\rcon-bible-20261017')
manifest=json.loads((work/'manifest.json').read_text(encoding='utf8'))
path=Path(manifest['output'])
wb=load_workbook(path,data_only=False,read_only=True)
cache=load_workbook(path,data_only=True,read_only=True)
assert len(wb.sheetnames)==9
assert cache['登録ガイド']['B28'].value==56
assert cache['登録ガイド']['B29'].value==112
root=ET.parse(path.parent/'取説'/'ESI_IAI_Gateway_ECT_V_1_08_Rev_0.xml').getroot()
device=next(d for d in root.findall('.//Device') if d.findtext('Type')=='RCGW-ECT(112Byte/112Byte)')
assert device.find('Type').get('ProductCode')=='#x00A47070'
all_names=[]
for direction,pdo,index in [('OUT','RxPdo','2003'),('IN','TxPdo','2004')]:
    rows=list(wb[direction+'_IO'].iter_rows(min_row=2,max_row=57,min_col=1,max_col=9,values_only=True))
    entries=device.findall('.//'+pdo+'/Entry')
    assert len(rows)==len(entries)==56
    assert [list(r) for r in rows]==manifest['io'][direction]
    for n,(r,e) in enumerate(zip(rows,entries)):
        assert r[2]==e.findtext('Name')==direction+str(n).zfill(2)
        assert r[3]==e.findtext('DataType')=='UINT'
        assert e.findtext('BitLen')=='16'
        assert e.findtext('Index').lower()=='#x'+index
        assert r[8]==index+':'+format(int(e.findtext('SubIndex')),'02X')
        assert re.fullmatch(r'RCON1_'+direction+r'_[A-Za-z0-9_]+',r[0])
        assert len(r[0])<=127
        if n>=8:
            a=(n-8)//8+1
            assert r[5]==a-1 and f'_Axis{a}_' in r[0]
        all_names.append(r[0])
assert len(all_names)==len(set(all_names))==112
types={}
known={'BOOL','LREAL','DINT','UINT'}
for d in manifest['defs']:
    block=manifest['blockRows'][d['name']]
    rows=list(wb[block['sheet']].iter_rows(min_row=block['start'],max_row=block['end'],min_col=1,max_col=6,values_only=True))
    assert len(rows)==len(d['members'])
    types[d['name']]={}
    for row,m in zip(rows,d['members']):
        assert row[0]==m['name'] and row[1]==m['type'] and row[2]
        assert row[1] in known
        assert row[0] not in types[d['name']]
        types[d['name']][row[0]]=row[1]
    known.add(d['name'])
assert len(types)==4 and sum(map(len,types.values()))==39
def resolve(text):
    m=re.fullmatch(r'RCON1_(OUT|IN)\[([1-6])\]\.(.+)',text)
    assert m,text
    t='ST_RCON_Direct_'+m[1]+'_Axis'
    for member in m[3].split('.'):
        assert member in types[t],text
        t=types[t][member]
    return t
for direction in ('OUT','IN'):
    for row in manifest['io'][direction][8:]:
        if row[6]!='-':resolve(row[6])
for row in wb['組合せ例・型選び'].iter_rows(min_row=7,max_row=15,min_col=2,max_col=3,values_only=True):
    assert resolve(row[0])==row[1]
assert set(m['bit'] for m in manifest['defs'][0]['members'])==set(range(16))-{9}
assert set(m['bit'] for m in manifest['defs'][1]['members'])==set(range(16))-{6,9,10,11}
learn=cache['解説_単位と上下ワード']
for addr,val in {'E6':2540,'E7':2540,'E8':2540,'E9':0,'E10':2540,'E11':2540,'E12':25.4,'E15':10,'E16':200,'E17':0.1,'E18':20,'E19':127,'E30':16,'E31':0,'E32':16}.items():
    assert learn[addr].value==val,(addr,learn[addr].value,val)
for row,expected in [(23,(2540,2540,0)),(24,(70025,4489,1)),(25,(-2540,62996,65535)),(26,(0,0,0))]:
    assert tuple(learn[f'{c}{row}'].value for c in 'CEF')==expected
assert wb['解説_単位と上下ワード']['B6'].value==25.4
assert wb['解説_単位と上下ワード']['B17'].value==0.1
assert wb['解説_単位と上下ワード']['B31'].value is False
assert len(load_workbook(path,read_only=False).get_sheet_by_name('解説_単位と上下ワード').data_validations.dataValidation)==1
errors=[]
for sheet in cache:
    for row in sheet:
        for cell in row:
            if cell.data_type=='e':errors.append((sheet.title,cell.coordinate,cell.value))
assert not errors,errors
# プレビューを四枚ずつ一覧化。元の高解像度PNGも残す。
files=[work/'previews'/f'{name}.png' for _,_,name in manifest['views']]
for group in range(0,len(files),4):
    cards=[]
    for p in files[group:group+4]:
        im=Image.open(p).convert('RGB')
        im.thumbnail((1050,1100))
        card=Image.new('RGB',(1090,1160),'#E8EDF3')
        ImageDraw.Draw(card).text((15,12),p.stem,fill='black')
        card.paste(im,(20,42))
        cards.append(card)
    page=Image.new('RGB',(2180,2320),'white')
    for i,im in enumerate(cards):page.paste(im,((i%2)*1090,(i//2)*1160))
    page.save(work/'previews'/f'contact-{group//4+1}.png')
print(json.dumps({'file':str(path),'bytes':path.stat().st_size,'sheets':wb.sheetnames,'structures':4,'members':39,'esiPortsMatched':112,'rawNamesUnique':True,'referencePathsValid':True,'formulaCachesChecked':True,'negativePositionChecked':True,'reservedBitsChecked':True,'formulaErrors':errors},ensure_ascii=False))
