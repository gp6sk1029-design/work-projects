"""添付・送信段階のログを短いメタデータだけで確認する。"""
from pathlib import Path
import json
import re
from collections import Counter

base=Path(r'C:\Users\SEIGI-N13\AppData\Local\Codex\Logs\2026\11\02')
events=[]
patterns=re.compile(r'clipboard|attachment|upload|turn/start|turn_start|prompt.*submit|submit.*prompt|send_message|message.*(?:send|submit)|outcome=timeout',re.I)
for p in base.glob('*.log'):
    for no,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        if not patterns.search(line):continue
        # 一覧取得やライブラリ一覧は送信の証拠ではないので除外する。
        if 'thread/attachment/list' in line or 'marketplace' in line or 'runtimeInstallConfig=' in line:continue
        fields={}
        for key in ['method','event','stage','outcome','durationMs','errorMessage','errorName','errorCode','success','failureReason','conversationId','threadId','inputTextCharacters','attachmentsCount','attachmentCount']:
            m=re.search(r'\b'+key+r'=("(?:\\.|[^"\\])*"|[^ ]+)',line)
            if m:fields[key]=m[1][:180]
        event=line.split('] ',1)[-1].split(' ',1)[0]
        events.append({'time':line[:24],'file':p.name,'line':no,'event_name':event,'fields':fields})
result={'matched':len(events),'event_counts':dict(Counter(e['event_name'] for e in events)),'recent':sorted(events,key=lambda e:e['time'])[-24:]}
Path(__file__).with_name('attachment_stage.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
