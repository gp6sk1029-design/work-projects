// 【RCON2／Node5／5軸】直接数値指定の通信変換。加速と減速は共通値です。
// 前提：全軸が直接数値指定、直動軸、共通8ワード＋軸番号順に各8ワード。実機の設定は別途照合。
// OUTはPLC→RCONの指令、INはRCON→PLCの現在値・状態。名前はPLCから見た方向です。
// 構造体は人が扱いやすい箱、Eで始まる変数はI/Oマップに割付済みの通信の出入口です。
// このSTは変換と許可付き代入までです。自動運転、通信正常判定、安全停止、開始受付の管理は含みません。
// Sysmacでの全体再ビルドと実機照合は未実施です。このファイルだけで実機へ転送しないでください。
// 【② OUTの入力値を通信データへ翻訳する。まだ実出力には書かない】
// 例：RCON2_OUT[1].TargetPos_mm に25.40を設定すると、1軸目の25.40mm指令候補を作ります。
// 位置はmm、速度はmm/s、加減速はG、押付け制限は%。人が扱う単位のまま構造体へ設定します。
// TxWordは取説のbit並び、TxUIntは実通信へ渡す候補。③の許可がなければ機械には書込みません。
// EncodeError=0は数値変換可能という意味だけです。実際のストローク・速度上限・干渉は別に検査します。
// エラー番号：1速度単位、2位置、3位置決め幅、4速度、5加減速、6押付け、7ジョグ両方向。
// 速度0や幅0を正常運転値と認めたものではありません。実機に適した条件はMotionPermitの作成側で確認。
// 丸め：位置等は四捨五入、押付け制限のみ小数部を切捨てます。

