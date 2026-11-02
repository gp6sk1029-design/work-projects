from pathlib import Path
import sys,json,re,xml.etree.ElementTree as ET
sys.stdout.reconfigure(encoding='utf8')
d=json.loads((Path(__file__).parent/'inspection.json').read_text(encoding='utf8')); ts=d['texts']
g=next(t for t in ts.values() if '+GN=VAR_GLOBAL' in t)
rows=[dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p) for l in g.splitlines() if l.startswith('++D=')]
for node in [1,5]:
 for direction in ['Out','In']:
  r=[x for x in rows if x.get('AT','').startswith(f'ECAT://node#{node}/{direction}_')]
  print('BINDINGS',node,direction,len(r),r[:2],r[-2:])
print('INITIAL SAMPLES',[r for r in rows if any(k in r for k in ['IV','I','Init','InitVal'])][:4])
print('LOCAL IV EXAMPLES')
for n,t in ts.items():
 if t.startswith('[SLWD'):
  for l in t.splitlines():
   if 'IV=' in l or 'Init' in l: print(n,l[:250])
print('EXISTING LOGIC USES')
for n,t in ts.items():
 if t.startswith('[SLWD') or n.endswith('.oem') or not t.lstrip().startswith('{'):continue
 hits=re.findall(r'(?:RCON[12]_|E001_|E005_)(?:\w+)',t)
 # E005は別ノードの機器の名前にも用いられる。RCON用2003/2004ワードだけ。
 hits=[h for h in hits if h.startswith(('RCON1_','RCON2_','E001_')) or re.match(r'E005_(?:Out_OUT|In_IN)\d+_200[34]_',h)]
 if hits:print(n,len(hits),list(dict.fromkeys(hits))[:15])
print('SOURCEHOLDER RELATED FILES',[n for n in d['entries'] if any(i in n for i in ['76d6fc6a','f661ac2f','34f6688b','c58a0379','697c7521','40f71c79','a58927e4'])])
print('OEM SUMMARY',ET.fromstring(ts[d['oem']]).attrib)
