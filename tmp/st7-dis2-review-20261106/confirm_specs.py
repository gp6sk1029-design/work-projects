from pathlib import Path
import json
base=Path('C:/Users/SEIGI-N13/work-projects')
p=base/'outputs/st7-dis2-review-20261106/検証結果.json'
d=json.loads(p.read_text(encoding='utf-8'))
d['user_confirmed']={'X214':'5個そろった状態を検出','NG_Y719':'NG排出時は送り行を使用しない'}
d['pending_questions']=['X215の検出対象と回転時の信号遷移']
d['corrected_findings']={'16行':'NGの送りDone迂回は仕様どおり','15行':'送り行開始をOK選択M18に限定する案','21行':'回転前カウント0戻し単独では不具合と断定しない','27行':'X214の5個検出で回転開始を判断でき、CT=5追加は必須ではない'}
p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
with (base/'MEMORY.md').open('a',encoding='utf-8') as f:
    f.write('\n- ST7レビュー後の仕様確定・訂正（2026-11-06、Codex）：ユーザーがX214は5個揃い検出、NG排出ではY719送り行を使用しないと回答。16行のNG枝送りDone迂回は正常と訂正、Done共通化案は不採用。15行の送り行開始をM17 AND M18のOK限定へ修正する案。18/27のB参照はAへ整理し、27はX214で5個判定可能、CT=5追加を必須にしない。21の回転前0戻し単独は不具合と断定しない。満杯・回転中の積み込み禁止と再試行二重加算を別に確認。X215の詳細は未確認。報告・検証結果更新、実プログラム変更なし。学び：分岐で完了待ちを迂回していても、動作不要の仕様なら正しい。出力開始側との整合を確認する。\n')
print('報告・検証結果・MEMORY更新済み。実プログラム変更なし。')
