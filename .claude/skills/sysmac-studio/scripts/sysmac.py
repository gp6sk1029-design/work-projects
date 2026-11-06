"""Sysmacの読取り・候補作成・検査・公開。標準ライブラリのみ。"""
from __future__ import annotations
import argparse,base64,copy,hashlib,json,os,re,subprocess,sys,tempfile,uuid
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
from xml.etree import ElementTree as ET
from zipfile import ZipFile,ZIP_DEFLATED

def sha(data):return hashlib.sha256(data).hexdigest()
def jsha(value):return sha(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode('utf-8'))
def emit(value):print(json.dumps(value,ensure_ascii=False,indent=2))
def save_json(path,value):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
def stamp():return datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+uuid.uuid4().hex[:6]
def check(condition,message):
    if not condition:raise ValueError(message)
def safe_name(name):
    p=PurePosixPath(name)
    check(not p.is_absolute() and '..' not in p.parts and '\\' not in name and ':' not in name,'不正なエントリ名')
def without_comment(row):return {k:v for k,v in row.items() if k!='CMT'}

def reindex(row):
    n=0
    for c in row['CLs']:
        if c['__type']!='HL':c['Ix']=n;n+=1
        for p in c.get('In',[])+c.get('Out',[]):
            if p['__type']=='PRM':p['Ix']=n;n+=1
    row['LRI']=n;row['RRI']=n+1;n+=2
    for v in row.get('VLs',[]):v['Ix']=n;n+=1
    return row

class Project:
    def __init__(self,path):
        self.path=Path(path).resolve();self.directory=self.path.is_dir();self.entries={};self.infos=[];self.zip_comment=b''
        if self.directory:
            for p in sorted(self.path.rglob('*')):
                if p.is_file():
                    check(p.resolve().is_relative_to(self.path),'内部フォルダ外へのリンクは対象外')
                    self.entries[p.relative_to(self.path).as_posix()]=p.read_bytes()
        else:
            with ZipFile(self.path) as z:
                names=z.namelist();check(len(names)==len(set(names)),'ZIPエントリ重複')
                check(z.testzip() is None,'ZIP CRCエラー')
                self.infos=z.infolist();self.zip_comment=z.comment
                for info in self.infos:
                    safe_name(info.filename);self.entries[info.filename]=z.read(info.filename)
        self.fingerprint=self.current_fingerprint()
        self.sections=[];self.variable_parts={};self.solution_names=[];seen=set()
        byname={}
        for part in self.entries:byname.setdefault(PurePosixPath(part).name,[]).append(part)
        def resolve(oem,ident):
            candidate=str(PurePosixPath(oem).parent/(ident+'.xml'))
            if candidate in self.entries:return candidate
            hits=byname.get(ident+'.xml',[])
            return hits[0] if len(hits)==1 else None
        for oem,data in self.entries.items():
            if not oem.endswith('.oem'):continue
            root=ET.fromstring(data)
            def visit(node,ancestors):
                typ=node.get('type');name=node.get('name');lineage=ancestors
                if typ=='Solution' and name:self.solution_names.append(name)
                elif typ and name:lineage=ancestors+[name]
                if typ in ['PouBody','Variables'] and node.get('id'):
                    part=resolve(oem,node.get('id'))
                    if part:
                        text=self.entries[part].decode('utf-8-sig')
                        if typ=='Variables' and text.startswith('[SLWD'):self.variable_parts[part]=text
                        if typ=='PouBody' and part not in seen and text.lstrip().startswith('{'):
                            rs=[json.loads(l) for l in text.splitlines() if l.strip()]
                            if rs and all(isinstance(r,dict) and 'CLs' in r for r in rs):
                                key='/'.join(lineage)
                                self.sections.append({'key':key,'id':node.get('id'),'name':name,'part':part,'rows':rs})
                                seen.add(part)
                for child in node:visit(child,lineage)
            visit(root,[])
        check(self.sections,'ラダー節を発見できません。形式/保護/対応版を確認してください')
    def current_fingerprint(self):
        if not self.directory:return sha(self.path.read_bytes())
        values=[]
        for p in sorted(self.path.rglob('*')):
            if p.is_file():
                check(p.resolve().is_relative_to(self.path),'内部フォルダ外リンク')
                values.append((p.relative_to(self.path).as_posix(),sha(p.read_bytes())))
        return jsha(values)
    def section(self,selector):
        hits=[s for s in self.sections if selector in [s['key'],s['id'],s['part'],s['name']]]
        check(len(hits)==1,f'節が一意でありません: {selector}。inspectのkey/idを指定してください')
        return hits[0]
    def put_section(self,s):
        raw=self.entries[s['part']];text=raw.decode('utf-8-sig');old=text.splitlines(keepends=True);rs=s['rows'];lines=[]
        for i,r in enumerate(rs):
            if len(old)==len(rs) and json.loads(old[i])==r:lines.append(old[i]);continue
            ending='\r\n' if '\r\n' in text else '\n'
            lines.append(json.dumps(r,ensure_ascii=False,separators=(',',':'))+ending)
        self.entries[s['part']]=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+''.join(lines).encode('utf-8')
    def write_archive(self,destination):
        check(not self.directory,'内部全体の自動SMC2化は未検証。ベースSMC2を使用してください')
        p=Path(destination);check(p.resolve()!=self.path,'stageで元ファイルを上書きしないでください')
        check(not p.exists(),'候補の出力先が既に存在します')
        p.parent.mkdir(parents=True,exist_ok=True)
        with ZipFile(p,'x') as z:
            z.comment=self.zip_comment
            for info in self.infos:z.writestr(copy.copy(info),self.entries[info.filename])
        with ZipFile(p) as z:check(z.testzip() is None,'候補のCRCエラー')
    def declarations(self):
        # コメントを除いた宣言を、変数表のID単位で照合する。
        result={}
        for part,text in self.variable_parts.items():
            fields=[]
            for line in text.splitlines():
                if line.startswith('++D='):
                    f=dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p)
                    fields.append({k:v for k,v in f.items() if k not in ['Com','EC']})
            result[PurePosixPath(part).name]=fields
        return result
    def summary(self,details=False):
        return {'path':str(self.path),'kind':'internal-directory' if self.directory else 'smc2','sha256':self.fingerprint,
            'solutions':self.solution_names,'parts':len(self.entries),'variable_tables':len(self.variable_parts),
            'sections':[{**{k:s[k] for k in ['key','id','name','part']},'row_count':len(s['rows']),
                         **({'rows':s['rows']} if details else {})} for s in self.sections]}