ConvUnitOK := (RCON2_SpeedUnit_mm_s = LREAL#1.0) OR
              (RCON2_SpeedUnit_mm_s = LREAL#0.1);

// 共通制御：MONは論理b15、RTEは論理b13。他のbitは0。
// MONを落とす処理を安全停止として扱わないでください。
RCON2_TxWord[0] := WORD#16#0000;
IF RCON2_GwMON_Request THEN
    RCON2_TxWord[0] := RCON2_TxWord[0] OR WORD#16#8000;
END_IF;
IF RCON2_GwRTE_Request THEN
    RCON2_TxWord[0] := RCON2_TxWord[0] OR WORD#16#2000;
END_IF;

FOR ConvAxisIndex := INT#1 TO INT#5 DO
    ConvBase := INT#8 + (ConvAxisIndex - INT#1) * INT#8;
    RCON2_EncodeError[ConvAxisIndex] := UINT#0;

    // 比較で範囲を確認してから型変換するため、NaN・無限大も変換対象から外れます。
    // 位置・幅9999.99mmはこの案で採用する通信範囲の上限で、実機ストロークではありません。
    IF NOT ConvUnitOK THEN
        RCON2_EncodeError[ConvAxisIndex] := UINT#1;
    ELSIF NOT ((RCON2_OUT[ConvAxisIndex].TargetPos_mm >= LREAL#-9999.99) AND
               (RCON2_OUT[ConvAxisIndex].TargetPos_mm <= LREAL#9999.99)) THEN
        RCON2_EncodeError[ConvAxisIndex] := UINT#2;
    ELSIF NOT ((RCON2_OUT[ConvAxisIndex].PositionBand_mm >= LREAL#0.0) AND
               (RCON2_OUT[ConvAxisIndex].PositionBand_mm <= LREAL#9999.99)) THEN
        RCON2_EncodeError[ConvAxisIndex] := UINT#3;
    ELSIF NOT ((RCON2_OUT[ConvAxisIndex].Speed_mm_s >= LREAL#0.0) AND
               (RCON2_OUT[ConvAxisIndex].Speed_mm_s <= LREAL#65535.0 * RCON2_SpeedUnit_mm_s)) THEN
        RCON2_EncodeError[ConvAxisIndex] := UINT#4;
    ELSIF NOT ((RCON2_OUT[ConvAxisIndex].AccDec_G >= LREAL#0.0) AND
               (RCON2_OUT[ConvAxisIndex].AccDec_G <= LREAL#655.35)) THEN
        RCON2_EncodeError[ConvAxisIndex] := UINT#5;
    ELSIF NOT ((RCON2_OUT[ConvAxisIndex].PushLimit_pct >= LREAL#0.0) AND
               (RCON2_OUT[ConvAxisIndex].PushLimit_pct <= LREAL#200.0)) THEN
        RCON2_EncodeError[ConvAxisIndex] := UINT#6;
    ELSIF RCON2_OUT[ConvAxisIndex].Control.JogMinus AND RCON2_OUT[ConvAxisIndex].Control.JogPlus THEN
        RCON2_EncodeError[ConvAxisIndex] := UINT#7;
    END_IF;

    RCON2_EncodeOK[ConvAxisIndex] := RCON2_EncodeError[ConvAxisIndex] = UINT#0;
    IF RCON2_EncodeOK[ConvAxisIndex] THEN
    // 【数値例】TargetPos_mm=25.40→×100で2540。下位ワード2540、上位ワード0。
// 700.25mm→70025なので下位4489、上位1。65536を超えた分が上位に入ります。
// DINTは符号付きの数、DWORDは同じ32bitの模様。負数の符号を壊さず分割するために使い分けます。
// TRUNCは小数部を捨てます。正数+0.5／負数-0.5を先に行い、四捨五入を明示しています。
    // 目標位置：mmから0.01mmの符号付き整数へ。
        ConvScaled := RCON2_OUT[ConvAxisIndex].TargetPos_mm * LREAL#100.0;
        IF ConvScaled >= LREAL#0.0 THEN
            ConvPos := LINT_TO_DINT(TRUNC(ConvScaled + LREAL#0.5));
        ELSE
            ConvPos := LINT_TO_DINT(TRUNC(ConvScaled - LREAL#0.5));
        END_IF;
        // 負数を含む32bitパターンを保ち、下位・上位の16bitへ分割。
        ConvDWord := DINT_TO_DWORD(ConvPos);
        RCON2_TxWord[ConvBase] := DWORD_TO_WORD(ConvDWord AND DWORD#16#0000FFFF);
        RCON2_TxWord[ConvBase + INT#1] := DWORD_TO_WORD(SHR(ConvDWord, ULINT#16));

        // 位置決め幅：非負の内部整数としてUDINTを選定（メーカーの符号なし保証ではありません）。
        ConvBand := LINT_TO_UDINT(TRUNC(RCON2_OUT[ConvAxisIndex].PositionBand_mm * LREAL#100.0 + LREAL#0.5));
        ConvDWord := UDINT_TO_DWORD(ConvBand);
        RCON2_TxWord[ConvBase + INT#2] := DWORD_TO_WORD(ConvDWord AND DWORD#16#0000FFFF);
        RCON2_TxWord[ConvBase + INT#3] := DWORD_TO_WORD(SHR(ConvDWord, ULINT#16));

// 速度20mm/s：速度単位1.0なら20、0.1なら200を送信します。
// 加減速0.20G：×100して20。加速と減速の両方に同じ値を使います。
// 押付け50%：×255÷100=127.5を切捨てて127。押付けの使用可否・上限は実機仕様で別確認。
        // 速度は1カウント量が1.0か0.1かで値が10倍変わります。
        ConvSpeed := LINT_TO_UINT(TRUNC(RCON2_OUT[ConvAxisIndex].Speed_mm_s / RCON2_SpeedUnit_mm_s + LREAL#0.5));
        ConvAccDec := LINT_TO_UINT(TRUNC(RCON2_OUT[ConvAxisIndex].AccDec_G * LREAL#100.0 + LREAL#0.5));
        ConvPush := LINT_TO_UINT(TRUNC(RCON2_OUT[ConvAxisIndex].PushLimit_pct * LREAL#255.0 / LREAL#100.0));
        RCON2_TxWord[ConvBase + INT#4] := UINT_TO_WORD(ConvSpeed);
        RCON2_TxWord[ConvBase + INT#5] := UINT_TO_WORD(ConvAccDec);
        RCON2_TxWord[ConvBase + INT#6] := UINT_TO_WORD(ConvPush);
    END_IF;
    // 不正値の場合、数値ワードは前値保持。EncodeOK=FALSEで03の書込みを抑止。
    // 前値保持は停止指令ではありません。停止・異常処理は別途設計してください。

    // Controlを論理bitへ詰める。予約b9は必ず0。
    RCON2_TxWord[ConvBase + INT#7] := WORD#16#0000;
// b0 DSTR／Control.Start：TRUEで開始要求。受付応答と10ms以上の保持を確認してOFF。常時ONにしない。
    IF RCON2_OUT[ConvAxisIndex].Control.Start THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0001;
    END_IF;
// b1 HOME／Control.Home：TRUEで原点復帰を指令。原点復帰完了はIN側HomeDoneで確認。
    IF RCON2_OUT[ConvAxisIndex].Control.Home THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0002;
    END_IF;
// b2 STP／Control.Pause：TRUEで一時停止、FALSEで解除。非常停止・安全停止の代用ではない。
    IF RCON2_OUT[ConvAxisIndex].Control.Pause THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0004;
    END_IF;
// b3 RES／Control.Reset：TRUEでアラームリセット要求。コールドスタート級の異常には使用できない。
    IF RCON2_OUT[ConvAxisIndex].Control.Reset THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0008;
    END_IF;
// b4 SON／Control.ServoOn：TRUEでサーボON要求。ON状態はIN側ServoReadyで確認。
    IF RCON2_OUT[ConvAxisIndex].Control.ServoOn THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0010;
    END_IF;
// b5 JISL／Control.InchingSelect：TRUEは一定距離のインチング、FALSEは押している間のジョグ。
    IF RCON2_OUT[ConvAxisIndex].Control.InchingSelect THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0020;
    END_IF;
// b6 JVEL／Control.JogSpeedSelect：FALSEは速度No.26・距離No.48、TRUEは速度No.47または指令速度・距離No.49。
    IF RCON2_OUT[ConvAxisIndex].Control.JogSpeedSelect THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0040;
    END_IF;
// b7 JOG-／Control.JogMinus：TRUEで原点方向へジョグ。反対方向指令との同時ONを防ぐ。
    IF RCON2_OUT[ConvAxisIndex].Control.JogMinus THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0080;
    END_IF;
// b8 JOG+／Control.JogPlus：TRUEで反原点方向へジョグ。反対方向指令との同時ONを防ぐ。
    IF RCON2_OUT[ConvAxisIndex].Control.JogPlus THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0100;
    END_IF;
// b10 GSL0／Control.GainSelect0：GainSelect1と組合せてサーボゲインセット0～3を選ぶ。機械調整用。
    IF RCON2_OUT[ConvAxisIndex].Control.GainSelect0 THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0400;
    END_IF;
// b11 GSL1／Control.GainSelect1：GainSelect0との2bitで選択。速度指令とは別の機能。
    IF RCON2_OUT[ConvAxisIndex].Control.GainSelect1 THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#0800;
    END_IF;
// b12 PUSH／Control.PushEnable：TRUEは押付け、FALSEは通常位置決め。押付け条件は別途確認。
    IF RCON2_OUT[ConvAxisIndex].Control.PushEnable THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#1000;
    END_IF;
// b13 DIR／Control.PushDirection：CON方式押付け時、TRUEは反原点方向、FALSEは原点方向。
    IF RCON2_OUT[ConvAxisIndex].Control.PushDirection THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#2000;
    END_IF;
// b14 INC／Control.RelativeMove：FALSEは絶対座標、TRUEは現在位置からの相対移動量。
    IF RCON2_OUT[ConvAxisIndex].Control.RelativeMove THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#4000;
    END_IF;
// b15 BKRL／Control.BrakeRelease：TRUEはブレーキ強制解除。通常FALSE。縦軸では落下等の危険がある。
    IF RCON2_OUT[ConvAxisIndex].Control.BrakeRelease THEN
        RCON2_TxWord[ConvBase + INT#7] := RCON2_TxWord[ConvBase + INT#7] OR WORD#16#8000;
    END_IF;
END_FOR;

// 論理ワードから実際に送るUINTへ。INと同じ1ワード内のバイト交換を適用します。
FOR ConvWordIndex := INT#0 TO INT#47 DO
    ConvWord := RCON2_TxWord[ConvWordIndex];
    IF RCON2_SwapBytes THEN
        ConvWord := Swap(ConvWord);
    END_IF;
    RCON2_TxUInt[ConvWordIndex] := WORD_TO_UINT(ConvWord);
END_FOR;
