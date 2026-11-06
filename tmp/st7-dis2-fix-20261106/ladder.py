"""既存のSysmac行形式を維持するための候補編集補助。"""
from copy import deepcopy
import uuid
import sys
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm

def ld(v,x=0,y=0,nc=False):
    c={'__type':'LD','Var':v,'X':x,'Y':y}
    if nc:c['Not']=True
    return c
def st(v,x=0,y=0,mode='normal'):
    c={'__type':'ST','Var':v,'X':x,'Y':y}
    if mode=='set':c['S']=True
    if mode=='reset':c['RS']=True
    return c
def hl(x,y=0):return {'__type':'HL','X':x,'Y':y}
def vl(x,y=0):return {'X':x,'Y':y}
def row(cs,vs=(),cmt=''):return sm.reindex({'CLs':cs,'VLs':list(vs),'CMT':cmt.replace('\n','\r\n')})
def up(x,y=0):return {'__type':'F','Name':'Up','In':[{'__type':'PF','Arg':'In'}],'Out':[{'__type':'PF','Arg':''}],'Id':str(uuid.uuid4()),'X':x,'Y':y}
def calc(name,inputs,output=None,x=0,y=0):
    ps=[{'__type':'PF','Arg':'EN'}]
    for i,v in enumerate(inputs):ps.append({'__type':'PRM','Arg':'In' if name=='MOVE' else 'In'+str(i+1),'Type':'ANY' if name=='MOVE' else ('ANY_ELEMENTARY, ENUM' if name in ['=','<>'] else 'ANY_NUM'),'Var':v})
    outs=[{'__type':'PF','Arg':'ENO' if output else ''}]
    if output:outs.append({'__type':'PRM','Arg':'Out','Type':'ANY' if name=='MOVE' else 'ANY_NUM','Var':output})
    return {'__type':'F','Name':name,'In':ps,'Out':outs,'X':x,'Y':y}
def timer(var,pt,x,y=0):return {'__type':'FB','Name':'TON','Var':var,'X':x,'Y':y,'In':[{'__type':'PF','Arg':'In'},{'__type':'PRM','Arg':'PT','Type':'TIME','Var':pt}],'Out':[{'__type':'PF','Arg':'Q'},{'__type':'PRM','Arg':'ET','Type':'TIME','Var':''}]}
def branch_column(r,x,new,bypass_ys):
    for c in r['CLs']:
        if c.get('X',0)>=x:c['X']=c.get('X',0)+1
    for v in r['VLs']:
        if v.get('X',0)>=x:v['X']+=1
    r['CLs'].append(new);r['CLs'].extend(hl(x,y) for y in bypass_ys);sm.reindex(r)
def common_column(r,x,new):
    for c in r['CLs']:
        if c.get('X',0)>=x:c['X']=c.get('X',0)+1
    for v in r['VLs']:
        if v.get('X',0)>x:v['X']+=1
    r['CLs'].append(new);sm.reindex(r)
def map_var(r,old,new,kind=None):
    count=0
    for c in r['CLs']:
        if c.get('Var')==old and (kind is None or c['__type']==kind):c['Var']=new;count+=1
    return count

def any_row(terms,output,mode='normal',common=(),cmt=''):
    """直列条件のORを作り、共通条件を合流後に置く。各条件はLDかFの辞書。"""
    n=max(len(t) for t in terms);cs=[];vs=[]
    for y,term in enumerate(terms):
        for x,c in enumerate(term):
            z=deepcopy(c);z['X']=x;z['Y']=y;cs.append(z)
        cs.extend(hl(x,y) for x in range(len(term),n))
        if y<len(terms)-1:vs.append(vl(n,y))
    for offset,c in enumerate(common):z=deepcopy(c);z['X']=n+offset;z['Y']=0;cs.append(z)
    cs.append(st(output,n+len(common),mode=mode))
    return row(cs,vs,cmt)
