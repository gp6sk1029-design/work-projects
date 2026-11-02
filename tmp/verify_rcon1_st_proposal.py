"""生成STの限定構文をPCで模擬評価する。Sysmacコンパイル・実機試験の代用ではない。"""
from pathlib import Path
from types import SimpleNamespace
import re
import math
import json
import random
import zipfile

folder=Path(r'C:\Users\SEIGI-N13\Desktop\3089-2603A 検査箱詰め装置(CORE SUB)\資料\RCON1_6軸_ST変換案_20261017A')
current=json.loads(Path(r'C:\Users\SEIGI-N13\work-projects\tmp\rcon1_current_names.json').read_text(encoding='utf8'))
design=json.loads(Path(r'C:\Users\SEIGI-N13\work-projects\tmp\rcon-bible-20261017\manifest.json').read_text(encoding='utf8'))
defs={d['name']:d for d in design['defs']}
def table(name):
    lines=(folder/name).read_text(encoding='utf8').splitlines()
    return [l.split('\t') for l in lines[1:]]
globals_=table('追加グローバル変数.tsv')
locals_=table('追加ローカル変数.tsv')
existing={r['N']:r for r in current['variables']}
assert not (set(x[0] for x in globals_)&set(existing))
declared=set(existing)|set(x[0] for x in globals_+locals_)
files=sorted(folder.glob('*.st'))
assert len(files)==3
def strip(s):return re.sub(r'//[^\n]*','',s)
st=[strip(f.read_text(encoding='utf8')) for f in files]
names=set(re.findall(r'\b(?:RCON1_|E001_|Conv)\w*','\n'.join(st)))
assert names<=declared,names-declared
controls=design['defs'][0]['members']
statuses=design['defs'][1]['members']
for m in controls:assert f'.Control.{m["name"]}' in st[1]
for m in statuses:assert f'.Status.{m["name"]}' in st[0]
for m in re.findall(r'RCON1_OUT\[[^]]+\]\.(\w+)',st[1]):assert m in {x['name'] for x in defs['ST_RCON_Direct_OUT_Axis']['members']}
for m in re.findall(r'RCON1_IN\[[^]]+\]\.(\w+)',st[0]):assert m in {x['name'] for x in defs['ST_RCON_Direct_IN_Axis']['members']}
def raw(direction,n):return f'E001_{"Out" if direction=="OUT" else "In"}_{direction}{n:02d}_{"2003" if direction=="OUT" else "2004"}_{n+1:02X}'
for direction in ('OUT','IN'):
    for n in range(72):
        name=raw(direction,n)
        assert existing[name]['D']=='UINT'
        assert existing[name]['AT']==f'ECAT://node#1/{name[len("E001_"):]}'
written=re.findall(r'\b(E001_\w+)\s*:=','\n'.join(st))
assert set(written)=={raw('OUT',0)}|{raw('OUT',n) for n in range(8,56)}
assert len(written)==49
assert len(re.findall(r'RCON1_RxRaw\[\d+\]\s*:=',st[0]))==72

def checked(v,lo,hi):
    assert lo<=v<=hi,(v,lo,hi)
    return int(v)
