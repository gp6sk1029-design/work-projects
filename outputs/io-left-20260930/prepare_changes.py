import json,re,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).parent
d=json.loads((base/'source_cells.json').read_text(encoding='utf-8'))['IO']['cells']
changes=[]
pairs=[]
def convert(s):
    s=s.replace('右','左').replace('ミギ','ヒダリ').replace('ﾐｷﾞ','ﾋﾀﾞﾘ')
    return re.sub(r'(?<![A-Za-z0-9])R(?![A-Za-z0-9])','L',s)
def pair(src,dst,wire=None,kind='名称'):
    old=d.get(dst,'')
    right=d.get(src,'')
    if not right: return
    after=convert(right)
    if kind=='コメント':
        after=re.sub(r'^【[XY]\d+】','',after)
        if '左' in old and '左' not in after and 'ストッパー' in after:
            after=after.replace('ストッパー','左ストッパー')
        if wire:
            assert d[wire].isdigit(),(dst,wire,d.get(wire))
            after='【'+('X' if int(re.search(r'\d+',dst).group())<30 else 'Y')+d[wire]+'】'+after
    pairs.append({'source':src,'target':dst,'kind':kind,'expected':after})
    if after!=old: changes.append({'source':src,'target':dst,'kind':kind,'before':old,'after':after})
rows_in=list(range(7,15))+list(range(16,24))
rows_out=list(range(33,41))+list(range(43,51))
for r in rows_in:
    for c1,c2,w in [('R','AR','AT'),('Y','AY','AW'),('AE','BE','BG'),('AL','BL','BJ')]:
        pair(c1+str(r),c2+str(r),w+str(r),'コメント')
    for c1,c2 in [('S','AS'),('X','AX'),('AF','BF'),('AK','BK')]:
        pair(c1+str(r),c2+str(r))
for r in rows_out:
    for c1,c2,w in [('R','AE','AG'),('Y','AL','AJ')]:
        pair(c1+str(r),c2+str(r),w+str(r),'コメント')
    for c1,c2 in [('S','AF'),('X','AK')]: pair(c1+str(r),c2+str(r))
# 同じユニット内に右左の端子が並ぶ設備
for right,left in [(16,18),(17,19)]:
    pair('L'+str(right),'L'+str(left),'J'+str(left),'コメント')
    pair('K'+str(right),'K'+str(left))
for right,left in [(33,39),(34,40),(35,43),(36,44),(37,45),(38,46)]:
    pair('L'+str(right),'L'+str(left),'J'+str(left),'コメント')
    pair('K'+str(right),'K'+str(left))
for right,left in [(45,48),(46,49),(47,50)]:
    pair('E'+str(right),'E'+str(left),'G'+str(left),'コメント')
    pair('F'+str(right),'F'+str(left))
for right,left in [(7,8),(9,10),(11,13),(12,14)]:
    pair('CD'+str(right),'CD'+str(left),kind='コメント')
    pair('CE'+str(right),'CE'+str(left))
for right,left in [(33,35),(34,36)]:
    pair('BE'+str(right),'BE'+str(left),'BG'+str(left),'コメント')
    pair('BF'+str(right),'BF'+str(left))
assert len({c['target'] for c in changes})==len(changes)
(base/'changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2),encoding='utf-8')
(base/'pairs.json').write_text(json.dumps(pairs,ensure_ascii=False,indent=2),encoding='utf-8')
print('対応セル:',len(pairs),'変更セル:',len(changes),'コメント:',sum(c['kind']=='コメント' for c in changes),'名称:',sum(c['kind']=='名称' for c in changes))
for c in changes: print(c['source'],'→',c['target'],repr(c['before']),'→',repr(c['after']))
