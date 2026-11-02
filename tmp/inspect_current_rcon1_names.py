"""対象C版の保存済み変数名だけを読み、ST案の参照先を確認する。"""
from pathlib import Path
import xml.etree.ElementTree as ET
import re
import json
import sys
sys.stdout.reconfigure(encoding='utf8')
folder=Path(r'C:\OMRON\Data\Solution\1b1e94fa-3893-4ce1-8e74-dc8e6e24bc60')
oem=next(folder.glob('*.oem'))
root=ET.parse(oem).getroot()
g=next(e for e in root.iter('Entity') if e.get('type')=='Variables' and e.get('subtype')=='Global')
path=folder/(g.get('id')+'.xml')
t=path.read_bytes().decode('utf-8-sig')
rows=[]
for line in t.splitlines():
    if line.startswith('++D='):
        fields=dict(x.split('=',1) for x in line[2:].split('\t') if '=' in x)
        rows.append(fields)
for direction in ('Out','In'):
    hits=[x for x in rows if re.fullmatch(r'E001_'+direction+'_'+direction.upper()+r'\d{2}_200[34]_[0-9A-F]{2}',x.get('N',''))]
    print(direction,'COUNT',len(hits))
    for r in hits[:3]+hits[-2:]:print(json.dumps(r,ensure_ascii=False))
print('INTERNAL',[x for x in rows if re.fullmatch(r'RCON1_(OUT|IN|SpeedUnit_mm_s)',x.get('N',''))])
type_files=[]
for e in root.iter('Entity'):
    if e.get('type')=='DataType':
        p=folder/(e.get('id')+'.xml')
        if p.exists():
            try:r=ET.parse(p).getroot()
            except E.ParseError:continue
            ds=r.findall('.//DataType')
            names=[x.get('Name') for x in ds if x.get('BaseType')=='STRUCT']
            if any('RCON' in str(n) for n in names):print('TYPES',names)
result={'sourceProject':'20261017C（保存済みデータ）','globalPath':str(path),'variables':[x for x in rows if x.get('N','').startswith(('E001_','RCON1_'))]}
out=Path(r'C:\Users\SEIGI-N13\work-projects\tmp\rcon1_current_names.json')
out.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
