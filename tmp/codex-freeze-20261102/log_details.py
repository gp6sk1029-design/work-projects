"""エラー行を原因フィールドに限定して表示する。"""
from pathlib import Path
import json
import re

base=Path(r'C:\Users\SEIGI-N13\AppData\Local\Codex\Logs\2026\11\02')
git=[]; failures=[]; counts={}; closed=[]; hooks=[]
for p in base.glob('*.log'):
    for no,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        if 'app_server_connection.closed' in line:
            m=re.search(r'\breason=("(?:\\.|[^"\\])*")',line)
            reason=json.loads(m[1]) if m else line
            closed.append({'time':line[:24],'reason_tail':reason[-1200:]})
        if re.search(r'\bhook\b|SessionStart|Stop.*hook|UserPromptSubmit',line,re.I):
            hooks.append({'time':line[:24],'prefix':line[:200]})
        if 'git.command.complete' in line and ('aborted=true' in line or re.search(r'exitCode=[1-9]',line)):
            fields={}
            for key in ['aborted','durationMs','exitCode','signal','errorMessage','stderr','errorCode']:
                m=re.search(r'\b'+key+r'=("(?:\\.|[^"\\])*"|[^ ]+)',line)
                if m:fields[key]=m[1][:600]
            git.append({'file':p.name,'line':no,'fields':fields,'tail':line[-400:]})
        if re.search(r'Authenticated workspace changed|sa_server_request_failed|app_server.*(?:closed|unavailable)|send.*(?:failed|error)|upload.*(?:failed|error)|renderer.*unresponsive',line,re.I):
            fields={}
            for key in ['errorMessage','errorCode','errorName','reason','path','url']:
                m=re.search(r'\b'+key+r'=("(?:\\.|[^"\\])*"|[^ ]+)',line)
                if m and key not in ['url','path']:fields[key]=m[1][:260]
            failures.append({'file':p.name,'line':no,'time':line[:24],'event':line.split('] ',1)[-1].split(' ',1)[0],'fields':fields})
result={'git_errors':git[-10:],'request_failures':failures[-20:],'closed':closed,'hook_records':hooks[-8:]}
Path(__file__).with_name('log_details.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
