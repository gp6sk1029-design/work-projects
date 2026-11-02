"""追加位置と複製元の条件だけを表示する。"""
from pathlib import Path
import json, re, sys
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).resolve().parent
d=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
rows=json.loads((b/'rcon_rows.json').read_text(encoding='utf-8'))
for i,r in enumerate(rows[203:],203):
 print('ROW',i,r.get('CMT','').replace('\r\n',' / '),json.dumps(r,ensure_ascii=False)[:150] if i>=243 else '')
for n,t in d['texts'].items():
 if not t.startswith('[SLWD'):continue
 print('TABLE',n)
 for l in t.splitlines():
  if re.search(r'\bN=RCON[12]_[1-6]_',l):
   if '+GN=VAR_GLOBAL' in t or 'N=RCON1_6_T' in l: print(l[:550])
print('CORE_ST',[(i,[c.get('TXT','')[:200] for c in r['CLs'] if c.get('__type')=='IST']) for i,r in enumerate(rows) if i>242])
