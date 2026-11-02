"""検証結果から納品用の変更内容と変数一覧を作成する。"""
from pathlib import Path
from zipfile import ZipFile
import json,re,sys
sys.stdout.reconfigure(encoding='utf-8')
base=Path(__file__).parent
d=json.loads((base/'rev_origin_design_20261023.json').read_text(encoding='utf-8'))
v=json.loads((base/'rev_origin_verification_20261023.json').read_text(encoding='utf-8'))
dst=Path(d['destination']);groups=d['groups']
with ZipFile(d['source']) as za,ZipFile(dst) as zb:
    def rows(z,n):
        return {r['N']:r for r in [dict(p.split('=',1) for p in l.lstrip('+').split('\t') if '=' in p)
            for l in z.read(n).decode('utf-8-sig').splitlines() if l.startswith('++')]}
    oldglobal=rows(za,d['paths']['global'])
    renamed=[n for n in oldglobal if '_Swv_' in n]
    details=[]
    for key in ['global','mode','device','io']:
        old=rows(za,d['paths'][key]);new=rows(zb,d['paths'][key])
        for n,row in new.items():
            if n not in old and n.replace('_Rev_','_Swv_') not in old:
                details.append((key,n,row['D'],row['G'],row.get('Com','')))
    origin=[json.loads(l) for l in zb.read(d['paths']['origin']).decode('utf-8-sig').splitlines()]
notes=[
    '反転名の統一・4組同時原点復帰 C版 変更内容',
    '作成日：2026-10-23',
    '原本：'+d['source'], '出力：'+d['destination'],
    '原本B版は前後SHA256一致。ファイル名だけCへ変更し、内部プロジェクト名は元のまま。',
    '', '【1 名前とコメント】',
    f'グローバルの既存{len(renamed)}変数名にある_Swv_を_Rev_へ変更。',
    '宣言・全ラダー/ST参照・メモリ変数メタ情報・ビルド検証キーも同じ対応で変更。',
    '行コメント・変数コメント・配列要素コメントの旋回を反転へ変更。',
    '01はST4、02はST6を表すことをコメントに追加。',
    '依頼どおりST4_A_Rev_02などの先頭ST4は維持し、02のコメントでST6を明示。',
    '', '【2 4組の対応】',
]
for i,g in enumerate(groups):
    notes.append(f"{g['label']}：{g['seq']}[1..7] / {g['axis']} / 原点復帰ラダー行{5+7*i}～{11+7*i}")
