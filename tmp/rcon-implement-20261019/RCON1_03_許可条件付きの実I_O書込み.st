// 【RCON1／Node1／6軸】直接数値指定の通信変換。加速と減速は共通値です。
// 前提：全軸が直接数値指定、直動軸、共通8ワード＋軸番号順に各8ワード。実機の設定は別途照合。
// OUTはPLC→RCONの指令、INはRCON→PLCの現在値・状態。名前はPLCから見た方向です。
// 構造体は人が扱いやすい箱、Eで始まる変数はI/Oマップに割付済みの通信の出入口です。
// このSTは変換と許可付き代入までです。自動運転、通信正常判定、安全停止、開始受付の管理は含みません。
// Sysmacでの全体再ビルドと実機照合は未実施です。このファイルだけで実機へ転送しないでください。
// 【③ 確認・許可がそろったときだけ、実際のI/O出力変数へ書く】
// 初期状態はWriteEnable／LayoutConfirmed／ByteOrderConfirmed／CommOKがすべてFALSEです。
// これらを機械条件の確認なしに一括TRUEにしてはいけません。CommOKとMotionPermitは未作成です。
// FALSEのときは出力を更新しないだけ。前のStartやServoOnが残り得ます。停止指令ではありません。
// 安全停止・異常停止は別の設計です。書込み許可をOFFにすることを非常停止の代わりにしないでください。
// このSTだけでは動作開始しません。DSTR保持10ms以上、PEND OFF受付→DSTR OFF→PEND ON完了を管理する処理が必要です。
// GwWritten/AxisWrittenは「PLC変数へ代入した」印。通信成功・RCONの受付・移動完了を意味しません。
// 同じE始まりの出力変数を別のラダー/STから書くと、後から書いた値が優先します。出力担当を重複させないでください。

RCON1_GwWritten := FALSE;
FOR ConvAxisIndex := INT#1 TO INT#6 DO
    RCON1_AxisWritten[ConvAxisIndex] := FALSE;
END_FOR;

IF RCON1_WriteEnable AND RCON1_LayoutConfirmed AND RCON1_ByteOrderConfirmed AND RCON1_CommOK THEN
// 共通指令はMON/RTEのみ。最初のRUN応答に必要なため、軸DataValidとは別にGwApplyで許可します。
    IF RCON1_GwApply THEN
        E001_Out_OUT00_2003_01 := RCON1_TxUInt[0];
        RCON1_GwWritten := TRUE;
    END_IF;

// 1軸目＝実機軸No.0。OUT08～OUT15の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON1_AxisApply[1] AND RCON1_EncodeOK[1] AND RCON1_IN[1].DataValid
       AND RCON1_MotionPermit[1] THEN
        E001_Out_OUT08_2003_09 := RCON1_TxUInt[8];
        E001_Out_OUT09_2003_0A := RCON1_TxUInt[9];
        E001_Out_OUT10_2003_0B := RCON1_TxUInt[10];
        E001_Out_OUT11_2003_0C := RCON1_TxUInt[11];
        E001_Out_OUT12_2003_0D := RCON1_TxUInt[12];
        E001_Out_OUT13_2003_0E := RCON1_TxUInt[13];
        E001_Out_OUT14_2003_0F := RCON1_TxUInt[14];
        E001_Out_OUT15_2003_10 := RCON1_TxUInt[15];
        RCON1_AxisWritten[1] := TRUE;
    END_IF;

// 2軸目＝実機軸No.1。OUT16～OUT23の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON1_AxisApply[2] AND RCON1_EncodeOK[2] AND RCON1_IN[2].DataValid
       AND RCON1_MotionPermit[2] THEN
        E001_Out_OUT16_2003_11 := RCON1_TxUInt[16];
        E001_Out_OUT17_2003_12 := RCON1_TxUInt[17];
        E001_Out_OUT18_2003_13 := RCON1_TxUInt[18];
        E001_Out_OUT19_2003_14 := RCON1_TxUInt[19];
        E001_Out_OUT20_2003_15 := RCON1_TxUInt[20];
        E001_Out_OUT21_2003_16 := RCON1_TxUInt[21];
        E001_Out_OUT22_2003_17 := RCON1_TxUInt[22];
        E001_Out_OUT23_2003_18 := RCON1_TxUInt[23];
        RCON1_AxisWritten[2] := TRUE;
    END_IF;

