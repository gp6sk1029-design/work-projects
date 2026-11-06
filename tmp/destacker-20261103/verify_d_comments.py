"""C/Dを再読込みし、コメント以外の全定義と命令が同一であることを独立確認する。"""
from pathlib import Path
from lxml import etree as E
import json,zipfile,re,hashlib,sys,collections
from comment_plan import DESTACKER_ROWS,OUTPUT_ROWS,RCON_ROWS,VARIABLES
sys.stdout.reconfigure(encoding='utf-8')
b=Path(__file__).parent
meta=json.loads((b/'D版コメント追加検証.json').read_text(encoding='utf-8'))
inspection=json.loads((b/'コメント追加前調査.json').read_text(encoding='utf-8'))
src=Path(meta['source']);dst=Path(meta['output'])
plans={'Destacker_段バラシ':DESTACKER_ROWS,'Output_出力':OUTPUT_ROWS,'RCON_IAI':RCON_ROWS}
rowchanges=0;comchanges=0;ecchanges=0;found=set()
def strip_rows(rows):return [{k:v for k,v in r.items() if k!='CMT'} for r in rows]
def pairs(line):
 result={}
 for p in line.split('\t'):
  if '=' in p:
   k,v=p.split('=',1);assert k not in result;result[k]=v
 return result
def ecs(value):
 root=E.fromstring(value.encode('utf-8'));assert root.tag=='ECs'
 entries={}
 for e in root:
  assert e.tag=='EC' and e.get('EK') not in entries
  entries[e.get('EK')]=dict(e.attrib)
 return entries
