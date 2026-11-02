"""検証済み候補だけをDesktopのB版と説明資料フォルダへ保存する。"""
from pathlib import Path
import hashlib,json,shutil,sys,zipfile
sys.stdout.reconfigure(encoding='utf8')
here=Path(__file__).parent
r=json.loads((here/'implementation.json').read_text(encoding='utf8'))
v=json.loads((here/'検証結果.json').read_text(encoding='utf8'))
source=Path(r['原本']);candidate=Path(r['候補']);dest=Path(r['保存先'])
sha=lambda b:hashlib.sha256(b).hexdigest()
assert v['PC模擬チェック合計']==398 and v['原本不変']
assert sha(source.read_bytes())==r['原本SHA256']
assert sha(candidate.read_bytes())==r['出力SHA256']
assert not dest.exists(),'同名B版があるため停止'
folder=dest.parent/'RCON_ST実装資料_20261019B'
assert not folder.exists(),'同名資料フォルダがあるため停止'
with zipfile.ZipFile(candidate) as z:assert z.testzip() is None
folder.mkdir()
with dest.open('xb') as f:f.write(candidate.read_bytes())
assert sha(dest.read_bytes())==r['出力SHA256']
files=[b['file'] for b in r['blocks']]+['追加グローバル56変数.tsv','追加ローカル12変数.tsv','追加外部参照280変数.tsv','実I_O割付照合256変数.tsv','最初に読む_実装内容と確認手順.txt','検証結果.json']
for name in files:shutil.copy2(here/name,folder/name)
public={k:x for k,x in r.items() if k not in ['候補','newGlobals','newLocals','externalNames']}
public['追加グローバル一覧']=r['newGlobals'];public['追加ローカル一覧']=r['newLocals']
public['PC模擬チェック合計']=398;public['Sysmac読込み・全体再ビルド']='未実施・必要'
(folder/'実装検証.json').write_text(json.dumps(public,ensure_ascii=False,indent=2),encoding='utf8')
assert sha(source.read_bytes())==r['原本SHA256']
assert len(list(folder.iterdir()))==13
print(json.dumps({'B版':str(dest),'バイト':dest.stat().st_size,'SHA256':sha(dest.read_bytes()),'原本不変':True,'資料':str(folder),'資料ファイル数':13,'検証チェック':398,'実機接続・転送':'なし','Sysmacビルド':'未実施'},ensure_ascii=False,indent=2))
