from pathlib import Path
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;m=json.loads((b/'build.json').read_text(encoding='utf-8'));p=sm.Project(m['stage']);src=sm.Project(m['backup'])
for q,indices in [(src,[14,18]),(p,[m['old_to_new_rows']['14'],m['old_to_new_rows']['18']])]:
    for i in indices:
        r=q.section('ST7_A_Dis2_左SF排出')['rows'][i];print('FILE',q.path.name,'ROW',i)
        for c in sorted(r['CLs'],key=lambda c:(c.get('Y',0),c.get('X',0))):print(c.get('X',0),c.get('Y',0),c['__type'],c.get('Var',c.get('Name','')),c.get('Not',False))
        print('VL',r['VLs'])
