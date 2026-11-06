"""今回のBox行間コメントの入出力表記だけを【番号】：名称へ統一。"""
from pathlib import Path
from zipfile import ZipFile
from copy import copy,deepcopy
import io,json,re,hashlib
b=Path(__file__).parent;d=json.loads((b/'project.json').read_text(encoding='utf-8'))
p=Path(d['source']);raw=p.read_bytes();assert hashlib.sha256(raw).hexdigest()==d['sha256']
part=next(s['part'] for s in d['sections'] if s['name']=='BoxPacking_箱詰め')
changes=[]
with ZipFile(io.BytesIO(raw)) as z:
    original=z.read(part);lines=original.decode('utf-8-sig').splitlines(keepends=True);newlines=[]
    for i,line in enumerate(lines):
        r=json.loads(line);before=deepcopy(r);text=r.get('CMT','')
        text=re.sub(r'X1016・X1018：[^\r\n]*',
            '【X1016】：コンテナ排出1 戻確認\r\n【X1018】：コンテナ排出2 戻確認\r\n両方の戻完了を確認',text)
        text=text.replace('44行からは、X1010のOFFで復帰','44行からは、下記入力のOFFで復帰')
        text=text.replace('確認後、Y1204：コンテナ排出戻','確認後、排出シリンダーを戻す\r\n【Y1204】：コンテナ排出戻')
        text=re.sub(r'(?<![A-Za-z0-9_【])([XY]\d+)：',r'【\1】：',text)
        r['CMT']=text
        # 表記以外のデータには一切変更を加えない。
        a=deepcopy(before);a.pop('CMT',None);c=deepcopy(r);c.pop('CMT',None);assert a==c
        if before!=r:
            changes.append({'row':i,'before':before.get('CMT',''),'after':text})
            ending='\r\n' if line.endswith('\r\n') else '\n' if line.endswith('\n') else ''
            newlines.append(json.dumps(r,ensure_ascii=False,separators=(',',':'))+ending)
        else:newlines.append(line)
        assert not re.search(r'(?<!【)[XY]\d+',text),'未整形の入出力番号あり'
    replacement=(b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'')+''.join(newlines).encode('utf-8')
    stream=io.BytesIO()
    with ZipFile(stream,'w') as w:
        w.comment=z.comment
        for info in z.infolist():w.writestr(copy(info),replacement if info.filename==part else z.read(info.filename))
    data=stream.getvalue()
    with ZipFile(io.BytesIO(data)) as w:
        assert w.testzip() is None and w.namelist()==z.namelist()
        assert [n for n in z.namelist() if w.read(n)!=z.read(n)]==[part]
assert changes
stage=b/p.name;stage.write_bytes(data)
m={'source':str(p),'output':str(p),'staged':str(stage),'source_sha256':d['sha256'],'output_sha256':hashlib.sha256(data).hexdigest(),
    'part':part,'row_count':len(lines),'changed_rows':len(changes),'changes':changes,'comment_only':True,'native_read':None,'published':False}
(b/'verification.json').write_text(json.dumps(m,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'changed_comment_rows':len(changes),'example':changes[0],'stage':str(stage)},ensure_ascii=False))
