"""ZIP/XML/構成差分を読取り検査し、原本保持を記録する。"""
from pathlib import Path
import hashlib,json,re,sys,xml.etree.ElementTree as ET,zipfile
sys.stdout.reconfigure(encoding='utf-8')
BASE=Path(__file__).resolve().parent
old_report=json.loads((BASE.parent/'section-organize-20261028/verification.json').read_text(encoding='utf-8-sig'))
paths={'I':Path(old_report['source']),'J':Path(old_report['destination'])}
result={}
for version,path in paths.items():
 digest=hashlib.sha256(path.read_bytes()).hexdigest()
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  assert len(z.namelist())==len(set(z.namelist()))
  xml_ok=0;rungs=0;bad_xml=[]
  for name in z.namelist():
   try:text=z.read(name).decode('utf-8-sig')
   except UnicodeError:continue
   if '\x00' in text:continue
   if text.lstrip().startswith('<'):
    try:ET.fromstring(text);xml_ok+=1
    except ET.ParseError as error:bad_xml.append({'entry':name,'error':str(error)})
   if text.startswith('{"CLs"'):
    rr=[json.loads(line) for line in text.splitlines() if line.strip()];rungs+=len(rr)
  result[version]={'path':str(path),'sha256':digest,'zip_crc_ok':True,'xml_parsed':xml_ok,'xml_errors':bad_xml,'rungs':rungs}
assert result['J']['sha256']==old_report['output_sha256'],'配布Jから更新あり'
assert result['I']['sha256']==old_report['source_sha256'],'原本Iから更新あり'
result['native_connection_audit']=json.loads((BASE/'connection_results.json').read_text(encoding='utf-8-sig'))
result['observed_logs']={
 'file':r'C:\Users\SEIGI-N13\AppData\Roaming\OMRON\CXAP\Log\SysmacStudioErrorTrace.log',
 'display_crashes':['2026-10-29T08:41:52.349','2026-10-29T08:43:28.845'],
 'exception':'System.ArgumentOutOfRangeException',
 'method':'LadderLayoutStrategy.AssignXCoordinate',
 'user_report':'リビルドではエラー表示なし、Error_エラー処理を開くと異常終了',
}
result['findings']={
 'section':'Error_エラー処理','row':11,'variables':'HMI_Message_Request[101]～[107]',
 'confirmed_defect':'メーカー変換後モデルでコイルの出力接続点/出力辺が0。正常な他コイルには出力接続あり。',
 'display_code_evidence':'AssignXCoordinateはコイルの出力辺GetOutputs(vertex)[0]を参照する経路を持つ。',
 'causal_status':'不正接続7件は確認済み。利用者の発生画面とログに整合し有力な原因。UIでの修正前後再現検証は未実施。',
 'inherited_by_i_and_j':True,'source_projects_modified':False,'repair_performed':False,
}
(BASE/'diagnosis.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k in ('I','J','findings')},ensure_ascii=False,indent=2))