def align(a,b):
    pairs=[];remaining=list(b.sections)
    for s in a.sections:
        hits=[t for t in remaining if t['id']==s['id']]
        if len(hits)!=1:hits=[t for t in remaining if t['key']==s['key']]
        check(len(hits)==1,f'対応する節を特定できません: {s["key"]}')
        t=hits[0];remaining.remove(t);pairs.append((s,t))
    check(not remaining,'参照元と対象の節数が異なります')
    return pairs

def comparison(a,b):
    sections=[];control=False;comment_count=0
    for s,t in align(a,b):
        logic=[];comments=[];count_changed=len(s['rows'])!=len(t['rows'])
        for i,(x,y) in enumerate(zip(s['rows'],t['rows'])):
            if without_comment(x)!=without_comment(y):logic.append(i)
            if x.get('CMT','')!=y.get('CMT',''):comments.append(i)
        comment_count+=len(comments);control=control or count_changed or bool(logic)
        if count_changed or logic or comments:sections.append({'key':s['key'],'row_count_changed':count_changed,'logic_rows':logic,'comment_rows':comments})
    variables_equal=a.declarations()==b.declarations()
    return {'source_sha256':a.fingerprint,'target_sha256':b.fingerprint,'sections':sections,
            'control_difference':control,'variable_declarations_equal':variables_equal,'comment_rows':comment_count}

def archive_diff(a,b):
    check(set(a.entries)==set(b.entries),'ZIPエントリ追加/削除はこの公開機能では対象外')
    parts=[];comment_only=True
    ladder={s['part']:s for s in a.sections};other={s['part']:s for s in b.sections}
    for part in a.entries:
        if a.entries[part]==b.entries[part]:continue
        parts.append(part)
        if part not in ladder or part not in other:comment_only=False;continue
        x,y=ladder[part]['rows'],other[part]['rows']
        if len(x)!=len(y) or any(without_comment(v)!=without_comment(w) for v,w in zip(x,y)):comment_only=False
    return {'changed_parts':parts,'unchanged_parts':len(a.entries)-len(parts),'comment_only':comment_only}