def swap(v):return ((v&255)<<8)|((v>>8)&255)
def signed(v,bits):return v-(1<<bits) if v&(1<<(bits-1)) else v
functions={
    'UINT_TO_WORD':lambda v:checked(v,0,65535),
    'WORD_TO_UINT':lambda v:checked(v,0,65535),
    'WORD_TO_DWORD':lambda v:checked(v,0,65535),
    'DWORD_TO_WORD':lambda v:checked(v,0,65535),
    'DINT_TO_DWORD':lambda v:checked(v,-2147483648,2147483647)&0xFFFFFFFF,
    'UDINT_TO_DWORD':lambda v:checked(v,0,4294967295),
    'DWORD_TO_DINT':lambda v:signed(checked(v,0,4294967295),32),
    'WORD_TO_INT':lambda v:signed(checked(v,0,65535),16),
    'LINT_TO_DINT':lambda v:checked(v,-2147483648,2147483647),
    'LINT_TO_UDINT':lambda v:checked(v,0,4294967295),
    'LINT_TO_UINT':lambda v:checked(v,0,65535),
    'INT_TO_USINT':lambda v:checked(v,0,255),
    'DINT_TO_LREAL':float,'INT_TO_LREAL':float,
    'Swap':swap,'SHL':lambda v,n:v<<n,'SHR':lambda v,n:v>>n,
    'TRUNC':math.trunc,'TestABit':lambda v,p:bool(v&(1<<p)),
}
def expr(s,env):
    s=' '.join(s.split())
    bitwise=('WORD#' in s or 'WORD_TO_DWORD' in s)
    def literal(m):
        t,n=m.groups()
        if n.upper().startswith('16#'):return str(int(n[3:],16))
        return str(float(n)) if t in ('REAL','LREAL') else str(int(n))
    s=re.sub(r'\b(LREAL|REAL|ULINT|LINT|UDINT|DINT|UINT|INT|USINT|WORD|DWORD)#(16#[0-9A-Fa-f]+|[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)',literal,s)
    s=re.sub(r'\bTRUE\b','True',s);s=re.sub(r'\bFALSE\b','False',s)
    s=re.sub(r'\bAND\b','&' if bitwise else 'and',s)
    s=re.sub(r'\bOR\b','|' if bitwise else 'or',s)
    s=re.sub(r'\bNOT\b','not',s)
    s=s.replace('<>','!=')
    s=re.sub(r'(?<![<>=!:])=(?!=)','==',s)
    return eval(s,{'__builtins__':{}},functions|env)
def assign(lhs,value,env):
    root=re.match(r'\w+',lhs).group()
    rest=lhs[len(root):]
    if not rest:env[root]=value;return
    parts=re.findall(r'\[([^]]+)\]|\.(\w+)',rest)
    obj=env[root]
    for i,(index,member) in enumerate(parts):
        last=i==len(parts)-1
        if member:
            if last:setattr(obj,member,value)
            else:obj=getattr(obj,member)
        else:
            n=expr(index,env)
            if last:obj[n]=value
            else:obj=obj[n]
def tokenize(text):
    tokens=[];pos=0
    while pos<len(text):
        match=re.match(r'\s*',text[pos:]);pos+=match.end()
        if pos==len(text):break
        for name,end in [('END_IF',';'),('END_FOR',';'),('ELSIF','THEN'),('IF','THEN'),('FOR','DO')]:
            if re.match(name+r'\b',text[pos:]):
                m=re.search(r'\b'+end+r'\b' if end!=';' else ';',text[pos:])
                assert m,(name,text[pos:pos+100])
                chunk=text[pos:pos+m.start()].strip();pos+=m.end()
                tokens.append((name,chunk[len(name):].strip()));break
        else:
            if re.match(r'ELSE\b',text[pos:]):tokens.append(('ELSE',''));pos+=4;continue
            end=text.index(';',pos);chunk=text[pos:end].strip();pos=end+1
            assert ':=' in chunk,chunk
            tokens.append(('ASSIGN',chunk));continue
    return tokens
def parse(tokens,index=0,stop=()):
    result=[]
    while index<len(tokens):
        kind,text=tokens[index]
        if kind in stop:return result,index
        index+=1
        if kind=='ASSIGN':result.append((kind,text))
        elif kind=='FOR':
            body,index=parse(tokens,index,('END_FOR',));assert tokens[index][0]=='END_FOR';index+=1
            result.append((kind,text,body))
        elif kind=='IF':
            branches=[]
            body,index=parse(tokens,index,('ELSIF','ELSE','END_IF'));branches.append((text,body))
            while tokens[index][0]=='ELSIF':
                condition=tokens[index][1];index+=1
                body,index=parse(tokens,index,('ELSIF','ELSE','END_IF'));branches.append((condition,body))
            if tokens[index][0]=='ELSE':
                index+=1;body,index=parse(tokens,index,('END_IF',));branches.append((None,body))
            assert tokens[index][0]=='END_IF';index+=1;result.append((kind,branches))
        else:raise AssertionError(kind)
    return result,index
