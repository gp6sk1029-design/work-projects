import hashlib,json,shutil,sys
from pathlib import Path
from datetime import datetime
from openpyxl.utils.datetime import to_excel
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
d=Path(r'\\nas-ime5\生産技術部\1.注文書\_内作設備\_1.製作中注文書\2717-2610A インナー巻線機 (AIW-1100T) 〈2台〉【マーレOH】')
assert not list(d.glob('~$*')),'Excelが開かれています'
p=next(d.glob('*.xlsx')); local=Path(__file__).parent
assert not (local/'before.xlsx').exists()
shutil.copy2(p,local/'before.xlsx')
w=openpyxl.load_workbook(local/'before.xlsx',read_only=True,data_only=False)
assert w['発注先']['M6'].value=='株式会社テクノ'
s=w['巻線']
assert all(s[f'{c}{r}'].value is None for r in [16,17] for c in 'BCDEF')
updates={'B4':'株式会社テクノ','G3':to_excel(datetime(2026,10,21)),'C11':'生産技術部 幸田宛て',
 'B16':'SLM-8000','C16':'ワンボードモーションコントローラ一式','D16':'テクノ','E16':2,'F16':355000,
 'C17':'送料','E17':1,'F17':2000}
for sh in w:
 if sh.title=='発注先':continue
 for row in sh.iter_rows():
  for c in row:
   assert c.value not in ('SLM-8000','SLM8000'), '既存登録あり'
w.close()
m={'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'updates':updates,'total':712000}
(local/'manifest.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print('バックアップ完了：現行ファイルから作成、スガテクノ他ページを保持')
