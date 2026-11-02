import json,sys
from pathlib import Path
sys.stdout.reconfigure(encoding='utf-8')
d=json.loads(Path(__file__).with_name('source_cells.json').read_text(encoding='utf-8'))['IO']['cells']
for row in list(range(7,24))+list(range(33,51)):
    cols=['R','S','X','Y','AE','AF','AK','AL','AR','AS','AX','AY','BE','BF','BK','BL']
    print(row, ' | '.join(c+'='+d.get(c+str(row),'') for c in cols))
print('LOCAL')
for row in list(range(7,24))+list(range(33,51)):
    print(row,' | '.join(c+'='+d.get(c+str(row),'') for c in ['E','F','G','J','K','L','CD','CE','CG','CH','CJ','CK']))
