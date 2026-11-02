"""保存済みExcel・公式ESI・貼付TSV・型定義を読み取り専用で照合する。"""
from pathlib import Path
from collections import Counter
import xml.etree.ElementTree as ET
import json
import re
from openpyxl import load_workbook

folder=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\資料\RCON_直接数値指定_6軸_IO構造体_20261017A')
path=folder/'RCON_直接数値指定_6軸_IOリスト・構造体.xlsx'
wb=load_workbook(path,read_only=True,data_only=False)
cached=load_workbook(path,read_only=True,data_only=True)
assert cached['概要と登録手順']['B8'].value==56
assert cached['概要と登録手順']['B9'].value==112
root=ET.parse(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\資料\取説\ESI_IAI_Gateway_ECT_V_1_08_Rev_0.xml').getroot()
device=next(d for d in root.findall('.//Device') if d.findtext('Type')=='RCGW-ECT(112Byte/112Byte)')
names=[]
allrows={}
for sheet,prefix,pdo,obj in [('OUT_IO','OUT','RxPdo','2003'),('IN_IO','IN','TxPdo','2004')]:
    rows=list(wb[sheet].iter_rows(min_row=2,max_row=57,min_col=1,max_col=9,values_only=True))
    entries=device.findall('.//'+pdo+'/Entry')
    assert len(entries)==len(rows)==56
    for n,(row,entry) in enumerate(zip(rows,entries)):
        assert row[2]==entry.findtext('Name')==prefix+str(n).zfill(2)
        assert row[3]==entry.findtext('DataType')=='UINT'
        assert entry.findtext('BitLen')=='16'
        assert row[8]==obj+':'+format(int(entry.findtext('SubIndex')),'02X')
        assert re.fullmatch('[A-Za-z][A-Za-z0-9_]*',row[0])
        assert len(row[0])<=127 and row[1]
        if n>=8:
            axis=(n-8)//8+1
            assert row[5]==axis-1 and f'Axis{axis}_' in row[0]
    names.extend(r[0] for r in rows)
    allrows[sheet]=rows
    tsv=(folder/(prefix+'_56ワード_貼付用.tsv')).read_text(encoding='utf-8').splitlines()
    assert [line.split('\t') for line in tsv]==[list(r[:2]) for r in rows]
assert len(names)==len(set(names))==112
expected_out=['TargetPosLoRaw','TargetPosHiRaw','PositionBandLoRaw','PositionBandHiRaw','SpeedRaw','AccDecRaw','PushLimitRaw','ControlRaw']
expected_in=['ActualPosLoRaw','ActualPosHiRaw','CurrentLoRaw','CurrentHiRaw','ActualSpeedRaw','ReservedInRaw','AlarmCodeRaw','StatusRaw']
for axis in range(1,7):
    start=8+(axis-1)*8
    for sn,fields in [('OUT_IO',expected_out),('IN_IO',expected_in)]:
        assert [r[0] for r in allrows[sn][start:start+8]]==[f'RCON1_Dir_Axis{axis}_{f}' for f in fields]
type_rows=list(wb['構造体定義'].iter_rows(min_row=2,max_row=42,min_col=1,max_col=7,values_only=True))
types={}
known={'BOOL','LREAL','DINT','UINT'}
for order,t,member,dt,comment,unit,relation in type_rows:
    assert comment and unit and relation
    assert dt in known or dt in types
    types.setdefault(t,{})
    assert member not in types[t]
    types[t][member]=dt
assert len(types)==5 and len(type_rows)==41
for rows in allrows.values():
    for row in rows[8:]:
        if row[6]=='-':
            continue
        path_parts=re.sub(r'^RCON1_DirectAxis\[[1-6]\]\.', '',row[6]).split('.')
        current='ST_RCON_DirectAxis'
        for part in path_parts:
            assert part in types[current]
            current=types[current][part]
text=(folder/'構造体定義_参考.txt').read_text(encoding='utf-8')
for t,members in types.items():
    block=re.search(r'TYPE '+t+r'\s*:\s*STRUCT(.*?)END_STRUCT;',text,re.S).group(1)
    fields=dict(re.findall(r'^\s*(\w+)\s*:\s*(\w+)\s*;',block,re.M))
    assert fields==members
bit_rows=list(wb['ビット割付'].iter_rows(min_row=2,max_row=33,min_col=1,max_col=7,values_only=True))
reserved={'OUT':{9},'IN':{6,9,10,11}}
for direction,bit,mask,signal,dt,member,comment in bit_rows:
    assert mask=='16#'+format(1<<bit,'04X')
    assert (signal=='予約')==(bit in reserved[direction])
    if signal!='予約':
        current='ST_RCON_DirectAxis'
        for part in member.split('].',1)[1].split('.'):
            assert part in types[current]
            current=types[current][part]
        assert current==dt=='BOOL'
errors=[]
for sheet in wb:
    for row in sheet:
        for cell in row:
            if cell.data_type=='e': errors.append((sheet.title,cell.coordinate,cell.value))
assert not errors
assert wb['変数と単位']['B2'].value=='ARRAY[1..6] OF ST_RCON_DirectAxis'
print(json.dumps({'sheets':wb.sheetnames,'ioWordsPerDirection':56,'bytesPerDirection':112,'uniqueRawNames':112,'structures':len(types),'members':len(type_rows),'memberTypes':dict(Counter(r[3] for r in type_rows)),'esiMatch':True,'tsvMatch':True,'definitionTextMatch':True,'structReferencesValid':True,'bitMasksValid':True,'formulaErrors':errors},ensure_ascii=False))