def stage(args):
    source=Project(args.source);check(not source.directory,'stageの元はSMC2を指定')
    plan=json.loads(Path(args.plan).read_text(encoding='utf-8-sig'))
    check(plan.get('source_sha256')==source.fingerprint,'変更計画の元SHA不一致')
    touched=set();replaced=set()
    for op in plan['operations']:
        kind=op['op']
        if kind=='replace-part':
            part=op['part'];check(part in source.entries,'新しいエントリ追加は未対応')
            check(part not in touched,'同じエントリへのreplace-partと節操作を混在させないでください')
            check(sha(source.entries[part])==op['expected_sha256'],'エントリSHA不一致')
            source.entries[part]=Path(op['file']).read_bytes();replaced.add(part);continue
        s=source.section(op['section']);rs=s['rows']
        check(s['part'] not in replaced,'同じエントリへのreplace-partと節操作を混在させないでください');touched.add(s['part'])
        if kind=='comment':
            r=rs[op['row']];check(r.get('CMT','')==op['expected'],'変更前コメント不一致');r['CMT']=op['text'].replace('\r\n','\n').replace('\n','\r\n')
        elif kind=='map-indices':
            tag=op['tag'];mapping={int(k):int(v) for k,v in op['mapping'].items()};rx=re.compile(re.escape(tag)+r'\[(\d+)\]')
            selected=op.get('rows',list(range(len(rs))))
            def change(v):
                if isinstance(v,dict):
                    for key,x in v.items():
                        if key=='Var' and isinstance(x,str) and rx.fullmatch(x):
                            n=int(rx.fullmatch(x)[1]);v[key]=tag+'['+str(mapping.get(n,n))+']'
                        elif key=='TXT' and isinstance(x,str) and rx.search(x):
                            check(op.get('include_st',False),'ST参照があるため同時修正を明示してください')
                            v[key]=rx.sub(lambda m:tag+'['+str(mapping.get(int(m[1]),int(m[1])))+']',x)
                        else:change(x)
                elif isinstance(v,list):
                    for x in v:change(x)
            for index in selected:change(rs[index])
        elif kind in ['replace-row','insert-row']:
            index=op['row']
            if kind=='replace-row':
                check(jsha(rs[index])==op['expected_sha256'],'変更前行SHA不一致');rs[index]=op['value']
            else:check(0<=index<=len(rs),'挿入行範囲外');rs.insert(index,op['value'])
            if op.get('reindex',False):reindex(rs[index])
        else:raise ValueError('未知の操作: '+kind)
        source.put_section(s)
    source.write_archive(args.output)
    # 書き出した実体を再読込みして検査する。
    candidate=Project(args.output);original=Project(args.source);diff=archive_diff(original,candidate)
    report={'source':str(original.path),'source_sha256':original.fingerprint,'candidate':str(candidate.path),
        'candidate_sha256':candidate.fingerprint,**diff,'published':False}
    save_json(args.report,report);return report

def sync_comments(target,reference):
    check(target.declarations()==reference.declarations(),'変数宣言が一致しません。コメント以外の差を取り込まないでください')
    changed=[]
    for a,b in align(target,reference):
        check(len(a['rows'])==len(b['rows']),a['key']+': 行数不一致')
        rows=[]
        for i,(x,y) in enumerate(zip(a['rows'],b['rows'])):
            check(without_comment(x)==without_comment(y),a['key']+': 制御差分あり')
            if x.get('CMT','')!=y.get('CMT',''):x['CMT']=y.get('CMT','');rows.append(i)
        if rows:target.put_section(a);changed.append({'part':a['part'],'key':a['key'],'rows':rows})
    return changed

def backup_file(path,folder):
    folder.mkdir(parents=True,exist_ok=True)
    dest=folder/(path.stem+'_'+stamp()+path.suffix)
    check(dest.resolve().parent==folder.resolve() and not dest.exists(),'履歴パス不正')
    original=path.read_bytes()
    with dest.open('xb') as f:f.write(original)
    check(dest.read_bytes()==original,'履歴保存不一致');return dest

def atomic_write(path,data,fallback=False):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    check(temp.resolve().parent==path.resolve().parent,'一時ファイルの範囲外')
    try:
        with temp.open('xb') as f:f.write(data);f.flush();os.fsync(f.fileno())
        try:os.replace(temp,path)
        except PermissionError:
            check(fallback and path.exists(),'置換できません。開いている対象の状態を確認してください')
            original=path.read_bytes()
            try:
                with path.open('r+b') as f:f.write(data);f.truncate();f.flush();os.fsync(f.fileno())
            except Exception:
                with path.open('r+b') as f:f.write(original);f.truncate()
                raise
        check(path.read_bytes()==data,'保存後バイト不一致')
    finally:
        if temp.exists():temp.unlink()

