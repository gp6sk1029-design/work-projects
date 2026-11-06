"""登録用スキルを限定同期し、全配置と既存編集機能の不変を確認する。"""
from pathlib import Path
import hashlib,json,shutil,re
base=Path('C:/Users/SEIGI-N13/work-projects');out=base/'outputs/sysmac-skill-format-20261106'
source=base/'.claude/skills/sysmac-studio';dest=Path('C:/Users/SEIGI-N13/.codex/skills/sysmac-studio');agent=base/'.agents/skills/sysmac-studio'
before=json.loads((out/'変更前照合.json').read_text(encoding='utf-8'))
def hashit(data):return hashlib.sha256(data).hexdigest()
def files(root):return {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ['.pyc','.pyo']}
old=before[2]['files'];current=files(dest)
src=files(source)
assert set(old)<=set(current)<=set(src) and all((k in old and hashit(v)==old[k]) or v==src[k] for k,v in current.items()),'Codex登録先へ別編集が入ったため停止'
edits=[k for k in src if k not in old or hashit(src[k])!=old[k]]
expected={'SKILL.md','references/ladder-review.md','references/comment-style.md','references/ladder-diagrams.md','scripts/render_ladder.py','assets/ladder-example.json','assets/ladder-style-reference.png'}
assert set(edits)==expected
assert files(agent)==src,'先にsync_skills.pyで.agentsへ同期する'
for k in edits:
    target=(dest/k).resolve();assert target.is_relative_to(dest.resolve());target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(src[k])
assert files(dest)==files(agent)==src
# 今回の説明機能追加で既存のSMC2編集・直接反映スクリプトが変わっていないこと。
engines=['scripts/sysmac.py','scripts/NativeRead.cs','scripts/native_check.ps1','scripts/self_test.py']
assert all(hashit(src[k])==before[0]['files'][k] for k in engines)
# 相対リンク先が実在することを確認する。
for part,data in src.items():
    if not part.endswith('.md'):continue
    prose=re.sub(r'```[\s\S]*?```','',data.decode('utf-8-sig'))
    prose=re.sub(r'`[^`]*`','',prose)
    for link in re.findall(r'\]\(([^)]+)\)',prose):
        if '://' in link or link.startswith('#'):continue
        assert (source/part).parent.joinpath(link.split('#')[0]).resolve().is_file(),(part,link)
r={'date':'2026-11-06','updated_files':edits,'total_files':len(src),'three_locations_equal':True,'existing_project_editing_scripts_unchanged':engines,'image_preview_inspected':True,'image_size':[1740,1050],'skill_frontmatter_validated':True,'plc_project_modified':False,'files_sha256':{k:hashit(v) for k,v in src.items()}}
(out/'検証結果.json').write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding='utf-8')
report='''【振り返りレポート】
エージェント名：生産技術主任補佐PDM_261102／Codexスキル整備担当
業務・タスク内容：Sysmacスキルへラダー画像の毎回提示とI版コメント標準を追加
実行日：2026-11-06

✅ 良かった点
- SKILL本文の必須機能、詳細規則、実行できる描画スクリプト、再利用JSONと画像見本を一組で追加。
- コメントは大中小の流れ、改行、分岐・合流行番号、I/Oの意味、RCON軸名、短いCom/ECと全参照同期を具体化。
- 3配置15ファイル一致、既存SMC2編集機能4ファイル不変。実PLCプロジェクトの編集なし。

⚠️ 改善点
- 図の座標と文字配置は目視確認が必要。描画成功は配線や制御の検証ではない。
- 検証器はPyYAML依存かつWindows既定cp932では読めない。隔離した検証用依存と-X utf8で実行し、普段の環境やスキルへ依存一式を持ち込まなかった。

🔄 次回試すこと
- ST7など次の対策案から、現状・対策のラダー画像を本文に表示して比較する。

📝 SKILL.md更新内容
- 標準提示機能を明記。ladder-diagrams.mdとcomment-style.mdを追加し、ladder-review.mdから参照。
- render_ladder.py、ladder-example.json、ladder-style-reference.pngを追加。
- 再承認や余分な操作条件は追加せず、提案と実装を区別する既存方針を維持。

💾 MEMORY.md追記内容
- カテゴリ：Sysmacの表示・コメント標準
- 内容：ラダー分析/提案/修正報告では毎回白背景黒線青変更点のPNGを本文表示。コメントはI版形式。3配置同期と描画を確認。

💰 ROI評価
- 投じた時間・コスト：時間未計測、追加有料APIなし。
- 得られたリターン：反復描画スクリプト1本、見本2形式、コメント標準1本。次回から図と書式を作り直す手間を削減できる構成。
- 次回改善でROIを上げる方法：既存JSON配置を再利用し、制御根拠の照合と見やすさの確認へ時間を使う。
'''
(out/'更新内容・振り返り.txt').write_text(report,encoding='utf-8')
with (base/'MEMORY.md').open('a',encoding='utf-8') as f:
    f.write('\n### 2026-11-06 Sysmacスキルへ画像提示・I版コメント標準を機能追加（Codexスキル整備担当）\n- ユーザー明示：ラダー図を白背景・黒線・青変更点の添付例形式で毎回提示し、行間/変数コメントはI版BoxPacking/Destacker形式を基準にする。sysmac-studio本文に明記、references/ladder-diagrams.mdとcomment-style.md追加。ASCIIのみは不可、画像を本文埋込み、現状/提案/反映済みと略称・行番号・検証範囲を明示。\n- コメント：大工程#【番号 名称】、中工程【名称】、小工程短文。改行/空行、I/O【X/Y番号】：名称、RCON軸名、分岐/合流元と行先、短いCom/EC、外部参照同期。設定番号と実式を一致させ、コメント依頼で制御を変えない。\n- Pillowのrender_ladder.pyと配置JSON、PNG見本追加。1740×1050pxを実描画・目視確認。quick_validate成功（検証用PyYAMLはtmpへ隔離、-X utf8使用）。保守元.claude→sync_skills.pyで.agents→Codex登録先へ限定同期、15ファイル全一致。既存編集エンジン4ファイル不変、PLC実データ変更なし。\n- 成果物outputs/sysmac-skill-format-20261106/検証結果.json、更新内容・振り返り.txt、ラダー表示の標準見本.png、変更前スキル.zip。スキル追加内容は今回実装済み。時間未計測・追加有料APIなし。\n')
print(json.dumps({'changed_files':len(edits),'total_files':len(src),'all_three_equal':True,'project_editing_engine_unchanged':True},ensure_ascii=False))