def run(block,env):
    for node in block:
        if node[0]=='ASSIGN':
            lhs,rhs=node[1].split(':=',1);assign(lhs.strip(),expr(rhs.strip(),env),env)
        elif node[0]=='FOR':
            m=re.fullmatch(r'(\w+)\s*:=\s*(.*?)\s+TO\s+(.*)',node[1],re.S);assert m,node
            first,last=expr(m[2],env),expr(m[3],env)
            for n in range(first,last+1):env[m[1]]=n;run(node[2],env)
        else:
            for condition,body in node[1]:
                if condition is None or expr(condition,env):run(body,env);break
blocks=[]
for text in st:
    tokens=tokenize(text);block,end=parse(tokens);assert end==len(tokens);blocks.append(block)
def value(dtype):
    m=re.fullmatch(r'ARRAY\[(\d+)\.\.(\d+)\] OF (\w+)',dtype)
    if m:return {n:value(m[3]) for n in range(int(m[1]),int(m[2])+1)}
    if dtype in defs:return SimpleNamespace(**{m['name']:value(m['type']) for m in defs[dtype]['members']})
    return False if dtype=='BOOL' else (0.0 if dtype=='LREAL' else 0)
def environment(byte_swap=False):
    env={r['N']:value(r['D']) for r in current['variables']}
    env.update({name:value(dtype) for name,dtype,_ in globals_+locals_})
    for name in ('RCON1_LayoutConfirmed','RCON1_ByteOrderConfirmed','RCON1_CommOK'):env[name]=True
    env['RCON1_SwapBytes']=byte_swap;env['RCON1_SpeedUnit_mm_s']=0.1
    env['RCON1_GwMON_Request']=True
    norm=[0]*72;norm[0]=0x8000;norm[1]=0x003F
    for a in range(1,7):
        b=8+(a-1)*8;pos=-2540 if a%2 else 70025;bits=pos&0xFFFFFFFF
        norm[b]=bits&0xFFFF;norm[b+1]=bits>>16
        norm[b+2]=1000;norm[b+3]=0;norm[b+4]=(-1250)&0xFFFF
        norm[b+6]=0x1234;norm[b+7]=0xD01B
        cmd=env['RCON1_OUT'][a];cmd.TargetPos_mm=25.4;cmd.PositionBand_mm=0.1
        cmd.Speed_mm_s=20.;cmd.AccDec_G=0.2;cmd.PushLimit_pct=50.;cmd.Control.ServoOn=True
    for n,v in enumerate(norm):env[raw('IN',n)]=swap(v) if byte_swap else v
    for n in range(72):env[raw('OUT',n)]=0x5A5A
    return env
tests=0
for order in (False,True):
    env=environment(order)
    for block in blocks:run(block,env)
    assert all(env[raw('OUT',n)]==0x5A5A for n in range(72))
    for a in range(1,7):
        inp=env['RCON1_IN'][a]
        assert math.isclose(inp.ActualPos_mm,-25.4 if a%2 else 700.25,abs_tol=1e-9)
        assert inp.Current_mA==1000 and inp.ActualSpeed_mm_s==-125.0 and inp.AlarmCode==0x1234
        assert inp.DataValid and env['RCON1_EncodeOK'][a]
        for m in statuses:assert getattr(inp.Status,m['name'])==bool(0xD01B&(1<<m['bit']))
    tests+=12
    env['RCON1_WriteEnable']=True;env['RCON1_GwApply']=True
    for a in range(1,7):env['RCON1_AxisApply'][a]=True;env['RCON1_MotionPermit'][a]=True
    run(blocks[2],env)
    for a in range(1,7):
        b=8+(a-1)*8;expected=[2540,0,10,0,200,20,127,16]
        assert [env[raw('OUT',b+k)] for k in range(8)]==[swap(v) if order else v for v in expected]
        assert env['RCON1_AxisWritten'][a]
    assert env[raw('OUT',0)]==(swap(0x8000) if order else 0x8000)
    assert all(env[raw('OUT',n)]==0x5A5A for n in list(range(1,8))+list(range(56,72)))
    tests+=14