with zipfile.ZipFile(src) as a,zipfile.ZipFile(dst) as z:
 assert a.testzip() is None and z.testzip() is None and a.namelist()==z.namelist()
 changed=[p for p in a.namelist() if a.read(p)!=z.read(p)]
 assert changed==meta['changed_parts'] and len(changed)==8
 for p in changed:
  old=a.read(p).decode('utf-8-sig');new=z.read(p).decode('utf-8-sig')
  assert len(old.splitlines())==len(new.splitlines())
  if old.startswith('[SLWD'):
   for line1,line2 in zip(old.splitlines(),new.splitlines()):
    f1=pairs(line1);f2=pairs(line2)
    assert [t for t in line1.split('\t') if not t.startswith(('Com=','EC='))]==[t for t in line2.split('\t') if not t.startswith(('Com=','EC='))]
    name=f1.get('N')
    if line1==line2:continue
    assert name in VARIABLES;found.add(name)
    plan=VARIABLES[name]
    if f1.get('Com')!=f2.get('Com'):
     assert f2['Com']==plan['Com'];comchanges+=1
    e1=ecs(f1.get('EC','<ECs/>'));e2=ecs(f2.get('EC','<ECs/>'))
    assert set(e1)<=set(e2)
    for key,attrs in e1.items():
     assert {k:v for k,v in attrs.items() if k!='C'}=={k:v for k,v in e2[key].items() if k!='C'}
    for key,attrs in e2.items():
     if e1.get(key)!=attrs:
      n=int(re.fullmatch(r'\[(\d+)\]',key)[1]);assert attrs['C']==plan['EC'][n];ecchanges+=1
    for n,comment in plan.get('EC',{}).items():assert e2[f'[{n}]']['C']==comment
  else:
   before=[json.loads(l) for l in old.splitlines()];after=[json.loads(l) for l in new.splitlines()]
   assert strip_rows(before)==strip_rows(after),'コメント以外の回路要素が変化'
   section=next(s for s,n in inspection['sections'].items() if n==p)
   for i,(r1,r2) in enumerate(zip(before,after)):
    if r1.get('CMT')!=r2.get('CMT'):
     assert r2['CMT']==plans[section][i];rowchanges+=1
 assert (rowchanges,comchanges,ecchanges)==(48,52,131)
 assert found==set(VARIABLES)
 assert hashlib.sha256(src.read_bytes()).hexdigest()==meta['source_sha256']
 assert hashlib.sha256(dst.read_bytes()).hexdigest()==meta['output_sha256']
 # 要確認事項を回路そのものと照合する。
 part=inspection['sections']['Destacker_段バラシ']
 ds=[json.loads(l) for l in z.read(part).decode('utf-8-sig').splitlines()]
 assert not any(e.get('Name')=='MOVE' for e in ds[7]['CLs'])
 assert '目標位置の代入はない' in ds[7]['CMT']
 assert '[1]付きで参照' in ds[18]['CMT']
 result={'検証':'合格','D版':str(dst),'D版SHA256':meta['output_sha256'],'C版不変':True,'回路命令と分岐とST実行コード':'全一致','変数名・型・I/O割付・保持設定':'全一致','追加整理した行コメント':rowchanges,'変数コメント更新箇所':comchanges,'要素コメント更新箇所':ecchanges,'対象変数名数':len(found),'異なる配列要素数':63,'対象外部品':202,'ZIP_CRC':'正常','要確認事項':2,'SysmacStudioでの表示・読込み・再ビルド':'未実施'}
 (b/'D版独立コメント検証.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
 print(json.dumps(result,ensure_ascii=False))
 text=['D版 コメント追加内容・確認事項（2026-11-03）','',f'ファイル：{dst.name}','対象：段バラシとその出力・RCON接続先','回路ロジック、条件、変数名、型、I/O割付、保持設定はC版から変更なし。','行コメント48行、変数コメント52箇所、配列要素コメント131箇所を追加・整理。','変数名として25種類、配列要素として63種類（うち段24・外向き指令16）の用途を記載。','','【要確認事項】','1. 段バラシ7行目：元の行名はセイフティPos移動だが、Auto[3]を出す行に目標位置のMOVEがない。','   コメントにはそのまま記載。意図する移動先の確認が必要。コードは変更していない。','2. 段バラシ18・19行目：HMI_RCON2_5_OUT_TargetPosはLREALの単一値として宣言され、回路では[1]付きで参照されている。','   単一値として使うのか配列にするのかは未確定のため、型や参照は変更していない。','','【既存回路の範囲を明記した箇所】','Output270行：空コンテナ戻の駆動はAuto[1]～[3]を受けるが、この異常監視行はAuto[1]のみ。','今回の作業はコメント追加なので、監視条件の変更は行っていない。','','【行コメント一覧】']
 for s,plan in plans.items():
  text+=['',s]
  for row,comment in plan.items():text+=[f'表示行{row}：',comment,'']
 text+=['【変数・配列要素コメント一覧】']
 for name,plan in VARIABLES.items():
  text+=['',name]
  if 'Com' in plan:text+=[plan['Com']]
  for i,c in plan.get('EC',{}).items():text+=[f'  [{i}] {c}']
 text+=['','【検証範囲】','C版とD版を保存後に再読込みし、コメント以外の全命令と全宣言を比較。','他202部品は全バイト一致、ZIP CRC正常、C版ハッシュ不変。','Sysmac Studio上での表示・読み込み・全体再ビルドは未確認。PLC接続・転送なし。','','【振り返りレポート】','エージェント名：生産技術主任補佐PDM_261102／PLCコメント整備担当','業務・タスク内容：行コメント・変数コメント・配列要素コメントの追加整理','実行日：2026-11-03','','✅ 良かった点','- 実際の命令・接点・タイマ・参照先を読んで、段24工程と指令16種類の用途を記載。','- コメント以外の全命令と全宣言がC版と一致することを別スクリプトで検証。','- 目標位置代入なしと型/添字の不整合は推測で直さず、要確認として明示。','','⚠️ 改善点','- Sysmac Studioでのコメントの表示状態と全体再ビルドは未確認。','- 部門SKILL.mdは未整備のため既存手順とルートMEMORYを参照した。','','🔄 次回試すこと','- 実機の意図を確認できた位置設定だけ、要確認コメントを確定した説明へ更新する。','','📝 SKILL.md更新提案','- 該当セクション：PLCコメント整備手順（今後整備）','- 変更内容：行CMTとSLWDのCom/ECだけを編集し、外部変数表とグローバル表の要素コメントを同期する。命令から断定できない移動先・型の不整合は明記する。提案のみ。','','💾 MEMORY.md追記内容','- カテゴリ：コメントのみの編集・実コードと説明の照合','- 内容：48行・25変数・63要素の整備、全ロジック不変、確認が必要な2点、C版保全を記録。','','💰 ROI評価',f'- 投じた時間・コスト：生成処理{meta["seconds"]}秒、追加有料APIなし。全対応時間は未計測。','- 得られたリターン：段番号・指令の用途をプログラム内で確認可能にし、48行の処理説明を追加整理。','- 次回改善でROIを上げる方法：行番号・コイル・位置設定・受信先を対応表にしてコメントの更新漏れを減らす。']
 (b/'D版コメント一覧・確認事項と振り返り.txt').write_text('\n'.join(text)+'\n',encoding='utf-8')
