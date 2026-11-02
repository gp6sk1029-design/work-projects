from pathlib import Path
from pypdf import PdfReader
import re,sys
sys.stdout.reconfigure(encoding='utf8')
p=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\資料\取説\RCONシステム_日本語取扱説明書_MJ0384-9D.pdf')
r=PdfReader(p)
for i,page in enumerate(r.pages):
 if not (i<70 or 210<i<370):continue
 t=page.extract_text() or ''
 if ('4.5' in t and ('STOP' in t or '非常停止' in t)) or ('停止入力' in t and ('B接点' in t or 'b接点' in t or '駆動源' in t)):
  print('PDF PAGE',i+1,'\n',t,'\n')
