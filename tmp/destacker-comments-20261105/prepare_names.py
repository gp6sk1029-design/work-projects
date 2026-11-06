from pathlib import Path,PurePosixPath
from xml.etree import ElementTree as E
import sys,json,re
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
import sysmac as sm
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
inside=sm.Project(d['internal']);base=sm.Project(b/'I_comments.smc2')
assert not sm.comparison(inside,base)['control_difference'] and inside.declarations()==base.declarations()
names={1:'初回確認開始',2:'初回の爪保持',3:'初回の位置判定',4:'初回安全位置あり',5:'初回安全位置なし',6:'初回の爪戻し',7:'初回安全位置移動',8:'初回1段目移動',9:'初回コンテナ保持',10:'初回安全位置戻り',11:'初回の送り戻し',12:'通常サイクル開始',13:'送り戻り待ち',14:'コンテナ確認中',15:'コンテナ確認OK',16:'1段目位置へ移動',17:'コンテナ切り離し',18:'段積み判定',19:'2段以上',20:'1段のみ',21:'2段目位置へ移動',22:'上段コンテナ保持',23:'安全・排出位置移動',24:'送り行待ち',25:'送り戻り待ち',26:'初回確認済み',27:'初回安全 前完了解除',28:'初回1段 前完了解除',29:'初回戻り 前完了解除',30:'1段目 前完了解除',31:'2段目 前完了解除',32:'排出 前完了解除'}
comments={'Destacker_M':'段バラシ工程','Destacker_Init_Busy':'初回処理中','Destacker_End':'1サイクル完了','Destacker_Error':'方向・1段目確認異常'}
ops=[];targets=[]
for internal_part,content in inside.variable_parts.items():
    changed=False;result=[];changes=[]
    for line in content.splitlines(keepends=True):
        ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
        raw=line.rstrip('\r\n')
        if not raw.startswith('++D='):result.append(line);continue
        f=dict(t.split('=',1) for t in raw[2:].split('\t') if '=' in t);name=f.get('N')
        if name not in comments:result.append(line);continue
        updates={'Com':comments[name]}
        if name=='Destacker_M':
            ec=E.fromstring(f.get('EC','<ECs/>'))
            for n,text in names.items():
                matches=[x for x in ec if x.get('EK')==f'[{n}]'];assert len(matches)<=1
                node=matches[0] if matches else E.SubElement(ec,'EC',{'EK':f'[{n}]'})
                node.set('C',text)
            updates['EC']=E.tostring(ec,encoding='unicode',short_empty_elements=True)
        new=raw
        for key,value in updates.items():
            rx=r'\t'+re.escape(key)+r'=[^\t\r\n]*'
            if re.search(rx,new):new=re.sub(rx,lambda _:'\t'+key+'='+value,new)
            else:new+='\t'+key+'='+value
        if new!=raw:changed=True;changes.append(name)
        result.append(new+ending)
    if not changed:continue
    matches=[x for x in base.variable_parts if PurePosixPath(x).name==PurePosixPath(internal_part).name];assert len(matches)==1
    part=matches[0];old=base.entries[part];payload=(b'\xef\xbb\xbf' if old.startswith(b'\xef\xbb\xbf') else b'')+''.join(result).encode('utf-8')
    fn=b/('names_'+PurePosixPath(internal_part).name);fn.write_bytes(payload)
    ops.append({'op':'replace-part','part':part,'expected_sha256':sm.sha(old),'file':str(fn.resolve())})
    targets.append({'internal_part':internal_part,'base_part':part,'names':changes})
assert {x['internal_part'] for x in targets}=={'b530d740-9d69-41c3-974a-97c06e823eb2.xml','86df70c5-aaad-4d2c-bba7-04264d7b7f32.xml','f07dd06c-505c-431b-b9fc-098949805b4e.xml'},targets
sm.save_json(b/'name-plan.json',{'source_sha256':base.fingerprint,'operations':ops})
sm.save_json(b/'name-meta.json',{'internal_before':inside.fingerprint,'targets':targets,'element_comments':names})
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-comments-20261105')
(out/'工程ビットのコメント一覧.txt').write_text('\n'.join(f'Destacker_M[{n}]：{v}' for n,v in names.items())+'\n',encoding='utf-8')
print(json.dumps({'variable_tables':targets,'element_count':len(names),'all_variable_declarations_unchanged_before_stage':inside.declarations()==base.declarations()},ensure_ascii=False))
