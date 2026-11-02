"""既存インラインSTだけを補完し、原本を保持したB版を作成する。"""
import copy
import hashlib
import json
import re
import sys
from pathlib import Path
from zipfile import ZipFile

sys.stdout.reconfigure(encoding='utf-8')
desktop = Path(r'C:\Users\SEIGI-N13\Desktop')
sources = list(desktop.glob('3089-2603A_*_20261023A.smc2'))
assert len(sources) == 1
src = sources[0]
dst = src.with_name(src.stem[:-1] + 'B.smc2')
listing = dst.with_suffix('.原点復帰ST.txt')
report = dst.with_suffix('.変更内容.txt')
assert not any(p.exists() for p in (dst, listing, report)), '既存ファイルを上書きしない'
source_hash = hashlib.sha256(src.read_bytes()).hexdigest()
assert source_hash == 'd8dfca05c8219bb73852f1a967beda36d36a7523e7d1b87e029ef6ee3feb1198'

st = '''//MC_HomeWithParameterの原点復帰パラメータ設定
//添付画像の参考値を設定（タッチパネルとの連携は未実装）
//実機使用前に原点信号・方向・速度・軸の単位を確認する
//このSTだけでは原点復帰を開始しない
//このST実行時は以下の固定値で上書きする

//原点復帰方式：近傍退避・原点近傍入力ON
Homing_Para_Stm.HomingMode := _mcHomeSwTurnHomeSwOn;
//原点入力：Z相（実機の信号対応を要確認）
Homing_Para_Stm.HomeInput := _mcZPhase;
//原点復帰の開始方向：負方向
Homing_Para_Stm.StartDir := _mcNegativeDirection;
//原点入力の検出方向：負方向
Homing_Para_Stm.HomeDir := _mcNegativeDirection;
//正側リミット入力時：即停止して反転
Homing_Para_Stm.PosiLmtMode := _mcRevImmediateStop;
//負側リミット入力時：即停止して反転
Homing_Para_Stm.NegaLmtMode := _mcRevImmediateStop;

//原点復帰速度 [指令単位/s]
Homing_Para_Stm.Vel := LREAL#40;
//原点近傍での接近速度 [指令単位/s]
Homing_Para_Stm.ApproachVel := LREAL#1;
//原点復帰の加速度 [指令単位/s^2]
Homing_Para_Stm.Acc := LREAL#100;
//原点復帰の減速度 [指令単位/s^2]
Homing_Para_Stm.Dec := LREAL#200;
//ジャーク [指令単位/s^3]：0はジャーク制御なし
Homing_Para_Stm.Jerk := LREAL#0;

//原点入力マスク距離 [指令単位]：今回の方式では未使用
Homing_Para_Stm.Mask := LREAL#0;
//原点確定後の現在位置 [指令単位]
Homing_Para_Stm.Offset := LREAL#0;
//押当て時間 [ms]：今回の方式では未使用
Homing_Para_Stm.PushTime := UINT#0;
//原点検出後の補正移動量 [指令単位]：0は補正移動なし
Homing_Para_Stm.Compensation := LREAL#0;
//原点補正移動時の速度 [指令単位/s]
Homing_Para_Stm.CompensationVel := LREAL#10;
'''.replace('\n', '\r\n')

expected_values = {
    'HomingMode': '_mcHomeSwTurnHomeSwOn', 'HomeInput': '_mcZPhase',
    'StartDir': '_mcNegativeDirection', 'HomeDir': '_mcNegativeDirection',
    'PosiLmtMode': '_mcRevImmediateStop', 'NegaLmtMode': '_mcRevImmediateStop',
    'Vel': 'LREAL#40', 'ApproachVel': 'LREAL#1', 'Acc': 'LREAL#100',
    'Dec': 'LREAL#200', 'Jerk': 'LREAL#0', 'Mask': 'LREAL#0',
    'Offset': 'LREAL#0', 'PushTime': 'UINT#0',
    'Compensation': 'LREAL#0', 'CompensationVel': 'LREAL#10',
}
assignments = re.findall(r'^Homing_Para_Stm\.(\w+) := ([^;]+);$', st, re.M)
# CRLFの末尾を許容して、各メンバーが一度だけ設定されていることを確認する。
assignments = re.findall(r'^Homing_Para_Stm\.(\w+) := ([^;]+);\r?$', st, re.M)
assert len(assignments) == len(dict(assignments)) == 16
assert dict(assignments) == expected_values

