from pathlib import Path
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
inside=sm.Project(d['internal']);outside=sm.Project(d['external'])
v={'internal_before':d['internal_sha256'],'internal_after':inside.fingerprint,'internal_unchanged':d['internal_sha256']==inside.fingerprint,
   'external_before':d['external_sha256'],'external_after':outside.fingerprint,'external_unchanged':d['external_sha256']==outside.fingerprint,
   'comparison':sm.comparison(inside,outside),'internal_destacker_unchanged':inside.section('Destacker_段バラシ')==next(s for s in d['sections'] if s['name']=='Destacker_段バラシ')}
(b/'readonly_verification.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(v,ensure_ascii=False))
