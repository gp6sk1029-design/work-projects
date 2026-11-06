from pathlib import Path
import sys,json,re
from zipfile import ZipFile,ZIP_DEFLATED
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;b.mkdir(exist_ok=True)
inside=sm.Project('C:/OMRON/Data/Solution/fe78558c-1d0e-41d5-9b83-730179a87edb')
matches=sm.find_projects('C:/OMRON/Data/Solution','20261105H')['matches']
assert any(Path(x['directory']).resolve()==inside.path for x in matches)
folder=Path('C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/0.DLデータ/OMRON/Codex編集用')
external=sm.Project(folder/'3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105H.smc2')
diff=sm.comparison(external,inside)
assert all(x['key'].endswith('/Destacker_段バラシ') for x in diff['sections']),diff
assert diff['variable_declarations_equal']
data={'internal':str(inside.path),'external':str(external.path),'internal_sha':inside.fingerprint,'external_sha':external.fingerprint,'comparison':diff,'sections':inside.sections,'variable_parts':inside.variable_parts}
(b/'project.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
(b/'external-before.smc2').write_bytes(external.path.read_bytes())
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-fix-20261105');out.mkdir(exist_ok=True)
backup=out/'内部H_修正前の保存データ.zip'
assert not backup.exists()
with ZipFile(backup,'x',compression=ZIP_DEFLATED) as z:
    for part,value in inside.entries.items():z.writestr(part,value)
with ZipFile(backup) as z:
    assert z.testzip() is None
    assert all(z.read(part)==value for part,value in inside.entries.items())
print(json.dumps({'internal_sha':inside.fingerprint,'comparison':diff,'backup_files':len(inside.entries)},ensure_ascii=False))
dest=inside.section('Destacker_段バラシ');print('DEST',dest['key'],dest['part'],len(dest['rows']))
used=sorted(set(int(n) for n in re.findall(r'Destacker_M\[(\d+)\]',json.dumps(inside.sections,ensure_ascii=False))))
print('USED_M',used)
assert not set(range(26,33))&set(used)
assert 'Destacker_Init_Busy' not in json.dumps(data,ensure_ascii=False)
for part,text in inside.variable_parts.items():
    if any('\tN='+tag+'\t' in text for tag in ['Destacker_M','BoxPacking_Init_Busy']):
        print('SCOPE',part)
        for line in text.splitlines():
            if any('\tN='+tag+'\t' in line for tag in ['Destacker_M','BoxPacking_Init_Busy']):print(line)
print('SOURCE_STABLE',inside.current_fingerprint()==inside.fingerprint,external.current_fingerprint()==external.fingerprint)