with ZipFile(src) as zin:
    assert zin.testzip() is None
    payload = {info.filename: zin.read(info) for info in zin.infolist()}
    target = next(n for n, b in payload.items()
                  if b'"__type":"IST"' in b and b'Homing_Para_Stm' in b)
    declaration = next(b.decode('utf-8-sig') for b in payload.values()
                       if b'++D=_sHOMING_REF\tN=Homing_Para_Stm\tG=VAR' in b)
    assert declaration.count('N=Homing_Para_Stm\t') == 1
    old_bytes = payload[target]
    old_text = old_bytes.decode('utf-8-sig')
    before = [json.loads(line) for line in old_text.splitlines() if line.strip()]
    assert len(before) == 2
    assert len(before[0]['CLs']) == 1
    cell = before[0]['CLs'][0]
    assert cell['__type'] == 'IST' and cell['TXT'].rstrip().endswith('Homing_Para_Stm')
    assert before[1]['CLs'][0]['Name'] == 'MC_HomeWithParameter'
    assert before[1]['CLs'][0]['Var'] == 'Stm_A_Rev_Axis000'
    expected = copy.deepcopy(before)
    expected[0]['CLs'][0]['TXT'] = st
    # 既存のJSON書式・改行・位置・IDを保持し、TXT文字列だけを置換する。
    serialized = json.dumps(st, ensure_ascii=False).replace('/', '\\/')
    serialized = serialized.replace('\\r', '\\u000d').replace('\\n', '\\u000a')
    new_text, count = re.subn(r'"TXT":\s*"(?:\\.|[^"\\])*"',
                              lambda _: '"TXT":' + serialized, old_text, count=1)
    assert count == 1
    after = [json.loads(line) for line in new_text.splitlines() if line.strip()]
    assert after == expected
    assert after[1] == before[1], '未完成FBを変更しない'
    payload[target] = new_text.encode('utf-8-sig')
    with ZipFile(dst, 'w') as zout:
        zout.comment = zin.comment
        for info in zin.infolist():
            zout.writestr(info, payload[info.filename])

with ZipFile(src) as zin, ZipFile(dst) as zout:
    assert zout.testzip() is None
    assert zin.namelist() == zout.namelist()
    changed = [n for n in zin.namelist() if zin.read(n) != zout.read(n)]
    assert changed == [target]
    reread = [json.loads(line) for line in zout.read(target).decode('utf-8-sig').splitlines() if line.strip()]
    assert reread == expected
    assert len(zin.namelist()) == 188
assert hashlib.sha256(src.read_bytes()).hexdigest() == source_hash

notes = '\r\n'.join([
    '原点復帰パラメータST追加（20261023A→20261023B）',
    '原本：' + str(src), '出力：' + str(dst),
    '対象：OtherDeviceの既存CV2A_KEDセクション、回路0のインラインST。',
    'Homing_Para_Stm（既存ローカル変数、_sHOMING_REF）へ16メンバーを設定。',
    '設定値は添付画像を踏襲。開始・検出方向のコメントは実指定に合わせ負方向へ訂正。',
    '速度40、接近速度1、加速度100、減速度200、ジャーク0、補正速度10。',
    '距離・速度の単位は軸の指令単位に従う。degree軸ならdegreeとdegree/s等。',
    '画像の冒頭にあったタッチパネル連携は実装されていないため、その旨を明記。',
    'このSTが実行されるたびに固定値を上書きする。HMIから直接編集する用途には未対応。',
    'Z相を原点入力とする設定は参考画像の指定。CVD側の信号対応・配線・原点近傍設定は未検証。',
    '回路1のMC_HomeWithParameterは原本から未接続であり、今回は変更していない。',
    '要修正：回路1のFBインスタンス名Stm_A_Rev_Axis000は既存軸変数_sAXIS_REFと同名。',
    '実行回路を完成させる際は、別名のMC_HomeWithParameter型インスタンスを登録して接続する必要がある。',
    'Axis・HomingParameter・Execute・応答の接続は追加していない。自動始動処理なし。',
    '既存変数・I/O・タスク・機器設定・回路1を保持。原本A版は変更していない。',
    'ZIP内は対象STを含む1エントリのみ変更。他187エントリはバイト一致。',
    'ファイル名末尾のみBへ変更し、プロジェクト内部名は保持。',
    'ZIP CRC、JSON構造、16項目とリテラル型、原本ハッシュを検証済み。',
    'Sysmac読込み・全体再ビルド・実機動作は未検証。PLC接続・転送なし。',
    'このB版はST設定部を補完したもの。原点復帰運転が完成した版ではない。',
    '公式参照：W508-E1-28 3-42～3-45 _sHOMING_REF / MC_HomeWithParameter',
    'https://files.omron.eu/downloads/latest/manual/en/w508_nj_nx-series_motion_control_instructions_reference_manual_en.pdf?v=3',
    '原本SHA256：' + source_hash,
    '出力SHA256：' + hashlib.sha256(dst.read_bytes()).hexdigest(),
])
listing.write_bytes(b'\xef\xbb\xbf' + st.encode('utf-8'))
report.write_bytes(b'\xef\xbb\xbf' + (notes + '\r\n').encode('utf-8'))
print(notes)
