"""同一ブックの処理を、作業フォルダ内外のコピーで比較する。"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import time
import tomllib

root=Path(r'C:\Users\SEIGI-N13\work-projects')
home=Path(r'C:\Users\SEIGI-N13')
source=home/'Desktop'/'【業務報告2026 Ver2.7】幸田.xlsx'
node=home/'.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
script=root/'tmp/work-report-202610/edit.mjs'
data=source.read_bytes();before=hashlib.sha256(data).hexdigest()
folders=[root/'tmp/codex-freeze-20261102/inside-test',home/'Codex-Diagnostics/freeze-20261102']
result=[]
for folder in folders:
    folder.mkdir(parents=True,exist_ok=True)
    (folder/'freeze-source.xlsx').write_bytes(data)
    env={**os.environ,'CODEX_FREEZE_TEST_DIR':str(folder)}
    start=time.perf_counter()
    p=subprocess.run([str(node),str(script),'probe'],cwd=folder,env=env,capture_output=True,text=True,encoding='utf-8',timeout=60)
    (folder/'test-process.log').write_text(p.stdout+'\n'+p.stderr,encoding='utf-8')
    result.append({'folder':str(folder),'seconds':round(time.perf_counter()-start,3),'exit_code':p.returncode,'input_sha256':hashlib.sha256((folder/'freeze-source.xlsx').read_bytes()).hexdigest(),'saved':(folder/'freeze-test-only.xlsx').is_file(),'stdout':p.stdout.strip()[-500:]})
    assert p.returncode==0,p.stderr[-500:]
after=hashlib.sha256(source.read_bytes()).hexdigest()
config=tomllib.loads((home/'.codex/config.toml').read_text(encoding='utf-8'))
config_summary={'hooks_feature':config.get('features',{}).get('hooks','未指定'),'deprecated_codex_hooks_feature':config.get('features',{}).get('codex_hooks','未指定'),'global_hook_events':list(config.get('hooks',{})),'user_hooks_json_exists':(home/'.codex/hooks.json').exists(),'project_hooks_json_exists':(root/'.codex/hooks.json').exists()}
out={'tests':result,'original_unchanged':before==after,'source_write_operations':0,'config':config_summary,'scope':'Node上の読込・コピー変更・保存の比較。Codexの添付/送信やhooksの動作を再現する試験ではない。'}
(root/'tmp/codex-freeze-20261102/directory_comparison.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(out,ensure_ascii=False))
