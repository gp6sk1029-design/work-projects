from pathlib import Path
from PIL import Image
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts');import sysmac as sm
b=Path(__file__).parent;out=Path('C:/Users/SEIGI-N13/work-projects/outputs/st7-dis2-review-20261106/recheck-02');d=json.loads((b/'snapshot.json').read_text(encoding='utf-8'))
previous=json.loads((out.parent/'recheck-01/検証結果.json').read_text(encoding='utf-8'));assert previous['sha256']==d['sha']
p=sm.Project(d['path']);assert p.fingerprint==d['sha'],'読取り後に本体が変わったため更新が必要'
images=[]
for path in sorted(out.glob('*.png')):
    with Image.open(path) as im:assert max(im.size)<=1800;images.append({'path':str(path),'size':list(im.size),'visually_inspected':True})
report='''ST7_A_Dis2_左SF排出：現在の問題点と改善案
確認日：2026-11-06／対象：登録済み20261105J、08:55:08保存
SHA256：be2074fba67262e997ff5812b96c993b800345ab9666ba4ac747e256b8914f41
前回再確認後の制御・コメント差分なし。実プログラム変更なし。
今回から更新済みSysmacスキルの描画機能を使用し、3枚の図を作成・目視確認。

【修正済み・維持する点】
15行の送り行開始はM17 AND M18のOK品限定。NGではY719を使用せず、NGの横移動枝は送り完了を待たない。31行の箱詰め取出し・Z上昇完了による待ち解除も維持。

【優先する問題】
1. 16行：OK枝のM21は送り行の開始記憶で、到達確認ではない。送り開始と同じ走査で横移動できる。
   改善：この接点をOut_CYw_Ejc_Hldr_Feed_A_F_Doneへ戻す。15行OK限定、M22自己保持、Retry/M23解除、NG枝は維持。図01参照。
2. 10/19行：RCON1_5_Auto2の通常コイル重複。10行ONの後に19行OFFで消える。
   改善：4/10/13/19/22行を動作順にAuto1～5へ分離し、受け201行へAuto5追加。図02参照。
3. 25行：送り戻Auto3の受け接点0。Output106/108は1/2だけ。
   改善：25行を既存受けへ接続済みのAuto2へ変更する案。現保存版ではAuto2の他の書込み元なし。
4. 8/26行：無ワークM10から完了へ行けず、EndにはNextCycle解除がない。
   改善：8行で実物・データなしを正常完了とし、26行の全枝へNC NextCycleを共通追加。8行M8保持もEndで解除し、NG満杯を空ワーク完了へ掛けない。図03参照。

【次に整える項目】
5. 8/18/27行のA/Bセンサー混在：Aの正常判定はBのNG満杯、Aの積み込み/回転はBのIN/Outを参照。
   改善：A側I/Oへ整理。X214は5個揃い検出とユーザー確認済み。18行OK積み込みではA満杯OFF、27行回転はA満杯ONを使う方向。回転中の積み込み禁止も必要。X215の検出対象は別途照合し、名前だけで空きと確定しない。
6. 5/7/11/14/18/20/23/25行の旧MoveDone流用と、RCON120/201のOR連続要求の再受付、121/202の今回完了誤認。
   改善：前Done OFF→今回要求受付→今回PEND OFF/ON完了→次工程を一組として整える。工程側だけ補助ビットを足したり、受け側だけ替えて完成とはしない。
7. 14行の配置前加算：Retry再進入で同じワークを再加算できる。
   改善：同一ワークの加算を1回にする。21行の5→0は、X214の満杯判定と回転中禁止が成立すれば回転前でも成立し得るため、単独不具合とは断定しない。
8. 17行の積み基準TargetPos3と、変数説明の基準2が不一致。9行は2をコンベア回収下降へ使用。
   改善：回収位置と積み1段目基準の役割を明確化し、HMI/Com/EC/式の説明を統一する。ピッチ0・段数0/6以上・算出位置範囲を確認し、理由の分かる待ち/異常表示にする。
9. 27～30行：回転両端OFFでBusyだけ保持され、指令も出ない。
   改善：X324/X325の端位置妥当性と、工程側Busy～完了の時間監視を追加する案。27行の高さ比較2個は重複であり、他軸条件だと推測して書き換えない。
10. 判定がOK1またはNG9かつDetails4/5以外のとき、行先選択なしで停止する。
   改善：行先未確定の表示・禁止条件を設ける。現Jは15行OK限定により、以前の「想定外でも送り行だけ出る」は抑止されたが、行先未定の待ち自体は残る。

【受け側の仮止め】
RCON86/167行のStartはP_Off直列。上下162～165の数値転送、左右82～84の幅/速度/加減速もP_Off。
ST7の局所修正だけでは実機移動経路は完成しない。通信・単軸・許可条件を確認して接続する。無条件P_On化は行わない。

【図と検証】
図01はOK枝・自己保持・共通解除と並列コイルを表示。NG枝は省略と明記。
図02は重複コイルの説明図。開始/保持は要約と明記し、番号分離と受け追加を記載。
図03は空ワーク合流と全枝のNext解除。8行の保持解除と25行未接続の対策も併記。
全図は提案・未反映。最大幅1740px、文字・結線・青の変更点を目視確認。
今回本体指紋は前回検算対象と同一。前回の15行32条件、16行1接点案6条件、31行64条件、End案32条件を該当範囲の根拠として使用。図生成をPLCシミュレータ・全体ビルド・実機試験の代用としない。

【振り返りレポート】
エージェント名：生産技術主任補佐PDM_261102／Codex PLC分析担当
業務・タスク内容：最新Jの現問題と改善案を新しい画像形式で提示
実行日：2026-11-06
✅ 良かった点：最新Jのハッシュ一致を確認し、修正済み15行を維持。3図で変更する接点・枝・共通解除を表示。X214とNG不要動作の仕様を反映。
⚠️ 改善点：回転側のX215検出内容は未確定。図の省略条件と全体検証の限界を明示する。
🔄 次回試すこと：16行・要求番号・戻要求・無ワーク/Endを最小修正単位で検算する。
📝 SKILL.md更新：直前の依頼で図の毎回表示とI版コメント標準を実装・3配置同期済み。今回その描画機能で3図を生成し実運用確認。
💾 MEMORY.md追記：同一Jを再確認、3画像提示、想定外判定の送り誤指令は15行OK限定で改善済みと更新。
💰 ROI評価：時間未計測、追加有料APIなし。新規描画スクリプトを3図で再利用。次回はJSON配置を再利用し差分確認に集中する。
'''
(out/'現在の問題点・改善案・振り返り.txt').write_text(report,encoding='utf-8')
sm.save_json(out/'検証結果.json',{'solution':d['solution'],'saved_date':d['date'],'sha256':p.fingerprint,'unchanged_since_previous_review':True,'source_unchanged_during_read':True,'project_modified':False,'diagrams':images,'scope':'保存済みラダーの静的照合と、同一SHAでの既存局所検算。新しい実機/全体ビルド試験なし。'})
with Path('C:/Users/SEIGI-N13/work-projects/MEMORY.md').open('a',encoding='utf-8') as f:
    f.write('\n### 2026-11-06 最新Jの問題点を標準ラダー画像で再提示（Codex PLC分析担当）\n- 再取得Jは08:55:08／be2074fb...で前回と同一、前後不変。新スキルrender_ladder.pyで3画像：16行OK完了待ち、10/19要求重複、8/26空ワークとNext解除。PNG1740幅、全図目視確認。実更新なし。\n- 15行OK限定は改善済みで維持。これにより想定外判定で送りだけ出る旧指摘も改善。ただし行先未確定の待ちは残る。その他Auto2重複/戻Auto3未接続/無ワーク完了なし/End残留/B参照/旧Done/再加算/基準説明/端位置/軸P_Offは現状として整理。X214は5個満杯、NGはY719不要、21の回転前リセット単独は誤りと断定しない。\n- 成果物outputs/st7-dis2-review-20261106/recheck-02/現在の問題点・改善案・振り返り.txtと3PNG、検証結果.json。同一SHAの前回局所検算を再利用、全体ビルド・実機なし。直前スキル整備を3図作成で実運用確認。時間未計測・追加有料APIなし。\n')
print(json.dumps({'source_unchanged':True,'images':len(images),'report':str(out/'現在の問題点・改善案・振り返り.txt')},ensure_ascii=False))
