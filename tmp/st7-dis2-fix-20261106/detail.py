from pathlib import Path
import json,re
b=Path(__file__).parent;d=json.loads((b/'snapshot.json').read_text(encoding='utf-8'))
for part,txt in d['variables'].items():
    for line in txt.splitlines():
        if not line.startswith('++D='):continue
        fields=dict(x.split('=',1) for x in line[2:].split('\t') if '=' in x)
        name=fields.get('N','')
        if any(x in name for x in ['ST7_A','A_SF_','RCON1_3_','RCON1_5_']) and name not in ['RCON1_RxWord','RCON1_RxRaw']:
            if fields.get('G') in ['VAR','VAR_GLOBAL'] or name=='ST7_A_SF_Busy':print(part,line)
for s in d['sections']:
    if s['name']!='Error_エラー処理':continue
    for i in [2,3,31,32,33,34,40]:
        print('ERROR',i,json.dumps(s['rows'][i],ensure_ascii=False))
