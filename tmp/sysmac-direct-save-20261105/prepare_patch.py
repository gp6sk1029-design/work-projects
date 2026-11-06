"""一覧内Hのコメント差分を準備し、内部保存先の完全バックアップを作る。"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from copy import copy,deepcopy
from lxml import etree as E
import json,hashlib,io
b=Path(__file__).parent;d=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
base=Path(d['internal_directory']).resolve();external=Path(d['external_file'])
assert base.parent==Path('C:/OMRON/Data/Solution').resolve()
metadata=E.fromstring((base/(base.name+'.oem')).read_bytes())
solution=next(e for e in metadata.iter() if e.get('type')=='Solution')
assert solution.get('name').endswith('_20261105H')
inside=next(s for s in d['internal_sections'] if s['name']=='BoxPacking_箱詰め')
outside=next(s for s in d['external_sections'] if s['name']=='BoxPacking_箱詰め')
target=Path(inside['path']).resolve();assert target.is_relative_to(base)
original=target.read_bytes();assert hashlib.sha256(original).hexdigest()==inside['sha256']
newlines=[];changes=[]
lines=original.decode('utf-8-sig').splitlines(keepends=True)
assert len(lines)==len(outside['rows'])==45
for i,(line,desired) in enumerate(zip(lines,outside['rows'])):
    current=json.loads(line);a=deepcopy(current);c=deepcopy(desired)
    a.pop('CMT',None);c.pop('CMT',None);assert a==c
    if current.get('CMT')!=desired.get('CMT'):
        changes.append({'row':i,'before':current.get('CMT',''),'after':desired.get('CMT','')})
        current['CMT']=desired['CMT']
        ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
        newlines.append(json.dumps(current,ensure_ascii=False,separators=(',',':'))+ending)
    else:newlines.append(line)
replacement=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(newlines).encode('utf-8')
assert [json.loads(l) for l in replacement.decode('utf-8-sig').splitlines()]==outside['rows']
assert len(changes)==18
(b/'internal_Box_before.xml').write_bytes(original)
(b/'internal_Box_after.xml').write_bytes(replacement)
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/sysmac-direct-save-20261105');out.mkdir(parents=True,exist_ok=True)
backup=out/'H_内部プロジェクト_直接保存前.zip';assert not backup.exists()
files=[p for p in base.rglob('*') if p.is_file()]
assert all(p.resolve().is_relative_to(base) for p in files)
manifest=[]
with ZipFile(backup,'x',compression=ZIP_DEFLATED) as z:
    for p in sorted(files):
        data=p.read_bytes();relative=str(p.relative_to(base)).replace('\\','/')
        z.writestr(relative,data);manifest.append({'path':relative,'sha256':hashlib.sha256(data).hexdigest(),'size':len(data)})
with ZipFile(backup) as z:
    assert z.testzip() is None
    for f in manifest:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
# 外部Hの箱詰め節へ内部データ形式の修正案を入れ、同梱読込みで検証する。
validated=b/'H_内部コメント更新_検証用.smc2'
with ZipFile(external) as z,ZipFile(validated,'w') as w:
    for info in z.infolist():w.writestr(copy(info),replacement if info.filename==outside['part'] else z.read(info.filename))
report={'internal_directory':str(base),'target':str(target),'solution_name':solution.get('name'),
    'external_file':str(external),'external_sha256':hashlib.sha256(external.read_bytes()).hexdigest(),
    'original_sha256':hashlib.sha256(original).hexdigest(),'replacement_sha256':hashlib.sha256(replacement).hexdigest(),
    'replacement':str(b/'internal_Box_after.xml'),'backup':str(backup),'backup_files':len(files),'backup_manifest':manifest,
    'changes':changes,'changed_comment_rows':len(changes),'staged':str(validated),'part':outside['part'],'native_read':None,
    'project_closed_confirmation':False,'applied':False,'ui_reflection_verified':False}
(b/'verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:report[k] for k in ['target','backup','backup_files','changed_comment_rows','applied']},ensure_ascii=False))