def publish(args):
    report=json.loads(Path(args.stage_report).read_text(encoding='utf-8-sig'))
    original=Project(report['source']);candidate=Project(report['candidate'])
    check(original.fingerprint==report['source_sha256'] and candidate.fingerprint==report['candidate_sha256'],'元または候補が変更されています')
    check(not original.directory and not candidate.directory,'内部更新はdirect-commentsを使用')
    diff=archive_diff(original,candidate)
    if not diff['comment_only']:check(args.allow_logic,'制御/変数変更は許可された範囲として--allow-logicを指定')
    check(args.native_report,'公開前にnativeの読込み検査結果を指定してください')
    nr=json.loads(Path(args.native_report).read_text(encoding='utf-8-sig'))
    check(nr.get('sha256')==candidate.fingerprint and nr.get('verified') is True,'native検査が候補SHAと不一致または失敗')
    dest=Path(args.destination).resolve()
    managed=Path('C:/OMRON/Data/Solution').resolve()
    check(not dest.is_relative_to(managed),'内部フォルダへSMC2を置く方法は使いません')
    check(not dest.exists() or args.overwrite,'既存ファイルへの上書き指定がありません')
    history=Path(args.history).resolve() if args.history else dest.parent/'履歴'
    check(history!=dest.parent and not dest.is_relative_to(history),'履歴と出力先が競合しています')
    backups=[]
    if dest.exists():backups.append(str(backup_file(dest,history)))
    elif original.path!=dest:backups.append(str(backup_file(original.path,history)))
    atomic_write(dest,candidate.path.read_bytes(),fallback=args.overwrite)
    archived=None;archive_error=None
    if args.archive_source and original.path!=dest:
        check(sha(original.path.read_bytes())==report['source_sha256'],'公開中に元ファイルが変更されました')
        archive_dir=original.path.parent/'履歴';archive_dir.mkdir(exist_ok=True)
        archived=archive_dir/(original.path.stem+'_'+stamp()+original.path.suffix)
        check(archived.resolve().parent==archive_dir.resolve() and not archived.exists(),'履歴の移動先が不正')
        try:os.rename(original.path,archived)
        except OSError as exc:archive_error=str(exc);archived=None
    result={'output':str(dest),'sha256':sha(dest.read_bytes()),'backups':backups,'archived_source':str(archived) if archived else None,'archive_error':archive_error,**diff,'published':True}
    save_json(args.report,result);return result

def direct_comments(args):
    target=Project(args.project);reference=Project(args.source)
    check(target.directory,'対象は登録済みプロジェクトのフォルダを指定')
    check(not Path(args.report).resolve().is_relative_to(target.path),'レポート/バックアップは内部プロジェクト外へ保存してください')
    check(args.expected_name in target.solution_names,'対象の登録プロジェクト名が一致しません')
    before=target.fingerprint;originals=dict(target.entries);changed=sync_comments(target,reference)
    result={'project':str(target.path),'solution':args.expected_name,'source':str(reference.path),'source_sha256':reference.fingerprint,
        'project_sha256_before':before,'changed':changed,'comment_rows':sum(len(c['rows']) for c in changed),'applied':False,'ui_reflection_verified':False}
    if not args.apply:save_json(args.report,result);return result
    check(args.project_closed,'今回の対象が閉じた状態である確認を--project-closedで記録してください')
    check(target.current_fingerprint()==before and reference.current_fingerprint()==reference.fingerprint,'準備中に元データが変更されました')
    if not changed:save_json(args.report,result);return result
    out=Path(args.report).resolve().parent;out.mkdir(parents=True,exist_ok=True)
    backup=out/('internal-before_'+stamp()+'.zip')
    with ZipFile(backup,'x',compression=ZIP_DEFLATED) as z:
        for part,data in originals.items():safe_name(part);z.writestr(part,data)
    with ZipFile(backup) as z:
        check(z.testzip() is None,'内部バックアップCRCエラー')
        for part,data in originals.items():check(z.read(part)==data,'内部バックアップ不一致')
    written=[]
    try:
        for c in changed:
            part=c['part'];path=(target.path/part).resolve()
            check(path.is_relative_to(target.path) and path.read_bytes()==originals[part],'内部対象が変更されています')
            atomic_write(path,target.entries[part]);written.append(part)
        check(reference.current_fingerprint()==reference.fingerprint,'参照元が変更されました')
        post=Project(target.path)
        actual=[p for p in originals if originals[p]!=post.entries.get(p)]
        check(set(post.entries)==set(originals) and set(actual)=={c['part'] for c in changed},'予定外の内部差分')
        check(not comparison(post,reference)['control_difference'],'内部更新後に制御差分')
    except Exception:
        for part in reversed(written):atomic_write(target.path/part,originals[part])
        raise
    result.update({'backup':str(backup),'backup_files':len(originals),'applied':True,'project_sha256_after':post.fingerprint,'non_comment_fields_identical':True})
    save_json(args.report,result);return result

