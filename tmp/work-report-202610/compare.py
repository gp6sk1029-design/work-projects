"""編集ツールの計算結果と原本との差を調べる。保存はしない。"""
from pathlib import Path
import json
import sys
# 標準ライブラリinspectと同名のローカル調査ファイルを探索対象から外す。
sys.path=[p for p in sys.path if Path(p or '.').resolve()!=Path(__file__).parent.resolve()]
import openpyxl

base=Path(__file__).parent
old=openpyxl.load_workbook(base/'backup'/'【業務報告2026 Ver2.7】幸田_編集前.xlsx',data_only=True)
new=openpyxl.load_workbook(sys.argv[1] if len(sys.argv)>1 else base/'artifact-edited.xlsx',data_only=True)
diff=[]
for ws in old:
    nw=new[ws.title]
    for row in ws:
        for c in row:
            b=nw[c.coordinate].value
            a=c.value
            if isinstance(a,(int,float)) and isinstance(b,(int,float)):
                equal=abs(a-b)<1e-9
            else:equal=a==b
            if not equal:diff.append({'sheet':ws.title,'cell':c.coordinate,'before':a,'after':b})
(base/('concurrent_differences.json' if len(sys.argv)>1 else 'value_differences.json')).write_text(json.dumps(diff,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
print(json.dumps({'count':len(diff),'diff':diff[:65]},ensure_ascii=False,default=str))
