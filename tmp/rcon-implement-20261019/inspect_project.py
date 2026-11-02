from pathlib import Path
import zipfile,xml.etree.ElementTree as ET,re,json,sys
sys.stdout.reconfigure(encoding='utf-8')
p=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261019A.smc2')
with zipfile.ZipFile(p) as z:
    texts={}
    for n in z.namelist():
        try:t=z.read(n).decode('utf-8-sig')
        except UnicodeError:continue
        if '\x00' not in t:texts[n]=t
    oemname=next(n for n in texts if n.endswith('.oem'))
    root=ET.fromstring(texts[oemname])
    parents={c:p for p in root.iter() for c in p}
    for e in root.iter('Entity'):
        if any(k in str(e.attrib) for k in ['RCON_IAI','OtherDevice_外部機器']):
            print('TARGET ENTITY',ET.tostring(e,encoding='unicode')[:16000])
            print('PARENT',ET.tostring(parents[e],encoding='unicode')[:18000])
            for d in e.iter('Entity'):
                n=next((n for n in texts if n.endswith('/'+d.get('id','-')+'.xml')),None)
                if n:print('TARGET FILE',n,repr(texts[n][:14000]))
    slwd={n:t for n,t in texts.items() if t.startswith('[SLWD')}
    for n,t in slwd.items():
        if '+GN=VAR_GLOBAL' in t:
            lines=[s for s in t.splitlines() if any(k in s for k in ['RCON1_','RCON2_','E005_','E001_'])]
            print('GLOBALS',n,'MATCHES',len(lines))
            print('\n'.join(lines[:12]+lines[-18:]))
        elif any('ST' in s for s in []):pass
    # ST本文・ローカル変数の既存例を特定する。
    st=[e for e in root.iter('Entity') if e.get('type')=='PouBody' and e.get('subtype') not in ['LdBody']]
    print('BODY TYPES',[(e.attrib) for e in st][:45])
    found=0
    for e in root.iter('Entity'):
        if e.get('type')!='PouBody':continue
        n=next((n for n in texts if n.endswith('/'+e.get('id','-')+'.xml')),None)
        if n and not texts[n].lstrip().startswith(('{','<','[SLWD')):
            print('ST SAMPLE ENTITY',e.attrib,'PARENT',parents[e].attrib,'FILE',n,'TEXT',repr(texts[n][:3000]))
            found+=1
            if found>=3:break
    print('SLWD HEADERS',[(n,t[:120]) for n,t in slwd.items()][:12])
    print('MANIFEST',next(t for n,t in texts.items() if n.endswith('.manifest'))[:2500])
    data={'oem':oemname,'texts':texts,'entries':z.namelist()}
    (Path(__file__).parent/'inspection.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
