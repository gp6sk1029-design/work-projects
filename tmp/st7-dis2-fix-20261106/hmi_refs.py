from pathlib import Path
import json
d=json.loads((Path(__file__).parent/'snapshot.json').read_text(encoding='utf-8'))
for s in d['sections']:
    for i,r in enumerate(s['rows']):
        if s['name']=='ST7_A_Dis2_左SF排出':continue
        txt=json.dumps(r,ensure_ascii=False)
        if ('ST7' in txt or 'Error_ST7' in txt or 'A_SF_CT' in txt) and s['name'] not in ['Ins_A_Cv_左検査Cv','RCON_IAI','BoxPacking_箱詰め']:
            print(s['name'],i)
            for c in r['CLs']:
                if c['__type']=='HL':continue
                if c['__type']=='IST':
                    for line in c.get('TXT','').splitlines():
                        if any(x in line for x in ['ST7','A_SF_CT','Source_M']):print(line)
                else:print(c['__type'],c.get('Var'),c.get('Name'))
            if 'ST7_A_Dis2_M[11]' in txt:print(json.dumps(r,ensure_ascii=False))
