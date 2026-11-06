from pathlib import Path
import sys,json,datetime
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent
ref=sm.Project(b/'I_all_comments.smc2');found=sm.find_projects('C:/OMRON/Data/Solution','20261105I')['matches'];results=[]
for match in found:
    p=sm.Project(match['directory']);diff=sm.comparison(p,ref);dest=p.section('Destacker_段バラシ')
    results.append({'name':match['name'],'directory':str(p.path),'sha':p.fingerprint,'comparison':diff,'first_comment':dest['rows'][0].get('CMT'),'check_comment':dest['rows'][16].get('CMT'),'ladder_mtime':datetime.datetime.fromtimestamp((p.path/dest['part']).stat().st_mtime).isoformat()})
external=sm.Project('C:/Users/SEIGI-N13/Desktop/3089-2603A 検査箱詰め装置(CORE SUB)/0.DLデータ/OMRON/Codex編集用/3089-2603A_検査箱詰め装置_CORE_SUB_PIP-02F02NX_20261105I.smc2')
out={'projects':results,'external_sha':external.fingerprint,'external_comparison':sm.comparison(external,ref)}
sm.save_json(b/'copy_audit.json',out)
print(json.dumps(out,ensure_ascii=False))
