"""メーカー取説のPDO関連ページを読み取り専用で確認する。"""
import argparse
import re
import sys
from pypdf import PdfReader
sys.stdout.reconfigure(encoding='utf-8')
p=argparse.ArgumentParser()
p.add_argument('path')
p.add_argument('--pages')
a=p.parse_args()
r=PdfReader(a.path)
if a.pages:
    for n in map(int,a.pages.split(',')):
        print(f'===== PDF PAGE {n} =====')
        print(r.pages[n-1].extract_text())
else:
    for n,page in enumerate(r.pages,1):
        t=page.extract_text()
        if re.search(r'6077|60FE|60FD|6081|60F4',t):
            lines=[line for line in t.splitlines() if re.search(r'6077|60FE|60FD|6081|60F4',line)]
            print(n,' | '.join(lines[:7]))