# 位置を正負と上位非ゼロ、0.5境界で検査する。
for mm in [-9999.99,-700.25,-25.4,-0.005,0.,0.005,25.4,700.25,9999.99]:
    env=environment();env['RCON1_OUT'][1].TargetPos_mm=mm;run(blocks[1],env)
    scaled=mm*100;expected=math.trunc(scaled+(0.5 if scaled>=0 else -0.5))
    assert env['RCON1_TxWord'][8]==(expected&0xFFFF)
    assert env['RCON1_TxWord'][9]==((expected&0xFFFFFFFF)>>16)
    tests+=1
for m in controls:
    env=environment()
    for c in controls:setattr(env['RCON1_OUT'][1].Control,c['name'],False)
    setattr(env['RCON1_OUT'][1].Control,m['name'],True);run(blocks[1],env)
    assert env['RCON1_TxWord'][15]==1<<m['bit']
    assert not env['RCON1_TxWord'][15]&(1<<9)
    tests+=1
invalid=[('unit',0.,1),('TargetPos_mm',float('nan'),2),('TargetPos_mm',float('inf'),2),('PositionBand_mm',-1.,3),('Speed_mm_s',-1.,4),('AccDec_G',float('nan'),5),('PushLimit_pct',201.,6),('jog',True,7)]
for field,v,code in invalid:
    env=environment()
    if field=='unit':env['RCON1_SpeedUnit_mm_s']=v
    elif field=='jog':env['RCON1_OUT'][1].Control.JogMinus=env['RCON1_OUT'][1].Control.JogPlus=True
    else:setattr(env['RCON1_OUT'][1],field,v)
    run(blocks[0],env);run(blocks[1],env)
    env['RCON1_WriteEnable']=True;env['RCON1_AxisApply'][1]=env['RCON1_MotionPermit'][1]=True
    run(blocks[2],env)
    assert env['RCON1_EncodeError'][1]==code and not env['RCON1_EncodeOK'][1]
    assert not env['RCON1_AxisWritten'][1]
    assert all(env[raw('OUT',n)]==0x5A5A for n in range(8,16))
    tests+=1
for unit,expected in [(1.,20),(0.1,200)]:
    env=environment();env['RCON1_SpeedUnit_mm_s']=unit;run(blocks[1],env)
    assert env['RCON1_TxWord'][12]==expected;tests+=1
for name in ('RCON1_LayoutConfirmed','RCON1_ByteOrderConfirmed','RCON1_CommOK'):
    env=environment();env[name]=False
    for block in blocks:run(block,env)
    assert not any(env['RCON1_IN'][a].DataValid for a in range(1,7));tests+=1
random.seed(3089)
for _ in range(100):
    count=random.randint(-999999,999999);env=environment();env['RCON1_OUT'][1].TargetPos_mm=count/100
    run(blocks[1],env)
    assert env['RCON1_TxWord'][8]==(count&0xFFFF) and env['RCON1_TxWord'][9]==((count&0xFFFFFFFF)>>16)
    tests+=1
report={'staticReferencesMatched':len(names),'existingE001PortsChecked':144,'newGlobals':len(globals_),'newLocals':len(locals_),'controlMembers':15,'statusMembers':12,'actualOutputTargets':49,'unmodifiedOutputRanges':'OUT01～07、OUT56～71','pcSimulationChecks':tests,'byteSwapBothDirections':True,'negativePositionAndSpeed':True,'invalidInputBlocked':True,'defaultNoPhysicalWrites':True,'sysmacCompile':'未実施','machineTest':'未実施'}
(folder/'検証結果.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
package=folder.with_suffix('.zip')
assert not package.exists(),'同名ZIPがあるため中止'
with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(folder.iterdir()):
        if p.is_file():z.write(p,arcname=folder.name+'/'+p.name)
with zipfile.ZipFile(package) as z:assert z.testzip() is None
print(json.dumps(report|{'package':str(package),'bytes':package.stat().st_size},ensure_ascii=False))
