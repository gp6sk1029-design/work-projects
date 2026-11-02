"""D版のCVD EtherCAT保存情報を読取確認する。"""
from pathlib import Path
from zipfile import ZipFile
import sys,re
if '--official' in sys.argv:
    import urllib.request,io,xml.etree.ElementTree as ET
    url='https://www.orientalmotor.com/support/software/SFTWR/ORIENTALMOTOR_CVD2A-KED_rev0001.zip'
    data=urllib.request.urlopen(url,timeout=40).read()
    with ZipFile(io.BytesIO(data)) as official:
        print('公式ZIP',official.namelist())
        for n in official.namelist():
            if not n.lower().endswith('.xml'):continue
            raw=official.read(n)
            root=ET.fromstring(raw)
            print('VENDOR',ET.tostring(root.find('Vendor'),encoding='unicode'))
            for d in root.findall('.//Devices/Device'):
                print('DEVICE',ET.tostring(d.find('Type'),encoding='unicode'),[(e.attrib,e.text) for e in d.findall('Name')])
    sys.exit()
sys.stdout.reconfigure(encoding='utf-8')
p=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_2026102D.smc2')
with ZipFile(p) as z:
    for n in z.namelist():
        raw=z.read(n)
        if any(k in n for k in ('fcc69278-8d06-4c1d-baa1-fc63ebc33bac','22aaf14a-1b6b-4d6b-8ef3-92d6b44c6fa5')):
            print('NODE_PAYLOAD',n,'BYTES',len(raw),'HEAD',repr(raw[:120]))
            for enc in ('utf-8-sig','utf-16le'):
                t0=raw.decode(enc,errors='replace')
                for m in list(re.finditer(r'CVD|ProductCode|Revision|Vendor|DeviceType',t0))[:12]:print('NODE_TEXT',enc,repr(t0[max(0,m.start()-120):m.start()+250]))
        try:t=raw.decode('utf-8-sig')
        except UnicodeError:continue
        if 'CVD2' not in t:continue
        print('ENTRY',n,'SIZE',len(raw))
        for m in list(re.finditer('CVD2',t))[:8]:print(t[max(0,m.start()-350):m.start()+950])
