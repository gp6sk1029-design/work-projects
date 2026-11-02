"""関連する経費ブックだけで採番重複と同型式を確認する。"""
from pathlib import Path
import openpyxl,sys
sys.stdout.reconfigure(encoding='utf-8')
root=Path(r'\\nas-ime5\生産技術部\1.注文書\A【経費】 10万円以下 修理部品 消耗部品 等')
for name in ('A【注文書】F 福西電機 2026.xlsx','A【注文書】F 電気部材 2026.xlsx'):
 w=openpyxl.load_workbook(root/name,read_only=True,data_only=False)
 hits=[]
 for s in w:
  for row in s:
   for c in row:
    if c.value is not None and any(x in str(c.value).upper() for x in ('AFPG804','AF-K261030-')):hits.append((s.title,c.coordinate,str(c.value)))
 print(name,'HITS',hits)
 w.close()
