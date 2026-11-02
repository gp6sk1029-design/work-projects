"""型変換・ビット演算の該当ページを読み取り専用で探す。"""
from pypdf import PdfReader
import re
import sys
sys.stdout.reconfigure(encoding='utf8')
r=PdfReader(r'C:\Program Files (x86)\OMRON\Sysmac Studio\Manual\NJ_NXシリーズ コマンドリファレンスマニュアル 基本編.pdf')
print('PAGES',len(r.pages))
terms=['LREAL_TO_DINT','DINT_TO_DWORD','TestABit','Trunc','SHL','データ型の変換']
counts={t:0 for t in terms}
for n,p in enumerate(r.pages,1):
    text=p.extract_text() or ''
    for t in terms:
        if t in text and counts[t]<5:
            lines=[l for l in text.splitlines() if t in l]
            print('MATCH',n,t,' / '.join(lines[:3]))
            counts[t]+=1
    if all(v>=5 for v in counts.values()):break
