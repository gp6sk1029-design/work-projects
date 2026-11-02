"""Excel保存後の読み戻しと印刷操作の記録。NASには書き込まない。"""
from pathlib import Path
import hashlib,json,shutil,sys
import openpyxl
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).resolve().parent
r=json.loads((b/'verification.json').read_text(encoding='utf-8'))
s=Path(r['source']);out=Path(r['output'])
w=openpyxl.load_workbook(s,data_only=False)
c=openpyxl.load_workbook(s,data_only=True)
t=w['10.30'];v=c['10.30']
for a,x in [('B17','AFPG804'),('E17',10),('F17',1050),('C9','AF-K261030-1'),('C10','生産技術部'),('C11','生産技術部 幸田宛')]:assert t[a].value==x,(a,t[a].value)
assert t['G17'].value=='=E17*F17' and t['G41'].value=='=SUM(G17:G40)'
assert v['G17'].value==v['G41'].value==10500
assert w.sheetnames==['10.30','10.7','7.9','7.7','原紙']
before=openpyxl.load_workbook(r['backup'],data_only=False)
for old in before:
 for row in old:
  for cell in row:assert cell.value==w[old.title][cell.coordinate].value,(old.title,cell.coordinate)
before.close();w.close();c.close()
shutil.copyfile(s,out)
r['sha256']=hashlib.sha256(s.read_bytes()).hexdigest()
assert hashlib.sha256(out.read_bytes()).hexdigest()==r['sha256']
r.update(printed=True,print_button_clicks=1,printer='RICOH SP 6410 JPN RPCS',paper='A4',copies=1,sides='片面',page_from=1,page_to=1,print_scope='作業中のシート 10.30',physical_output_confirmed=False,queue_remaining=0,excel_saved=True)
(b/'verification.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(r,ensure_ascii=False,indent=2))