def native(args):
    source=Path(args.source).resolve();check(source.is_file(),'nativeは検証用SMC2を指定')
    report=Path(args.report).resolve();report.parent.mkdir(parents=True,exist_ok=True)
    script=Path(__file__).with_name('native_check.ps1').resolve()
    def q(s):return "'"+str(s).replace("'","''")+"'"
    command="$ProgressPreference='SilentlyContinue'; & ([ScriptBlock]::Create([IO.File]::ReadAllText("+q(script)+',[Text.Encoding]::UTF8))) -Source '+q(source)+' -Report '+q(report)+' -InstallRoot '+q(args.install_root)+' -HelperPath '+q(script.with_name('NativeRead.cs'))
    encoded=base64.b64encode(command.encode('utf-16le')).decode('ascii')
    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-EncodedCommand',encoded],check=True)
    return json.loads(report.read_text(encoding='utf-8-sig'))

def find_projects(root,query):
    matches=[];skipped=0
    for folder in sorted(Path(root).iterdir()):
        if not folder.is_dir():continue
        oem=folder/(folder.name+'.oem')
        if not oem.exists():continue
        try:tree=ET.fromstring(oem.read_bytes())
        except (ET.ParseError,OSError):skipped+=1;continue
        for e in tree.iter():
            if e.get('type')=='Solution' and query.casefold() in e.get('name','').casefold():
                matches.append({'name':e.get('name'),'directory':str(folder),'id':e.get('id')})
    return {'matches':matches,'skipped_unreadable':skipped}

def parser():
    p=argparse.ArgumentParser(description=__doc__);sp=p.add_subparsers(dest='command',required=True)
    s=sp.add_parser('inspect');s.add_argument('source');s.add_argument('--details',action='store_true');s.add_argument('--report')
    s=sp.add_parser('find-projects');s.add_argument('--root',default='C:/OMRON/Data/Solution');s.add_argument('--query',default='')
    s=sp.add_parser('compare');s.add_argument('source');s.add_argument('target');s.add_argument('--report')
    s=sp.add_parser('stage');s.add_argument('source');s.add_argument('--plan',required=True);s.add_argument('--output',required=True);s.add_argument('--report',required=True)
    s=sp.add_parser('sync-comments');s.add_argument('--target',required=True);s.add_argument('--reference',required=True);s.add_argument('--output',required=True);s.add_argument('--report',required=True)
    s=sp.add_parser('native');s.add_argument('source');s.add_argument('--report',required=True);s.add_argument('--install-root',default='C:/Program Files (x86)/OMRON/Sysmac Studio')
    s=sp.add_parser('publish');s.add_argument('--stage-report',required=True);s.add_argument('--destination',required=True);s.add_argument('--report',required=True);s.add_argument('--native-report');s.add_argument('--history');s.add_argument('--overwrite',action='store_true');s.add_argument('--allow-logic',action='store_true');s.add_argument('--archive-source',action='store_true')
    s=sp.add_parser('direct-comments');s.add_argument('--source',required=True);s.add_argument('--project',required=True);s.add_argument('--expected-name',required=True);s.add_argument('--report',required=True);s.add_argument('--apply',action='store_true');s.add_argument('--project-closed',action='store_true')
    return p

def main():
    args=parser().parse_args();cmd=args.command
    if cmd=='inspect':result=Project(args.source).summary(args.details)
    elif cmd=='find-projects':
        result=find_projects(args.root,args.query)
    elif cmd=='compare':result=comparison(Project(args.source),Project(args.target))
    elif cmd=='stage':result=stage(args)
    elif cmd=='native':result=native(args)
    elif cmd=='publish':result=publish(args)
    elif cmd=='direct-comments':result=direct_comments(args)
    elif cmd=='sync-comments':
        target=Project(args.target);original=Project(args.target);reference=Project(args.reference)
        changed=sync_comments(target,reference);target.write_archive(args.output);candidate=Project(args.output)
        result={'source':str(original.path),'source_sha256':original.fingerprint,'candidate':str(candidate.path),'candidate_sha256':candidate.fingerprint,
                **archive_diff(original,candidate),'changed':changed,'published':False}
    if getattr(args,'report',None) and cmd in ['inspect','compare','sync-comments']:save_json(args.report,result)
    emit(result)

if __name__=='__main__':
    try:
        if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')
        main()
    except Exception as exc:
        print(json.dumps({'error':str(exc),'type':type(exc).__name__},ensure_ascii=False),file=sys.stderr);sys.exit(1)
