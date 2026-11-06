from pathlib import Path
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;b.mkdir(exist_ok=True)
matches=sm.find_projects('C:/OMRON/Data/Solution','20261105I')['matches'];assert len(matches)==1
inside=sm.Project(matches[0]['directory'])
base=sm.Project('C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/0.DLデータ/OMRON/Codex編集用/3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105I.smc2')
diff=sm.comparison(inside,base)
assert not diff['control_difference'] and diff['variable_declarations_equal'],diff
d={'internal':str(inside.path),'internal_sha':inside.fingerprint,'base':str(base.path),'base_sha':base.fingerprint,'solution':matches[0]['name'],'comparison':diff,'sections':inside.sections,'variable_parts':inside.variable_parts}
(b/'project.json').write_text(json.dumps(d,ensure_ascii=False),encoding='utf-8')
print(json.dumps({k:v for k,v in d.items() if k not in ['sections','variable_parts']},ensure_ascii=False))
for i,r in enumerate(inside.section('Destacker_段バラシ')['rows']):print(i,r.get('CMT','').replace('\r\n',' / '))
print('BOX_EXAMPLES')
for i in [0,3,10,15,35,39]:print(i,inside.section('BoxPacking_箱詰め')['rows'][i].get('CMT',''))
