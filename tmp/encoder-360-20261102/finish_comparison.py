"""Artifact Toolで作成した比較系列だけを元グラフに反映し、他のZIP部品を保持する。"""
from pathlib import Path
from lxml import etree as E
from copy import deepcopy, copy
import zipfile, json, hashlib, shutil, sys
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).parent
info=json.loads((base/'comparison_inspection.json').read_text(encoding='utf-8'))
prior=json.loads((base/'comparison_verification.json').read_text(encoding='utf-8')) if (base/'comparison_verification.json').exists() else None
src=Path(info['source'])
assert hashlib.sha256(src.read_bytes()).hexdigest()==info['sha256'], '作業中に原本が更新されたため停止'
backup=base/'G列変更前バックアップ.xlsx'
if not backup.exists(): shutil.copy2(src,backup)
assert hashlib.sha256(backup.read_bytes()).hexdigest()==info['sha256']
ns={'c':'http://schemas.openxmlformats.org/drawingml/2006/chart','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
with zipfile.ZipFile(src) as original, zipfile.ZipFile(base/'comparison_authored.xlsx') as authored:
 target='xl/charts/chart5.xml'
 root=E.fromstring(original.read(target))
 plot=root.find('.//c:scatterChart',ns)
 existing=plot.findall('c:ser',ns)
 assert len(existing)==2
 assert existing[0].findtext('c:tx/c:v',namespaces=ns)=='回転（1°毎）１（移動平均）'
 added=[]
 for name in authored.namelist():
  if '/charts/chart' in name and name.endswith('.xml'):
   ar=E.fromstring(authored.read(name))
   added.extend(ar.xpath('//c:ser[c:tx/c:v="比較データ（G列）"]',namespaces=ns))
 assert len(added)==1
 series=deepcopy(added[0])
 for tag in ['idx','order']: series.find('c:'+tag,ns).set('val','1')
 # 元グラフと同じ横軸参照・キャッシュを使い、0～359度をそのまま対応させる。
 oldx=series.find('c:xVal',ns)
 assert oldx is not None
 series.replace(oldx,deepcopy(existing[0].find('c:xVal',ns)))
 y=series.find('c:yVal/c:numRef',ns)
 assert y is not None and y.findtext('c:f',namespaces=ns).replace("'",'')=='Sheet1!$G$4:$G$363'
 pts=y.findall('c:numCache/c:pt',ns)
 assert len(pts)==360
 for p,v in zip(pts,info['G']):
  assert abs(float(p.findtext('c:v',namespaces=ns))-float(v['value']))<1e-12
 marker=series.find('c:marker',ns)
 if marker is not None: series.remove(marker)
 # 散布図の系列要素順に合わせ、マーカーなしをxValの直前へ置く。
 series.insert(series.index(series.find('c:xVal',ns)),deepcopy(existing[0].find('c:marker',ns)))
 plot.replace(existing[1],series)
 legend=root.find('.//c:legend',ns)
 legend.find('c:legendPos',ns).set('val','b')
 layout=legend.find('c:layout',ns)
 if layout is not None: legend.remove(layout)
 overlay=legend.find('c:overlay',ns)
 if overlay is not None: overlay.set('val','0')
 assert E.tostring(plot.findall('c:ser',ns)[0])==E.tostring(existing[0])
 outdir=base.parent.parent/'outputs/encoder-comparison-20261102'
 outdir.mkdir(exist_ok=True,parents=True)
 output=outdir/'1029_1332エンコーダ基準_比較グラフ.xlsx'
 patch=E.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
 with zipfile.ZipFile(output,'w',compression=zipfile.ZIP_DEFLATED) as dest:
  for item in original.infolist(): dest.writestr(copy(item),patch if item.filename==target else original.read(item.filename))
 with zipfile.ZipFile(output) as result:
  assert result.namelist()==original.namelist()
  changed=[name for name in original.namelist() if original.read(name)!=result.read(name)]
  assert changed==[target], changed
  for name in result.namelist():
   if name.endswith('.xml') or name.endswith('.rels'): E.fromstring(result.read(name))
  resultroot=E.fromstring(result.read(target))
  rs=resultroot.findall('.//c:scatterChart/c:ser',ns)
  assert len(rs)==2
  assert E.tostring(rs[0])==E.tostring(existing[0])
  assert rs[1].xpath('.//a:srgbClr/@val',namespaces=ns)==['ED7D31']
  assert rs[1].xpath('.//a:prstDash/@val',namespaces=ns) in [[],['solid']]
  assert len(rs[1].findall('c:yVal/c:numRef/c:numCache/c:pt',ns))==360
  assert len(rs[1].findall('c:xVal/c:numRef/c:numCache/c:pt',ns))==360
 desktop=Path(info['desktop'])
 if desktop.exists():
  assert hashlib.sha256(desktop.read_bytes()).hexdigest()==info['sha256'], '保存先が外部更新されたため停止'
  try: shutil.copy2(output,desktop)
  except PermissionError:
   desktop=desktop.with_name(desktop.stem+'_G列.xlsx')
   assert not desktop.exists(), '別名保存先が既に存在するため停止'
   shutil.copy2(output,desktop)
 else: shutil.copy2(output,desktop)
 report={'source':str(src),'output':str(output),'desktop':str(desktop),'source_sha256':info['sha256'],'output_sha256':hashlib.sha256(output.read_bytes()).hexdigest(),'changed_parts':changed,'all_other_parts_byte_identical':True,'original_series_preserved':True,'added_points':360,'x_degrees':[0,359],'y_reference':'Sheet1!$G$4:$G$363','color':'ED7D31','line':'solid','all_XML_parse':True,'native_excel_open_check':'未実施'}
 (base/'comparison_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(report,ensure_ascii=False))
