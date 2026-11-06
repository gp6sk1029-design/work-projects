"""内部Iの確認済み説明と外部Iを同期し、実際の今回保存時刻をメタデータへ記録する準備。"""
from pathlib import Path,PurePosixPath
from xml.etree import ElementTree as E
import sys,json,re,datetime
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent/'reconcile';b.mkdir(exist_ok=True)
inside=sm.Project('C:/OMRON/Data/Solution/6cb83995-6d0c-45b5-ace2-b96278ba04c8')
source=sm.Project('C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/0.DLデータ/OMRON/Codex編集用/3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105I.smc2')
ref=sm.Project(b.parent/'I_all_comments.smc2')
assert not sm.comparison(inside,ref)['control_difference'] and inside.declarations()==ref.declarations()
assert all(a['rows']==c['rows'] for a,c in sm.align(inside,ref))
assert not sm.comparison(source,ref)['control_difference'] and source.declarations()==ref.declarations()
now=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)));iso=now.isoformat(timespec='microseconds');oem_date=now.strftime('%m/%d/%Y %H:%M:%S')
solution=inside.solution_names[0];ident=inside.path.name
ops=[]
def replacement(part,new,label):
    if source.entries[part]==new:return
    f=b/(label+'.bin');f.write_bytes(new)
    ops.append({'op':'replace-part','part':part,'expected_sha256':sm.sha(source.entries[part]),'file':str(f.resolve())})
# コメントを全体検査済みの候補から、外部Iの対応エントリへ同期。
for s in ref.sections:
    if s['name']=='Destacker_段バラシ':
        target=source.section(s['key']);replacement(target['part'],ref.entries[s['part']],'ladder')
for part,content in ref.variable_parts.items():
    if source.entries[part]!=ref.entries[part]:replacement(part,ref.entries[part],PurePosixPath(part).stem)
def patch_oem(data):
    text=data.decode('utf-8-sig');m=re.search(r'<Entity\b[^>]*\btype="Solution"[^>]*>',text);assert m
    tag=re.sub(r'\bdateLastModified="[^"]*"','dateLastModified="'+oem_date+'"',m.group(0))
    new=text[:m.start()]+tag+text[m.end():]
    return (b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b'')+new.encode('utf-8')
def patch_root(data):
    text=data.decode('utf-8-sig');assert '<SolutionModel>' in text
    text,n=re.subn(r'<DateModified>[^<]*</DateModified>','<DateModified>'+iso+'</DateModified>',text);assert n==1
    text,n=re.subn(r'<Project>[^<]*</Project>','<Project>'+solution+'</Project>',text);assert n==1
    return (b'\xef\xbb\xbf' if data.startswith(b'\xef\xbb\xbf') else b'')+text.encode('utf-8')
internal_meta=[]
for part,data in inside.entries.items():
    if part==ident+'.oem':new=patch_oem(data)
    elif part==ident+'.xml':new=patch_root(data)
    else:continue
    f=b/('internal_'+PurePosixPath(part).suffix[1:]+'.bin');f.write_bytes(new)
    internal_meta.append({'part':part,'before_sha':sm.sha(data),'file':str(f.resolve())})
assert len(internal_meta)==2
# 外部のルートIDは元のSMC2のまま維持。本文に出るProject名と日時だけ合わせる。
oems=[x for x in source.entries if x.endswith('.oem')];assert len(oems)==1
opart=oems[0];rootpart=str(PurePosixPath(opart).with_suffix('.xml'));assert rootpart in source.entries
replacement(opart,patch_oem(source.entries[opart]),'external_oem')
replacement(rootpart,patch_root(source.entries[rootpart]),'external_root')
sm.save_json(b/'plan.json',{'source_sha256':source.fingerprint,'operations':ops})
meta={'internal':str(inside.path),'internal_sha':inside.fingerprint,'external':str(source.path),'external_sha':source.fingerprint,'solution':solution,'iso_jst':iso,'oem_date':oem_date,'internal_metadata':internal_meta,'user_confirmed_comment_visible':True,'changes_are_actual_comment_sync_and_save_metadata':True}
sm.save_json(b/'meta.json',meta)
print(json.dumps({'external_changes':len(ops),'internal_metadata':internal_meta,'time_jst':iso,'existing_control_identical':True},ensure_ascii=False))
