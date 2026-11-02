import hashlib
import json
import shutil
from pathlib import Path

base = Path(r'\\nas-ime5\生産技術部\1.注文書\_内作設備\_1.製作中注文書')
source = base / '__【原紙_内作設備】SSSS-YYMM★ 設備名 (型式) 〈台〉【備考】'
name = '2717-2610A インナー巻線機 (AIW-1100T) 〈2台〉【マーレOH】'
dest = base / name
local = Path(__file__).parent
assert source.is_dir()
assert not list(base.glob('2717-2610A*')), '同番号フォルダあり。上書き禁止'
files = list(source.rglob('*'))
assert not any(p.name.startswith('~$') for p in files), '原紙にロックファイルあり'
books = [p for p in files if p.suffix.lower() == '.xlsx']
assert len(books) == 1
book = books[0]
backup = local / '原紙バックアップ.xlsx'
assert not backup.exists()
shutil.copy2(book, backup)
data = {'source': str(source), 'book': str(book), 'destination': str(dest), 'name':name,
        'sha256': hashlib.sha256(book.read_bytes()).hexdigest()}
(local / 'manifest.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(data,ensure_ascii=False))
