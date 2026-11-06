"""個別の処理だけに時間制限を付け、アプリ画面を使わず実行する。"""
from pathlib import Path
import subprocess
import sys

here=Path(__file__).parent
node=Path(r"C:\Users\SEIGI-N13\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe")
try:
    r=subprocess.run([str(node),str(here/'edit.mjs'),sys.argv[1] if len(sys.argv)>1 else 'inspect'],capture_output=True,text=True,encoding='utf-8',timeout=60)
    (here/'node-last.log').write_text(r.stdout+'\n'+r.stderr,encoding='utf-8')
    print(r.stdout[-2500:])
    print(r.stderr[-1200:])
    sys.exit(r.returncode)
except subprocess.TimeoutExpired:
    print('個別の表計算処理が60秒を超えたため停止。原本には書き込んでいません。')
    sys.exit(124)
