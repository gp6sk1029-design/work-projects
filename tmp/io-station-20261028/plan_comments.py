"""コメント追記対象と除外対象を分類する。プロジェクト自体には書き込まない。"""
from pathlib import Path
import collections,json,re,sys
from station_rules import update,station
import xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
d=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
groups=collections.Counter();changed=[];excluded=[]
for p in d['io']:
    new=update(p['Com'])
    if new!=p['Com']:
        groups[station(p['Com'])]+=1
        changed.append({'name':p['N'],'old':p['Com'],'new':new,'physical':bool(p.get('AT'))})
    elif p.get('AT') and not re.search(r'ST\d',p['Com']):excluded.append({'name':p['N'],'comment':p['Com']})
(BASE/'comment_plan.json').write_text(json.dumps({'groups':dict(groups),'changes':changed,'physical_excluded':excluded},ensure_ascii=False,indent=2),encoding='utf-8')
print('GROUPS',dict(groups),'GLOBALS',len(changed),'PHYSICAL',sum(x['physical'] for x in changed),'EXCLUDED',len(excluded))
print('変更例')
for x in changed[:14]:print(x['new'])
print('除外対象')
for x in excluded:print(x['comment'])
comment_values=[]
for n,t in d['texts'].items():
    if t.lstrip().startswith('{') and n in d['ladder_counts']:
        comment_values.extend((n,json.loads(l).get('CMT','')) for l in t.splitlines() if l.strip())
    elif t.lstrip().startswith('<'):
        try:root=ET.fromstring(t)
        except ET.ParseError:continue
        for e in root.iter():
            comment_values.extend((n,v) for k,v in e.attrib.items() if k.rsplit('}',1)[-1] in ('Comment','Com','CMT'))
    elif t.startswith('[SLWD'):
        for p in d['tables'][n]:comment_values.append((n,p.get('Com','')))
missing_sides=sorted({c for n,c in comment_values if re.search(r'【[XY][0-9A-F]+】',c) and not re.search(r'[AB]\([左右]側\)|ST\d',c) and re.search(r'供給スライド|供給ピック|供給チャック|高さ検査|NG[12]|ストック|反転[12]|位置[0-7]ストッパー|ワーク位置',c)})
print('機器特定済みだが側表記なし',len(missing_sides))
for c in missing_sides[:15]:print(c)
