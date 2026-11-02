"""RCONの型・グローバル変数を別名smc2に追加する。I/O割付・ラダー・実機は変更しない。"""
from pathlib import Path
import argparse
import collections
import copy
import hashlib
import io
import json
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import quoteattr

sys.stdout.reconfigure(encoding='utf8')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('source',type=Path)
parser.add_argument('destination',type=Path)
parser.add_argument('--design',type=Path,required=True)
args=parser.parse_args()
assert args.source.resolve()!=args.destination.resolve()
assert not args.destination.exists(),'同名の保存先があるため中止'
source=args.source.read_bytes()
sha=lambda b:hashlib.sha256(b).hexdigest()
design=json.loads(args.design.read_text(encoding='utf8'))
definitions=design['defs']
expected_types=['ST_RCON_Direct_OUT_Control','ST_RCON_Direct_IN_Status','ST_RCON_Direct_OUT_Axis','ST_RCON_Direct_IN_Axis']
assert [d['name'] for d in definitions]==expected_types
assert [len(d['members']) for d in definitions]==[15,12,6,6]
assert sum(len(d['members']) for d in definitions)==39
known={'BOOL','LREAL','DINT','UINT'}
for d in definitions:
    assert len({m['name'].casefold() for m in d['members']})==len(d['members'])
    for m in d['members']:assert m['type'] in known
    known.add(d['name'])
globals_to_add=[]
for number,axes,node in [(1,6,1),(2,5,5)]:
    for direction in ('OUT','IN'):
        globals_to_add.append({'name':f'RCON{number}_{direction}','type':f'ARRAY[1..{axes}] OF ST_RCON_Direct_{direction}_Axis','comment':f'RCON{number} {axes}軸分 {"PLC→RCON 指令" if direction=="OUT" else "RCON→PLC 取得値・状態"}（内部変数・通信変換は別途）','kind':'内部構造体配列','unit':number,'nodeCandidate':node})
    globals_to_add.append({'name':f'RCON{number}_SpeedUnit_mm_s','type':'LREAL','comment':f'RCON{number} 速度の1カウント量mm/s。実機設定1.0または0.1を確認。未確認・0では使用しない。','kind':'内部補助値','unit':number,'nodeCandidate':node})
    for direction in ('OUT','IN'):
        for r in design['io'][direction][:8+8*axes]:
            name=r[0].replace('RCON1_',f'RCON{number}_',1)
            comment=f'RCON{number} '+r[1]+'（未割付・直接数値指定の設計用）'
            assert r[3]=='UINT'
            globals_to_add.append({'name':name,'type':'UINT','comment':comment,'kind':'未割付Raw','unit':number,'nodeCandidate':node,'port':r[2],'indexSubIndex':r[8],'internalPath':r[6].replace('RCON1_',f'RCON{number}_',1)})
assert len(globals_to_add)==214
assert len({x['name'].casefold() for x in globals_to_add})==214
def decode(b):
    try:t=b.decode('utf-8-sig')
    except UnicodeError:return None
    return None if '\x00' in t else t
def encode_like(b,t):return (b'\xef\xbb\xbf' if b.startswith(b'\xef\xbb\xbf') else b'')+t.encode('utf8')
def line_fields(t):
    result=[]
    for line in t.splitlines():
        if line.startswith('++D='):
            result.append(dict(p.split('=',1) for p in line[2:].split('\t') if '=' in p))
    return result
def find_entity_file(root,kind,subtype=None):
    entities=[e for e in root.iter('Entity') if e.get('type')==kind and (subtype is None or e.get('subtype')==subtype)]
    assert len(entities)==1,(kind,subtype,len(entities))
    id=entities[0].get('id')
    paths=[n for n in zin.namelist() if n.endswith('/'+id+'.xml')]
    assert len(paths)==1,(id,paths)
    return paths[0]

