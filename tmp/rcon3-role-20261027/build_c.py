"""RCON1_3の用途コメントのみを変更し、最新B版を保持してC版へ保存する。"""
from pathlib import Path
import collections,copy,hashlib,html,json,re,shutil,sys,zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
DATA=json.loads((BASE/'inspection.json').read_text(encoding='utf-8'))
SOURCE=Path(DATA['source']);DEST=SOURCE.with_name(SOURCE.name.replace('20261027B','20261027C'))
STAGED=BASE/DEST.name;REPORT=BASE/'verification.json'
NEW='SF/NG2仕分け(左右)'
OLD=['ストックフォルダ(SF)／NG2排出(送り)','ストックフォルダ(SF) or NG2排出(送り)',
     'SF/NG2排出(送り)','SF/NG2送り']
def relevant(context,comment):
    return bool(re.search(r'RCON1_3(?!\d)',context+' '+comment) or
                re.fullmatch(r'RCON1_(?:IN|OUT)\[3\](?:\..*)?',context) or
                re.search(r'RCON1_(?:IN|OUT)_Axis3_',context))
def replace_comment(context,c):
    if not relevant(context,c):return c
    for old in OLD:c=c.replace(old,NEW)
    return c
def fields(l):return dict(p.split('=',1) for p in l[2:].split('\t') if '=' in p)
def attr_value(c):return escape(c,{'"':'&quot;','\r':'&#xD;','\n':'&#xA;'})
def build():
    assert not DEST.exists(),'既存C版を上書きしません'
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==DATA['sha256'],'調査後にB版が更新されました'
    with zipfile.ZipFile(SOURCE) as z:
        assert z.testzip() is None
        original={n:z.read(n) for n in z.namelist()};infos=z.infolist();comment=z.comment
    changes={};records=[]
    def update(n,kind,context,c):
        new=replace_comment(context,c)
        if new!=c:records.append({'entry':n,'kind':kind,'context':context,'before':c,'after':new})
        return new
    for n,t in DATA['texts'].items():
        changed=t
        if t.startswith('[SLWD'):
            ls=[]
            for line in t.splitlines(keepends=True):
                if line.startswith('++D='):
                    end=line[len(line.rstrip('\r\n')):];p=fields(line.rstrip('\r\n'));parts=line.rstrip('\r\n')[2:].split('\t')
                    for i,part in enumerate(parts):
                        if part.startswith('Com='):parts[i]='Com='+update(n,'Com',p['N'],part[4:])
                        elif part.startswith('EC='):
                            def ec(m):
                                e=ET.fromstring(m[0]);before=e.get('C','')
                                after=update(n,'EC',p['N']+e.get('EK',''),before)
                                if after==before:return m[0]
                                return re.sub(r'\bC="[^"]*"',lambda _:'C="'+attr_value(after)+'"',m[0],count=1)
                            parts[i]='EC='+re.sub(r'<EC\b[^>]*?\s*/>',ec,part[3:])
                    line='++'+'\t'.join(parts)+end
                    after=fields(line.rstrip('\r\n'))
                    assert {k:v for k,v in p.items() if k not in ('Com','EC')}=={k:v for k,v in after.items() if k not in ('Com','EC')}
                    if p.get('EC'):
                        a,b=ET.fromstring(p['EC']),ET.fromstring(after['EC'])
                        assert len(a)==len(b)
                        for ae,be in zip(a,b):
                            aa,ba=dict(ae.attrib),dict(be.attrib);aa.pop('C',None);ba.pop('C',None);assert aa==ba
                ls.append(line)
            changed=''.join(ls)
        elif n in DATA['ladder_counts']:
            lines=t.splitlines(keepends=True)
            for i,line in enumerate(lines):
                if not line.strip():continue
                row=json.loads(line);old=copy.deepcopy(row)
                if 'CMT' in row:row['CMT']=update(n,'CMT',str(i),row['CMT'])
                if row!=old:
                    end=line[len(line.rstrip('\r\n')):]
                    lines[i]=json.dumps(row,ensure_ascii=False,separators=(',',':'))+end
                a,b=dict(old),dict(row);a.pop('CMT',None);b.pop('CMT',None);assert a==b
            changed=''.join(lines)
        elif t.lstrip().startswith('<'):
            try:ET.fromstring(t)
            except ET.ParseError:continue
            def xml_tag(m):
                if not re.search(r'\bComment="',m[0]):return m[0]
                refs=dict((k,html.unescape(v)) for k,v in re.findall(r'\b(Name|Address)="([^"]*)"',m[0]))
                context=refs.get('Address','')+' '+refs.get('Name','')
                c=html.unescape(re.search(r'\bComment="([^"]*)"',m[0])[1])
                new=update(n,'Comment',context,c)
                if new==c:return m[0]
                return re.sub(r'\bComment="[^"]*"',lambda _:'Comment="'+attr_value(new)+'"',m[0],count=1)
            changed=re.sub(r'<[A-Za-z_][^<>]*>',xml_tag,t)
            a,b=ET.fromstring(t),ET.fromstring(changed)
            assert len(list(a.iter()))==len(list(b.iter()))
            for ae,be in zip(a.iter(),b.iter()):
                aa,ba=dict(ae.attrib),dict(be.attrib);aa.pop('Comment',None);ba.pop('Comment',None)
                assert ae.tag==be.tag and aa==ba and ae.text==be.text
        if changed!=t:changes[n]=changed
    expected={(x['entry'],x['kind'],x['context'],x['comment']) for x in DATA['found']}
    actual={(x['entry'],x['kind'],x['context'],x['before']) for x in records}
    assert actual==expected,('調査対象との不一致',expected-actual,actual-expected)
    assert len(records)==76 and len(changes)==6
    assert all(NEW in r['after'] and not any(old in r['after'] for old in OLD) for r in records)
    assert not any(n.endswith(('.dat','.oem')) for n in changes)
    with zipfile.ZipFile(STAGED,'w') as z:
        z.comment=comment
        for info in infos:
            raw=original[info.filename]
            if info.filename in changes:raw=(b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'')+changes[info.filename].encode('utf-8')
            z.writestr(info,raw)
    # 保存後も、許可した用途表記の差分だけであることをバイト列の逆置換で独立検証。
    with zipfile.ZipFile(STAGED) as z:
        assert z.testzip() is None and z.namelist()==list(original)
        for n,raw in original.items():
            if n not in changes:assert z.read(n)==raw
            else:
                after=z.read(n).decode('utf-8-sig')
                expected_raw=raw.decode('utf-8-sig')
                # フィールド別の構造比較は上で実施。全非コメントデータの追加差分を禁止する。
                if n in DATA['ladder_counts']:
                    before_rows=[json.loads(l) for l in expected_raw.splitlines() if l.strip()]
                    after_rows=[json.loads(l) for l in after.splitlines() if l.strip()]
                    for ar,br in zip(before_rows,after_rows):
                        ar.pop('CMT',None);br.pop('CMT',None);assert ar==br
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==DATA['sha256']
    report={'source':str(SOURCE),'destination':str(DEST),'staged':str(STAGED),'source_sha256':DATA['sha256'],
            'output_sha256':hashlib.sha256(STAGED.read_bytes()).hexdigest(),'entries':len(original),'changed_entries':list(changes),
            'comment_changes':records,'comment_change_count':len(records),'change_counts':dict(collections.Counter(r['kind'] for r in records)),
            'ladder_counts':DATA['ladder_counts'],'native_validation':None,'comments_only_verified':True,'other_axes_unchanged':True,
            'names_logic_types_and_io_unchanged':True,'app_build_verified':False,'machine_transfer_performed':False}
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('comment_changes','ladder_counts')},ensure_ascii=False,indent=2))

def publish():
    r=json.loads(REPORT.read_text(encoding='utf-8-sig'))
    assert r['native_validation'] and all('PARSE_FAIL=0 MODEL_FAIL=0' in v for v in r['native_validation'].values())
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest()==r['source_sha256']
    assert hashlib.sha256(STAGED.read_bytes()).hexdigest()==r['output_sha256']
    with STAGED.open('rb') as a,DEST.open('xb') as b:shutil.copyfileobj(a,b)
    assert hashlib.sha256(DEST.read_bytes()).hexdigest()==r['output_sha256']
    r['published']=True;REPORT.write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
    print('保存完了',DEST)
if __name__=='__main__':publish() if '--publish' in sys.argv else build()
