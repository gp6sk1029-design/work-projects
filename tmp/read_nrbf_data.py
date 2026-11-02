"""NRBFを値として読むだけの限定パーサー。アセンブリのロード・オブジェクト実行はしない。"""
import io
import struct
import math
import json
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter

class Reader:
    def __init__(self,data):
        self.stream=io.BytesIO(data)
        self.objects={}
        self.metadata={}
        self.libraries={}
        self.end=False
    def read(self,n):
        b=self.stream.read(n)
        if len(b)!=n:raise ValueError('データ不足')
        return b
    def u8(self):return self.read(1)[0]
    def i32(self):return struct.unpack('<i',self.read(4))[0]
    def string(self):
        n=0
        for i in range(5):
            b=self.u8();n|=(b&127)<<(7*i)
            if b<128:break
        if n>50_000_000:raise ValueError('文字列が過大')
        return self.read(n).decode('utf8')
    def primitive(self,t):
        formats={1:'?',2:'B',6:'d',7:'h',8:'i',9:'q',10:'b',11:'f',12:'q',13:'Q',14:'H',15:'I',16:'Q'}
        if t in formats:
            f='<'+formats[t];return struct.unpack(f,self.read(struct.calcsize(f)))[0]
        if t==3:
            b=self.read(1)
            while True:
                try:return b.decode('utf8')
                except UnicodeDecodeError:b+=self.read(1)
        if t in (5,18):return self.string()
        if t==17:return None
        raise ValueError('未対応primitive '+str(t))
    def typeinfo(self,t):
        if t in (0,7):return self.u8()
        if t==3:return self.string()
        if t==4:return (self.string(),self.i32())
        return None
    def nextvalue(self):
        while True:
            x=self.record()
            if x!=('__library__',):return x
    def classvalues(self,id,metadata):
        classname,names,types,infos=metadata
        obj={'__type':classname,'__id':id}
        self.objects[id]=obj
        for name,t,info in zip(names,types,infos):
            obj[name]=self.primitive(info) if t==0 else self.nextvalue()
        return {'__ref':id}
    def arrayvalues(self,n,t,info):
        if not 0<=n<=3_000_000:raise ValueError('配列が過大')
        values=[]
        while len(values)<n:
            v=self.primitive(info) if t==0 else self.nextvalue()
            if isinstance(v,dict) and '__nulls' in v:values.extend([None]*v['__nulls'])
            else:values.append(v)
        if len(values)!=n:raise ValueError('配列長不一致')
        return values
    def record(self):
        offset=self.stream.tell();r=self.u8()
        if r==0:
            self.root=self.i32();self.header=self.i32();self.major=self.i32();self.minor=self.i32()
            return ('__library__',)
        if r==12:
            id=self.i32();self.libraries[id]=self.string();return ('__library__',)
        if r in (4,5):
            id=self.i32();name=self.string();n=self.i32()
            names=[self.string() for _ in range(n)]
            types=[self.u8() for _ in range(n)]
            infos=[self.typeinfo(t) for t in types]
            if r==5:library=self.i32()
            metadata=(name,names,types,infos);self.metadata[id]=metadata
            return self.classvalues(id,metadata)
        if r==1:
            id=self.i32();meta=self.i32();return self.classvalues(id,self.metadata[meta])
        if r==6:
            id=self.i32();self.objects[id]=self.string();return {'__ref':id}
        if r==8:return self.primitive(self.u8())
        if r==9:return {'__ref':self.i32()}
        if r==10:return None
        if r==11:self.end=True;return None
        if r==13:return {'__nulls':self.u8()}
        if r==14:return {'__nulls':self.i32()}
        if r in (15,16,17):
            id=self.i32();n=self.i32();t=0 if r==15 else (2 if r==16 else 1)
            info=self.u8() if r==15 else None
            obj={'__array':True,'__id':id,'values':[]};self.objects[id]=obj
            obj['values']=self.arrayvalues(n,t,info)
            return {'__ref':id}
        if r==7:
            id=self.i32();kind=self.u8();rank=self.i32();sizes=[self.i32() for _ in range(rank)]
            if kind in (3,4,5):bounds=[self.i32() for _ in range(rank)]
            t=self.u8();info=self.typeinfo(t)
            obj={'__array':True,'__id':id,'sizes':sizes,'values':[]};self.objects[id]=obj
            obj['values']=self.arrayvalues(math.prod(sizes),t,info)
            return {'__ref':id}
        raise ValueError(f'未対応レコード {r} offset {offset}')
    def parse(self):
        while not self.end:self.record()
        self.consumed=self.stream.tell()
        self.trailing=len(self.stream.getbuffer())-self.consumed
        return self
    def deref(self,v):
        return self.objects[v['__ref']] if isinstance(v,dict) and set(v)=={'__ref'} else v
    def shallow(self,o):
        result={}
        for k,v in o.items():
            v=self.deref(v)
            if isinstance(v,dict):result[k]={a:b for a,b in v.items() if a.startswith('__') and a!='__array'}
            else:result[k]=v
        return result

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8')
    with zipfile.ZipFile(sys.argv[1]) as z:
        name=next(n for n in z.namelist() if n.endswith('22aaf14a-1b6b-4d6b-8ef3-92d6b44c6fa5.dat'))
        reader=Reader(z.read(name)).parse()
    print('CONSUMED',reader.consumed,'TRAILING',reader.trailing,repr(reader.stream.getbuffer()[reader.consumed:reader.consumed+40].tobytes()))
    if '--tail' in sys.argv:
        tail=reader.stream.getbuffer()[reader.consumed:].tobytes()
        ending=tail.find(b'</EcatProjectEsiData>')+len(b'</EcatProjectEsiData>')
        assert ending>20
        text=tail[:ending].decode('utf-8-sig')
        print('TAIL_HEAD',text[:2000])
        root=ET.fromstring(text)
        print('TAIL_ROOT',root.tag,root.attrib)
        print('TAIL_TAGS',Counter(e.tag for e in root.iter()))
        for e in list(root)[:6]:print('TAIL_CHILD',ET.tostring(e,encoding='unicode')[:1600])
        for v in reader.objects.values():
            if isinstance(v,dict) and v.get('StationAddress') in (1,5):
                print('SLAVE_EXTRA',v['StationAddress'],json.dumps({k:reader.deref(x) for k,x in v.items() if not ('Pdo' in k or '/Bit' in k)},ensure_ascii=False)[:2300])
        sys.exit()
    counts=Counter(v.get('__type','array') for v in reader.objects.values() if isinstance(v,dict))
    print('CLASS_COUNTS',counts)
    for id,v in reader.objects.items():
        if isinstance(v,dict) and ('Port' in v.get('__type','') or 'Slave' in v.get('__type','') or 'Project' in v.get('__type','')):
            s=reader.shallow(v)
            if 'Port' not in v.get('__type','') or id%10==0:print('OBJECT',id,json.dumps(s,ensure_ascii=False)[:1600])
