"""閉状態確認済みIへ、検査した変数説明文だけを限定更新する。"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import sys,json,re
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-comments-20261105')
d=json.loads((b/'project.json').read_text(encoding='utf-8'));m=json.loads((b/'name-meta.json').read_text(encoding='utf-8'))
inside=sm.Project(d['internal']);ref=sm.Project(b/'I_all_comments.smc2');native=json.loads((b/'name-native.json').read_text(encoding='utf-8-sig'))
assert native['verified'] and native['sha256']==ref.fingerprint
assert inside.fingerprint==m['internal_before']
assert inside.declarations()==ref.declarations()
assert not sm.comparison(inside,ref)['control_difference']
assert all(a['rows']==c['rows'] for a,c in sm.align(inside,ref))
def no_comments(data):
    text=data.decode('utf-8-sig')
    return '\n'.join(re.sub(r'\t(?:Com|EC)=[^\t\r\n]*','',line) for line in text.splitlines())
changes=[]
for t in m['targets']:
    old=inside.entries[t['internal_part']];new=ref.entries[t['base_part']]
    assert no_comments(old)==no_comments(new),t
    assert old!=new
    changes.append({'part':t['internal_part'],'names':t['names'],'before_sha':sm.sha(old),'after_sha':sm.sha(new)})
backup=out/('names-before_'+sm.stamp()+'.zip')
with ZipFile(backup,'x',compression=ZIP_DEFLATED) as z:
    for part,data in inside.entries.items():z.writestr(part,data)
with ZipFile(backup) as z:
    assert z.testzip() is None and all(z.read(k)==v for k,v in inside.entries.items())
assert inside.current_fingerprint()==inside.fingerprint
written=[]
try:
    for target in m['targets']:
        part=target['internal_part'];path=(inside.path/part).resolve()
        assert path.is_relative_to(inside.path) and path.read_bytes()==inside.entries[part]
        sm.atomic_write(path,ref.entries[target['base_part']]);written.append(part)
    post=sm.Project(inside.path)
    assert set(post.entries)==set(inside.entries)
    changed=[k for k in inside.entries if inside.entries[k]!=post.entries[k]]
    assert set(changed)==set(written)
    assert post.declarations()==inside.declarations()==ref.declarations()
    assert all(a['rows']==c['rows'] for a,c in sm.align(inside,post))
    # 適用先のCom/ECも参照候補と一致することを変数表IDごとに照合。
    for target in m['targets']:assert post.entries[target['internal_part']]==ref.entries[target['base_part']]
except Exception:
    for part in reversed(written):sm.atomic_write(inside.path/part,inside.entries[part])
    raise
report={'project':str(inside.path),'solution':d['solution'],'user_confirmed_closed':True,'backup':str(backup),'backup_files':len(inside.entries),'before_sha':inside.fingerprint,'after_sha':post.fingerprint,'changed':changes,'comment_attributes_only':True,'variable_declarations_identical':True,'all_ladder_fields_identical':True,'element_comments':32,'ui_reflection_verified':False}
sm.save_json(out/'変数コメント直接反映結果.json',report);print(json.dumps(report,ensure_ascii=False))
