"""Thunderbirdの下書きを読み取り専用で照合する。"""
from pathlib import Path
from email.parser import BytesParser
from email import policy
import re, sys
sys.stdout.reconfigure(encoding='utf-8')
path = Path(r'C:\Users\SEIGI-N13\AppData\Roaming\Thunderbird\Profiles\ia5jx4ac.default-release\Mail\mail.ime-group.co.jp\Drafts')
with path.open('rb') as f:
    f.seek(max(0, path.stat().st_size - 10_000_000))
    data = f.read()
matches = []
for raw in re.split(rb'(?m)^From [^\n]*\n', data)[1:]:
    raw = b''.join(line for line in raw.replace(b'\r\r\n', b'\r\n').splitlines(keepends=True) if not line.startswith(b'>From '))
    msg = BytesParser(policy=policy.default).parsebytes(raw)
    if 'AFPG804' not in str(msg.get('Subject', '')):
        continue
    if int(msg.get('X-Mozilla-Status', '0000'), 16) & 8:
        continue
    matches.append({'件名': str(msg['Subject']), '宛先': str(msg.get('To', '')), 'CC': str(msg.get('Cc', ''))})
print({'一致件数': len(matches), '下書き': matches})
