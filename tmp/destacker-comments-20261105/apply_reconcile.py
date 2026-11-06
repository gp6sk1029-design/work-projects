"""一覧で対象が閉じていることを確認後、保存日時２項目だけを更新する。"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from xml.etree import ElementTree as E
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent/'reconcile'
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-comments-20261105/reconcile');out.mkdir(exist_ok=True)
m=json.loads((b/'meta.json').read_text(encoding='utf-8'))
p=sm.Project(m['internal']);ref=sm.Project(b/'I_synced.smc2')
assert p.fingerprint==m['internal_sha'], '準備後に内部本体が更新されたため停止'
assert p.declarations()==ref.declarations() and all(a['rows']==c['rows'] for a,c in sm.align(p,ref))
native=json.loads((b/'native.json').read_text(encoding='utf-8-sig'));assert native['verified'] and native['sha256']==ref.fingerprint
changes=[]
for t in m['internal_metadata']:
    old=p.entries[t['part']];new=Path(t['file']).read_bytes();assert sm.sha(old)==t['before_sha']
    x=E.fromstring(old);y=E.fromstring(new)
    if t['part'].endswith('.oem'):
        a=next(e for e in x.iter('Entity') if e.get('type')=='Solution');c=next(e for e in y.iter('Entity') if e.get('type')=='Solution')
        assert c.get('dateLastModified')==m['oem_date'];a.attrib.pop('dateLastModified');c.attrib.pop('dateLastModified')
    else:
        a=x.find('.//DateModified');c=y.find('.//DateModified');assert c.text==m['iso_jst'];a.text=c.text=''
    assert E.tostring(x)==E.tostring(y), '日時以外の変更は許可しない'
    changes.append({'part':t['part'],'before_sha':sm.sha(old),'after_sha':sm.sha(new)})
backup=out/('internal-metadata-before_'+sm.stamp()+'.zip')
with ZipFile(backup,'x',compression=ZIP_DEFLATED) as z:
    for part,data in p.entries.items():z.writestr(part,data)
with ZipFile(backup) as z:assert z.testzip() is None and all(z.read(k)==v for k,v in p.entries.items())
assert p.current_fingerprint()==p.fingerprint
written=[]
try:
    for t in m['internal_metadata']:
        target=(p.path/t['part']).resolve();assert target.is_relative_to(p.path)
        assert target.read_bytes()==p.entries[t['part']]
        sm.atomic_write(target,Path(t['file']).read_bytes());written.append(t['part'])
    post=sm.Project(p.path)
    assert set(post.entries)==set(p.entries)
    assert {k for k in p.entries if p.entries[k]!=post.entries[k]}==set(written)
    assert post.declarations()==p.declarations() and all(a['rows']==c['rows'] for a,c in sm.align(p,post))
except Exception:
    for part in reversed(written):sm.atomic_write(p.path/part,p.entries[part])
    raise
r={'solution':m['solution'],'project':str(p.path),'closed_state':'Sky画像でプロジェクト一覧を直前確認','backup':str(backup),'backup_files':len(p.entries),'before_sha':p.fingerprint,'after_sha':post.fingerprint,'changed':changes,'all_other_files_unchanged':True,'comments_control_declarations_unchanged':True,'comment_display_user_verified':True,'list_timestamp_display_verified':False,'DateModified':m['iso_jst'],'official_application_save':False}
sm.save_json(out/'内部日時更新結果.json',r)
print(json.dumps(r,ensure_ascii=False))
