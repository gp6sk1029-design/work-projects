"""利用者指定の現在のB版を読み取り専用で確認し、段番号と参照を集計する。"""
from pathlib import Path
from lxml import etree as E
import zipfile,json,re,hashlib,collections,sys,time
sys.stdout.reconfigure(encoding='utf-8')
start=time.monotonic();base=Path(__file__).parent
src=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\0.DLデータ\OMRON\3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261103B.smc2')
data=src.read_bytes();digest=hashlib.sha256(data).hexdigest()
def walk(x,path):
 if isinstance(x,dict):
  if isinstance(x.get('Var'),str):
   m=re.fullmatch(r'Destacker_M\[(\d+)\]',x['Var'])
   if m:yield {'index':int(m[1]),'type':x.get('__type'),'element':x.get('Ix'),'path':path}
  for k,v in x.items():yield from walk(v,path+[k])
 elif isinstance(x,list):
  for i,v in enumerate(x):yield from walk(v,path+[i])
with zipfile.ZipFile(src) as z:
 assert z.testzip() is None
 found=[]
 for n in z.namelist():
  if n.endswith('.oem'):
   r=E.fromstring(z.read(n))
   for e in r.iter():
    if e.get('name')=='Destacker_段バラシ':found.append(n.rsplit('/',1)[0]+'/'+e.get('id')+'.xml')
 assert len(found)==1
 target=found[0]
 rows=[json.loads(l) for l in z.read(target).decode('utf-8-sig').splitlines() if l.strip()]
 references=list(walk(rows,[]))
 coils=[x for x in references if x['type']=='ST']
 reads=[x for x in references if x['type']!='ST']
 coilnums=[x['index'] for x in coils];unique=set(coilnums);readnums={x['index'] for x in reads}
 rowtable=[{'row':i,'coils':[x['index'] for x in coils if x['path'][0]==i],'contacts':[x['index'] for x in reads if x['path'][0]==i]} for i in range(len(rows))]
 allnums={x['index'] for x in references}
 minimum=1;maximum=max(allnums)
 missing_coils=[i for i in range(minimum,maximum+1) if i not in unique]
 duplicates={str(i):[x['path'][0] for x in coils if x['index']==i] for i,c in collections.Counter(coilnums).items() if c>1}
 others=[]
 for n in z.namelist():
  if n==target:continue
  try:t=z.read(n).decode('utf-8-sig')
  except UnicodeError:continue
  hits=re.findall(r'Destacker_M\s*\[(\d+)\]',t)
  if hits:others.append({'part':n,'indices':sorted(set(map(int,hits)))})
 original_created=json.loads((base/'verification.json').read_text(encoding='utf-8'))['output_sha256']
 report={'file':str(src),'sha256':digest,'same_as_generated_B':digest==original_created,'target':target,'row_count':len(rows),'coil_order':coilnums,'coil_count':len(coilnums),'unique_coil_count':len(unique),'checked_range':[minimum,maximum],'missing_coils':missing_coils,'duplicate_coils_rows':duplicates,'contacts_without_coil':sorted(readnums-unique),'contacts_without_coil_rows':{str(i):sorted({x['path'][0] for x in reads if x['index']==i}) for i in readnums-unique},'missing_in_all_references':[i for i in range(minimum,maximum+1) if i not in allnums],'outside_section_indexed_references':others,'rows':rowtable,'ZIP_CRC':'正常','file_unchanged':hashlib.sha256(src.read_bytes()).hexdigest()==digest,'seconds':round(time.monotonic()-start,3)}
 assert report['file_unchanged']
 (base/'B版番号確認.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
