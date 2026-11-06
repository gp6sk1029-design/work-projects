"""作業フォルダの容量とGit・アプリログの負荷を読取りで集計する。"""
from pathlib import Path
from collections import Counter, defaultdict
import os
import json
import re
import subprocess
import time

root=Path(r'C:\Users\SEIGI-N13\work-projects')
start=time.perf_counter()
stats=defaultdict(lambda:{'files':0,'bytes':0})
largest=[]; skipped=[]
stack=[root]
while stack:
    folder=stack.pop()
    try:
        with os.scandir(folder) as entries:
            for e in entries:
                p=Path(e.path)
                if e.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()):
                    skipped.append(str(p.relative_to(root)));continue
                if e.is_dir(follow_symlinks=False):stack.append(p)
                elif e.is_file(follow_symlinks=False):
                    s=e.stat(follow_symlinks=False).st_size
                    top=p.relative_to(root).parts[0]
                    stats[top]['files']+=1;stats[top]['bytes']+=s
                    if s>5_000_000:largest.append({'path':str(p.relative_to(root)),'bytes':s})
    except (PermissionError,FileNotFoundError):pass
    if time.perf_counter()-start>40:break
git=subprocess.run(['git','ls-files','-z'],cwd=root,capture_output=True,check=True).stdout.decode('utf-8').split('\0')
tracked=Counter(); tracked_files=[]
for rel in filter(None,git):
    p=root/rel
    if not p.is_file():continue
    size=p.stat().st_size
    tracked[Path(rel).suffix.lower()]+=1
    if size>1_000_000:tracked_files.append({'path':rel,'bytes':size})
logs=Path(r'C:\Users\SEIGI-N13\AppData\Local\Codex\Logs\2026\11\02')
events=[]; git_times=[]; attach=[]; send=[]
for p in logs.glob('*.log'):
    for no,line in enumerate(p.read_text(encoding='utf-8',errors='replace').splitlines(),1):
        if 'git.command.complete' in line:
            dur=re.search(r'durationMs=([\d.]+)',line)
            if dur:git_times.append(float(dur[1]))
            if re.search(r'aborted=true|exitCode=[1-9]| error ',line):
                events.append({'file':p.name,'line':no,'time':line[:24],'kind':'git-error','duration':dur[1] if dur else None,'command':re.search(r'command="(.*?)"',line)[1][:180] if re.search(r'command="(.*?)"',line) else ''})
        if re.search(r'upload|attachment/(?:add|upload|create|import)|file.*(?:too large|denied)|attach.*(?:fail|error)',line,re.I):
            attach.append({'file':p.name,'line':no,'prefix':line[:350]})
        if 'outcome=timeout' in line:
            rid=re.search(r'clientRequestId=([^ ]+)',line)
            dur=re.search(r'durationMs=([\d.]+)',line)
            stage=re.search(r'stage=([^ ]+)',line)
            send.append({'file':p.name,'line':no,'time':line[:24],'request':rid[1] if rid else '', 'durationMs':dur[1] if dur else None,'stage':stage[1] if stage else None})
result={'scan_seconds':round(time.perf_counter()-start,2),'folders':dict(sorted(stats.items(),key=lambda x:x[1]['bytes'],reverse=True)),'largest_files':sorted(largest,key=lambda x:x['bytes'],reverse=True)[:15],'skipped_links':skipped,'tracked_count':len(list(filter(None,git))),'tracked_types':tracked.most_common(15),'tracked_large_files':sorted(tracked_files,key=lambda x:x['bytes'],reverse=True)[:15],'git_log_command_count':len(git_times),'git_log_max_ms':max(git_times,default=0),'git_errors':events[-15:],'attachment_events':attach[-12:],'send_timeouts':send[-12:],'unique_timeout_requests':len({x['request'] for x in send if x['request']})}
dest=root/'tmp'/'codex-freeze-20261102'/'workspace_check.json'
dest.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
