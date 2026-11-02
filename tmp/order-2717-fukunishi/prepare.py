import hashlib,json,shutil,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
d=Path(r'\\nas-ime5\生産技術部\1.注文書\_内作設備\_1.製作中注文書\2717-2610A インナー巻線機 (AIW-1100T) 〈2台〉【マーレOH】')
assert not list(d.glob('~$*')), 'Excelが開かれています'
p=next(d.glob('*.xlsx'))
local=Path(__file__).parent
assert not (local/'before.xlsx').exists()
shutil.copy2(p,local/'before.xlsx')
items=[
 ['MSMF152L1G6','サーボモータ 1.5kW','パナソニック',2,103500],
 ['MDDLT55SF','サーボアンプ 1.5kW用','パナソニック',2,127600],
 ['MSMF022L1A1','サーボモータ 200W','パナソニック',4,52200],
 ['MADLT15SF','サーボアンプ 200W用','パナソニック',4,89400],
 ['MSMF042L1B1','サーボモータ 400W ブレーキ付','パナソニック',2,88200],
 ['MBDLT25SF','サーボアンプ 400W用','パナソニック',2,96500],
]
assert sum(x[3]*x[4] for x in items)==1398000
meta={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'items':items,'total':1398000}
(local/'manifest.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
print('バックアップ完了。6品目合計',meta['total'])
