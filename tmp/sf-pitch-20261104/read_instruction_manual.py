"""オムロン公式命令マニュアルから型変換と乗算の該当箇所を確認する。"""
from pathlib import Path
import urllib.request,sys,json
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
p=b/'W502_公式命令マニュアル.pdf'
urls=['https://assets.omron.eu/downloads/latest/manual/en/w502_nj_nx-series_instructions_reference_manual_en.pdf']
if not p.exists():
 for url in urls:
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Mozilla/5.0'})
   with urllib.request.urlopen(req,timeout=20) as r:data=r.read()
   if data.startswith(b'%PDF'):
    p.write_bytes(data);(b/'manual_source.txt').write_text(url,encoding='utf-8');break
   print('PDF以外の応答',url,len(data))
  except Exception as e:print(type(e).__name__,str(e)[:180])
if p.exists():
 from pypdf import PdfReader
 doc=PdfReader(p);found=[]
 for i in range(min(600,len(doc.pages))):
  text=doc.pages[i].extract_text() or ''
  if ('TO_LREAL' in text or 'Mul (' in text or 'Multiplication' in text) and len(found)<40:
   found.append({'page':i,'text':text[:11000]})
 (b/'命令調査.json').write_text(json.dumps(found,ensure_ascii=False,indent=2),encoding='utf-8')
 print('PDF',len(doc.pages),'該当ページ',[(x['page'],x['text'][:70]) for x in found])
else:print('公式PDF未取得')