// 3軸目＝実機軸No.2。OUT24～OUT31の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON1_AxisApply[3] AND RCON1_EncodeOK[3] AND RCON1_IN[3].DataValid
       AND RCON1_MotionPermit[3] THEN
        E001_Out_OUT24_2003_19 := RCON1_TxUInt[24];
        E001_Out_OUT25_2003_1A := RCON1_TxUInt[25];
        E001_Out_OUT26_2003_1B := RCON1_TxUInt[26];
        E001_Out_OUT27_2003_1C := RCON1_TxUInt[27];
        E001_Out_OUT28_2003_1D := RCON1_TxUInt[28];
        E001_Out_OUT29_2003_1E := RCON1_TxUInt[29];
        E001_Out_OUT30_2003_1F := RCON1_TxUInt[30];
        E001_Out_OUT31_2003_20 := RCON1_TxUInt[31];
        RCON1_AxisWritten[3] := TRUE;
    END_IF;

// 4軸目＝実機軸No.3。OUT32～OUT39の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON1_AxisApply[4] AND RCON1_EncodeOK[4] AND RCON1_IN[4].DataValid
       AND RCON1_MotionPermit[4] THEN
        E001_Out_OUT32_2003_21 := RCON1_TxUInt[32];
        E001_Out_OUT33_2003_22 := RCON1_TxUInt[33];
        E001_Out_OUT34_2003_23 := RCON1_TxUInt[34];
        E001_Out_OUT35_2003_24 := RCON1_TxUInt[35];
        E001_Out_OUT36_2003_25 := RCON1_TxUInt[36];
        E001_Out_OUT37_2003_26 := RCON1_TxUInt[37];
        E001_Out_OUT38_2003_27 := RCON1_TxUInt[38];
        E001_Out_OUT39_2003_28 := RCON1_TxUInt[39];
        RCON1_AxisWritten[4] := TRUE;
    END_IF;

// 5軸目＝実機軸No.4。OUT40～OUT47の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON1_AxisApply[5] AND RCON1_EncodeOK[5] AND RCON1_IN[5].DataValid
       AND RCON1_MotionPermit[5] THEN
        E001_Out_OUT40_2003_29 := RCON1_TxUInt[40];
        E001_Out_OUT41_2003_2A := RCON1_TxUInt[41];
        E001_Out_OUT42_2003_2B := RCON1_TxUInt[42];
        E001_Out_OUT43_2003_2C := RCON1_TxUInt[43];
        E001_Out_OUT44_2003_2D := RCON1_TxUInt[44];
        E001_Out_OUT45_2003_2E := RCON1_TxUInt[45];
        E001_Out_OUT46_2003_2F := RCON1_TxUInt[46];
        E001_Out_OUT47_2003_30 := RCON1_TxUInt[47];
        RCON1_AxisWritten[5] := TRUE;
    END_IF;

// 6軸目＝実機軸No.5。OUT48～OUT55の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON1_AxisApply[6] AND RCON1_EncodeOK[6] AND RCON1_IN[6].DataValid
       AND RCON1_MotionPermit[6] THEN
        E001_Out_OUT48_2003_31 := RCON1_TxUInt[48];
        E001_Out_OUT49_2003_32 := RCON1_TxUInt[49];
        E001_Out_OUT50_2003_33 := RCON1_TxUInt[50];
        E001_Out_OUT51_2003_34 := RCON1_TxUInt[51];
        E001_Out_OUT52_2003_35 := RCON1_TxUInt[52];
        E001_Out_OUT53_2003_36 := RCON1_TxUInt[53];
        E001_Out_OUT54_2003_37 := RCON1_TxUInt[54];
        E001_Out_OUT55_2003_38 := RCON1_TxUInt[55];
        RCON1_AxisWritten[6] := TRUE;
    END_IF;
END_IF;
// OUT01～07、OUT56～71は、このSTからは一切書き換えません。
// 現在の実機設定・別処理の用途が未確認なので、余剰領域を勝手にゼロクリアしません。