with zipfile.ZipFile(io.BytesIO(source)) as zin:
    assert zin.testzip() is None
    texts={n:t for n in zin.namelist() if (t:=decode(zin.read(n))) is not None}
    oem_paths=[n for n in texts if n.endswith('.oem')]
    assert len(oem_paths)==1
    oem_path=oem_paths[0]
    oem=ET.fromstring(texts[oem_path])
    global_path=find_entity_file(oem,'Variables','Global')
    # PLCのデータ型はPLC本体Entity配下から特定し、HMI側の同名表は対象外。
    global_id=Path(global_path).stem
    global_entity=next(e for e in oem.iter('Entity') if e.get('id')==global_id)
    parents={child:parent for parent in oem.iter() for child in parent}
    controller=global_entity
    while controller is not None and not (controller.tag=='Entity' and controller.get('type')=='Device'):
        controller=parents.get(controller)
    assert controller is not None,'グローバル変数のPLC本体が見つからない'
    type_entities=[e for e in controller.iter('Entity') if e.get('type')=='DataType']
    assert len(type_entities)==1
    type_path=next(n for n in texts if n.endswith('/'+type_entities[0].get('id')+'.xml'))
    original_globals=texts[global_path]
    groups=[l for l in original_globals.splitlines() if l.startswith('+GN=')]
    assert groups==['+GN=VAR_GLOBAL\tGVT=GlobalNamespaceGroup'],'想定と異なるグローバルグループ'
    original_fields=line_fields(original_globals)
    all_existing=set()
    for t in texts.values():
        if t.startswith('[SLWD'):
            all_existing.update(m.group(1).casefold() for m in re.finditer(r'(?:^|\t)N=([^\t\r\n]+)',t,re.M))
    assert not [x['name'] for x in globals_to_add if x['name'].casefold() in all_existing],'追加名が既存変数と重複'
    original_types=texts[type_path]
    type_root=ET.fromstring(original_types)
    container=type_root.find('DataType')
    existing_type_names={e.get('Name').casefold() for e in container if e.tag=='DataType'}
    assert not any(d['name'].casefold() in existing_type_names for d in definitions),'追加型名が既存型と重複'
    prototype=next(e for e in container if e.get('BaseType')=='STRUCT')
    member_prototype=next(iter(prototype))
    newline='\r\r\n' if '\r\r\n' in original_types else '\r\n'
    chunks=[]
    type_comments=['PLCからRCONへ送る制御指令BOOL群','RCONからPLCへ受ける状態BOOL群','直接数値指定 1軸分の出力指令（内部工学単位）','直接数値指定 1軸分の入力情報（内部復元値）']
    for d,comment in zip(definitions,type_comments):
        attrs=dict(prototype.attrib)
        attrs.update(Name=d['name'],Comment=comment,Order='0')
        parent=ET.Element('DataType',attrs)
        for m in d['members']:
            attributes=dict(member_prototype.attrib)
            attributes.update(Name=m['name'],BaseType=m['type'],Comment=m.get('explain') or m['comment'],Order='0')
            ET.SubElement(parent,'DataType',attributes)
        ET.indent(parent,space='  ',level=2)
        chunks.append('    '+ET.tostring(parent,encoding='unicode',short_empty_elements=True).replace('\n',newline)+newline)
    close=original_types.rfind('  </DataType>')
    assert close>=0
    new_types=original_types[:close]+''.join(chunks)+original_types[close:]
    parsed=ET.fromstring(new_types)
    assert len(parsed.find('DataType'))==len(container)+4
    assert new_types[:close]+new_types[close+len(''.join(chunks)):]==original_types,'型表の既存文字列が変わった'
    for before,after in zip(list(container),list(parsed.find('DataType'))):
        left,right=copy.deepcopy(before),copy.deepcopy(after)
        left.tail=right.tail=None
        assert ET.tostring(left)==ET.tostring(right),'既存型が変わった'
    assert original_globals.endswith('\r\n')
    added_lines=[]
    for x in globals_to_add:
        assert '\t' not in x['comment'] and '\n' not in x['comment']
        added_lines.append(f"++D={x['type']}\tN={x['name']}\tG=VAR_GLOBAL\tCom={x['comment']}\r\n")
    new_globals=original_globals+''.join(added_lines)
    assert new_globals.startswith(original_globals)
    assert line_fields(new_globals)[:len(original_fields)]==original_fields
    assert all('AT' not in f and f['G']=='VAR_GLOBAL' for f in line_fields(new_globals)[len(original_fields):])
    # プロジェクトの表示名だけを保存先に合わせる。
    solution=oem.find('Entity')
    original_name=solution.get('name')
    new_name=args.destination.stem
    match=re.search(r'<Entity\b[^>]*\btype="Solution"[^>]*>',texts[oem_path])
    assert match
    new_tag=match[0].replace('name='+quoteattr(original_name),'name='+quoteattr(new_name))
    if solution.get('DN')==original_name:new_tag=new_tag.replace('DN='+quoteattr(original_name),'DN='+quoteattr(new_name))
    new_oem=texts[oem_path][:match.start()]+new_tag+texts[oem_path][match.end():]
    manifest_path=next(n for n in texts if n.endswith('.manifest'))
    manifest=texts[manifest_path]
    assert 'solutionName='+quoteattr(original_name) in manifest
    new_manifest=manifest.replace('solutionName='+quoteattr(original_name),'solutionName='+quoteattr(new_name),1)
    updates={type_path:new_types,global_path:new_globals,oem_path:new_oem,manifest_path:new_manifest}
    for path,t in updates.items():
        if not t.startswith('[SLWD'):ET.fromstring(t)
    result=io.BytesIO()
    with zipfile.ZipFile(result,'w') as zout:
        zout.comment=zin.comment
        for info in zin.infolist():
            before=zin.read(info.filename)
            after=encode_like(before,updates[info.filename]) if info.filename in updates else before
            zout.writestr(copy.copy(info),after)
    data=result.getvalue()
    with zipfile.ZipFile(io.BytesIO(data)) as check:
        assert check.testzip() is None
        assert check.namelist()==zin.namelist()
        unchanged=[]
        for n in zin.namelist():
            if n not in updates:
                assert check.read(n)==zin.read(n)
                unchanged.append(n)
        checked_types=ET.fromstring(decode(check.read(type_path))).find('DataType')
        for d,e in zip(definitions,list(checked_types)[len(container):]):
            assert e.get('Name')==d['name'] and e.get('BaseType')=='STRUCT'
            assert [(m.get('Name'),m.get('BaseType')) for m in e]==[(m['name'],m['type']) for m in d['members']]
        checked_globals=decode(check.read(global_path))
        assert checked_globals.startswith(original_globals)
        entries=line_fields(checked_globals)
        assert len(entries)==len(original_fields)+214
        assert len({e['N'].casefold() for e in entries})==len(entries),'グローバル変数名重複'
        assert sum('AT' in e for e in entries)==sum('AT' in e for e in original_fields)
        assert ET.fromstring(decode(check.read(oem_path))).find('Entity').get('name')==new_name
        assert ET.fromstring(decode(check.read(manifest_path))).find('Solution').get('solutionName')==new_name
    assert args.source.read_bytes()==source,'原本が作業中に更新されたため中止'
    with args.destination.open('xb') as f:f.write(data)
    assert args.destination.read_bytes()==data
    report={
        '原本':str(args.source),'出力':str(args.destination),
        '原本SHA256':sha(source),'出力SHA256':sha(data),'原本不変':sha(args.source.read_bytes())==sha(source),
        '追加構造体数':4,'追加メンバー数':39,'追加グローバル変数数':214,
        '内部配列数':4,'速度補助値数':2,'Raw変数数':208,
        'RCON1軸数':6,'RCON2軸数':5,'RCON1_Raw各方向':56,'RCON2_Raw各方向':48,
        '既存グローバル変数数':len(original_fields),'更新後グローバル変数数':len(original_fields)+214,
        'I/O割付':'全て既存のまま。追加RawはATなし・未割付。','追加変数の保持':'なし（VAR_GLOBAL）。速度単位は未設定。',
        'Node1通信容量':'144Byte/144Byteを保持','Node5通信容量':'112Byte/112Byteを保持',
        '変更エントリ':list(updates),'変更エントリ数':4,'不変エントリ数':len(unchanged),
        'ラダー・ST実行コード・HMI・EtherCAT設定':'全てバイト単位で不変',
        '元の型':'sDataを含め不変','ZIP/XML/変数重複・型依存':'検証済み',
        'Sysmac再読込・全体再ビルド':'未実施。ビルド済データは原本のままなので全体再ビルド必須。',
        '実機接続・転送':'未実施','変換・起動処理':'未追加。登録だけでは動作しない。',
        '型一覧':definitions,'追加変数一覧':globals_to_add,
    }
    report_path=args.destination.with_suffix('.登録検証.json')
    assert not report_path.exists()
    with report_path.open('x',encoding='utf8') as f:json.dump(report,f,ensure_ascii=False,indent=2)
    print(json.dumps({k:v for k,v in report.items() if k not in ('型一覧','追加変数一覧')},ensure_ascii=False,indent=2))
