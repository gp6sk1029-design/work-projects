"""原本を読み取り専用で調査する。"""
import sys, zipfile, re, io, collections, json
sys.stdout.reconfigure(encoding='utf-8')
def inspect(data, prefix=''):
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for e in z.infolist():
            b=z.read(e)
            path=prefix+e.filename
            if b.startswith(b'PK\x03\x04'):
                print('NESTED',path,len(b)); inspect(b,path+'!'); continue
            if not b: continue
            enc='utf-8-sig'
            if b.startswith((b'\xff\xfe',b'\xfe\xff')): enc='utf-16'
            try: t=b.decode(enc)
            except UnicodeError:
                hits=set(re.findall(rb'[A-Za-z_][A-Za-z_0-9]*_R(?:_[A-Za-z_0-9]*)?',b))
                if hits: print('BINARY_R',path,len(b),[x.decode() for x in sorted(hits)[:12]])
                continue
            if '\x00' in t:
                print('NULL_BINARY',path,len(b)); continue
            names=re.findall(r'(?:^|\t)N=([^\t\r\n]+)',t,re.M)
            if names:
                targets=[n for n in names if re.search(r'(^|_)R(?=_|$)',n)]
                collision=[(n,re.sub(r'(^|_)R(?=_|$)',r'\1A',n)) for n in targets if re.sub(r'(^|_)R(?=_|$)',r'\1A',n).casefold() in {s.casefold() for s in names}]
                print('DEFINITIONS',path,len(names),'R',len(targets),'COLLISIONS',collision)
                print(json.dumps(targets,ensure_ascii=False))
            if '_R' in t:
                print('TEXT_R',path,len(b),repr(t[:95]))
            if e.filename.endswith(('.manifest','.element','.ini')): print('META',path,t[:1200])
if '--summary' in sys.argv:
    with zipfile.ZipFile(sys.argv[1]) as z:
        texts={}
        for e in z.infolist():
            try:
                t=z.read(e).decode('utf-8-sig')
                if '\x00' not in t: texts[e.filename]=t
            except UnicodeError: pass
        names=set()
        for t in texts.values(): names.update(re.findall(r'(?:^|\t)N=([^\t\r\n]+)',t,re.M))
        targets={n:re.sub(r'(^|_)R(?=_|$)',r'\1A',n) for n in names if re.search(r'(^|_)R(?=_|$)',n)}
        print('UNIQUE',len(names),'TARGETS',len(targets))
        print('GLOBAL_COLLISIONS',[(a,b) for a,b in targets.items() if b.casefold() in {n.casefold() for n in names}])
        pat=re.compile(r'(?<![\w])(?:'+'|'.join(re.escape(n) for n in sorted(targets,key=len,reverse=True))+r')(?![\w])')
        for e in z.infolist():
            b=z.read(e)
            if e.filename in texts:
                t=texts[e.filename]; ms=pat.findall(t)
                if ms:
                    print('MAPPED',e.filename.rsplit('/',1)[-1],len(ms),len(set(ms)))
                    if e.filename.endswith('.oem'):
                        for m in list(pat.finditer(t))[:6]: print(repr(t[max(0,m.start()-95):m.end()+100]))
            elif not b.startswith(b'PK'):
                hits=[n for n in targets if n.encode() in b or n.encode('utf-16le') in b]
                if hits: print('UNDECODED_MAPPED',e.filename,len(hits))
        print('SAMPLES',sorted(targets.items())[:12])
else:
    with open(sys.argv[1],'rb') as f: inspect(f.read())
