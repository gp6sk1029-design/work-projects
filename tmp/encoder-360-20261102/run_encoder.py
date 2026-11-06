"""画面を開かず、この作業専用の処理だけに制限時間を付ける。"""
from pathlib import Path
import subprocess
import sys
base=Path(__file__).resolve().parent
node=Path(r'C:\Users\SEIGI-N13\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe')
try:
    p=subprocess.run([str(node),str(base/'edit_encoder.mjs'),sys.argv[1] if len(sys.argv)>1 else 'inspect'],capture_output=True,text=True,encoding='utf-8',timeout=60)
    (base/'last-process.log').write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
    print(p.stdout[-1200:]);print(p.stderr[-1000:]);sys.exit(p.returncode)
except subprocess.TimeoutExpired:
    print('60秒を超えたため、この処理のみ停止。原本への書込みはありません。');sys.exit(124)
