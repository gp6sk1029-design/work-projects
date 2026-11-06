from pathlib import Path
from zipfile import ZipFile
import json
b=Path(__file__).parent;m=json.loads((b/'inspection.json').read_text(encoding='utf-8'))
with ZipFile(m['source']) as z:
 rows=[json.loads(l) for l in z.read(m['target']['part']).decode('utf-8-sig').splitlines()]
 for i in [0,1,2]:print(i,json.dumps(rows[i],ensure_ascii=False))