notes += [
    '', '【3 Origin_原点復帰】',
    '元の7行を基に3組21行を追加。共通開始1行・初期化4行・集約2行を加え計35行。',
    'ボタン押下の開始パルスを1回だけ算出し、4組のシーケンスを同じ走査で開始。',
    '各組は、ピックアップ戻→モータ原点復帰→ピックアップ行→チャック閉→ワーク無確認の順。',
    '各段階は各組の実際の完了信号で進む。4モータの物理的な動き出し時刻が同一という意味ではない。',
    '共通のOrigin_Busyは個別BusyのOR（個別完了は除外）から1か所で出力。',
    'OriginDoneは今回の4組の完了AND。RCON等の他装置を含む全設備の原点・安全確認ではない。',
    '共通開始時に工程1～7・各組完了・各組Busy・モータ完了保持をリセット。',
    'ボタンを押し続けても完了後の自動再起動なし。離して押し直すと新しく開始。',
    'M9999、AutoMode、Auto_A_Start、Origin_BusyがONなら新規開始しない。',
    'AutoMode中の開始禁止は今回追加した共通インターロック。自動モードを解除して原点復帰する。',
    '', '【4 関連セクション】',
    'CV2A_KED：4軸分のMC_Power・MC_HomeWithParameter・MC_SetPositionをそれぞれ独立インスタンスで登録。',
    '既存軸000の回路を基に軸001/002/003を追加。全4軸でMC_Power.Statusを原点復帰許可に使用。',
    '原点復帰パラメータも軸ごとに独立させ、元の16項目の値をそのまま引き継ぐ。',
    'モータBusyは各軸の原点復帰FBと座標設定FBのBusyを集約。通常運転を含む万能な軸停止判定ではない。',
    'Output_出力：原点復帰配列[1]の接点と立上り検出を9か所追加。元からあった3か所も維持。',
    '16か所のモータBusy接点をそれぞれのA/B・ST4/ST6の実在信号へ対応。',
    '既存の非常停止フラグ・一時停止・出力保持/リセットタイマの条件は保持。',
    'グローバル22件、工程等のローカル変数、追加FB、必要なVAR_EXTERNALを登録。',
    '旧Mtr_Flip_01_Busy/Mtr_Flip_02_Busyの宣言は削除せず保持。対象16接点は新しい軸別Busyを参照。',
    '', '【5 使用前の確認（必須）】',
    'このファイルはオフライン編集済み確認版。Sysmac Studioの読込み・全体再ビルド・実機運転は未実施。',
    'まずオフラインで開き、B版との差分と全体再ビルドの結果を確認する。旧コンパイル結果を使って転送しない。',
    '原点入力は元の例どおりZ相、開始/検出は負方向、速度40、接近1、加速100、減速200。',
    'CVD/各軸でこの原点入力が利用できるか、原点近傍/リミットの割付と極性、単位・方向・速度を個別確認する。',
    '既存の固定値STは実行ごとに値を上書きする。HMIの設定値を読み込む連携は未実装。',
    '4組同時動作による干渉、ワーク保持状態、落下防止、停止回路を確認してから低速で各組の動作を検証する。',
    '非常停止フラグの論理OFF試験は安全回路そのものの性能検証ではない。安全回路は変更していない。',
    'PLC接続・転送・実機操作はしていない。',
    '', '【6 検証】',
    f"宣言/型/配線/論理の確認：{v['検証項目数']}チェック。ZIP正常、XML/ラダーJSON読戻し正常。",
    '実ラダーのブール論理走査で、同時開始・段階進行・3組だけの完了抑止・ワーク有抑止・再開始・停止条件を確認。',
    '追加出力接点9組の導通と非常停止/モータBusy/一時停止時の遮断を確認。',
    'この走査は独自の接点/コイル論理検査であり、SysmacシミュレータやMC命令の実行検証ではない。',
    f"既存191エントリ中21件変更、170件不変。追加インラインSTのブックマーク3件を追加。",
    '機器・軸・EtherCAT設定のdatは全件同一、既存変数の型/割付/保持/初期値を保持。',
    'STSdbは同梱ライブラリでメモリコピーを読み、現行Variable参照登録が0件であることを確認。',
    'STSdb内の旧名バイト列は過去の格納領域に残るが、バイナリを直接置換せずDB全体を原本保持。',
    'ソースの宣言と参照には_Swv_や旋回を残していない。クロスリファレンスはSysmac再読込/ビルドで再生成する。',
    '原本SHA256：'+v['原本SHA256'], 'C版SHA256：'+v['出力SHA256'],
    '', '【7 原点復帰ラダーの行コメント】',
]
notes += [f"{i}: {r.get('CMT','')}" for i,r in enumerate(origin)]
report=dst.with_suffix('.変更内容.txt')
report.write_text('\n'.join(notes)+'\n',encoding='utf-8-sig')
listing=['変数一覧（新規および名前変更）','作成日：2026-10-23','',
         '【新規宣言】','区分 / 名前 / 型 / 宣言区分 / コメント']
listing += [' / '.join(x) for x in details]
listing += ['', '【既存グローバル変数の名前変更】']
listing += [n+' → '+n.replace('_Swv_','_Rev_') for n in renamed]
listing += ['', '【ST4/ST6の対応】']
listing += [g['seq']+'：'+g['label']+' / '+g['axis'] for g in groups]
dst.with_suffix('.変数一覧.txt').write_text('\n'.join(listing)+'\n',encoding='utf-8-sig')
dst.with_suffix('.検証結果.json').write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'変更内容':str(report),'変数一覧':str(dst.with_suffix('.変数一覧.txt')),
    '名前変更グローバル数':len(renamed),'新規宣言数（外部参照含む）':len(details)},ensure_ascii=False,indent=2))
