from pathlib import Path
import json
d=json.loads((Path(__file__).parent/'snapshot.json').read_text(encoding='utf-8'))
for line in d['variables']['86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml'].splitlines():
    if not line.startswith('++'):print(repr(line))
rs=next(s for s in d['sections'] if s['name']=='RCON_IAI')['rows']
for i in [120,201]:print('RCON',i,json.dumps(rs[i],ensure_ascii=False))
