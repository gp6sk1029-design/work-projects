// 【RCON2／Node5／5軸】直接数値指定の通信変換。加速と減速は共通値です。
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

RCON2_GwWritten := FALSE;
FOR ConvAxisIndex := INT#1 TO INT#5 DO
    RCON2_AxisWritten[ConvAxisIndex] := FALSE;
END_FOR;

IF RCON2_WriteEnable AND RCON2_LayoutConfirmed AND RCON2_ByteOrderConfirmed AND RCON2_CommOK THEN
// 共通指令はMON/RTEのみ。最初のRUN応答に必要なため、軸DataValidとは別にGwApplyで許可します。
    IF RCON2_GwApply THEN
        E005_Out_OUT00_2003_01_1 := RCON2_TxUInt[0];
        RCON2_GwWritten := TRUE;
    END_IF;

// 1軸目＝実機軸No.0。OUT08～OUT15の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON2_AxisApply[1] AND RCON2_EncodeOK[1] AND RCON2_IN[1].DataValid
       AND RCON2_MotionPermit[1] THEN
        E005_Out_OUT08_2003_09_1 := RCON2_TxUInt[8];
        E005_Out_OUT09_2003_0A_1 := RCON2_TxUInt[9];
        E005_Out_OUT10_2003_0B_1 := RCON2_TxUInt[10];
        E005_Out_OUT11_2003_0C_1 := RCON2_TxUInt[11];
        E005_Out_OUT12_2003_0D_1 := RCON2_TxUInt[12];
        E005_Out_OUT13_2003_0E_1 := RCON2_TxUInt[13];
        E005_Out_OUT14_2003_0F_1 := RCON2_TxUInt[14];
        E005_Out_OUT15_2003_10_1 := RCON2_TxUInt[15];
        RCON2_AxisWritten[1] := TRUE;
    END_IF;

// 2軸目＝実機軸No.1。OUT16～OUT23の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON2_AxisApply[2] AND RCON2_EncodeOK[2] AND RCON2_IN[2].DataValid
       AND RCON2_MotionPermit[2] THEN
        E005_Out_OUT16_2003_11_1 := RCON2_TxUInt[16];
        E005_Out_OUT17_2003_12_1 := RCON2_TxUInt[17];
        E005_Out_OUT18_2003_13_1 := RCON2_TxUInt[18];
        E005_Out_OUT19_2003_14_1 := RCON2_TxUInt[19];
        E005_Out_OUT20_2003_15_1 := RCON2_TxUInt[20];
        E005_Out_OUT21_2003_16_1 := RCON2_TxUInt[21];
        E005_Out_OUT22_2003_17_1 := RCON2_TxUInt[22];
        E005_Out_OUT23_2003_18_1 := RCON2_TxUInt[23];
        RCON2_AxisWritten[2] := TRUE;
    END_IF;

// 3軸目＝実機軸No.2。OUT24～OUT31の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON2_AxisApply[3] AND RCON2_EncodeOK[3] AND RCON2_IN[3].DataValid
       AND RCON2_MotionPermit[3] THEN
        E005_Out_OUT24_2003_19_1 := RCON2_TxUInt[24];
        E005_Out_OUT25_2003_1A_1 := RCON2_TxUInt[25];
        E005_Out_OUT26_2003_1B_1 := RCON2_TxUInt[26];
        E005_Out_OUT27_2003_1C_1 := RCON2_TxUInt[27];
        E005_Out_OUT28_2003_1D_1 := RCON2_TxUInt[28];
        E005_Out_OUT29_2003_1E_1 := RCON2_TxUInt[29];
        E005_Out_OUT30_2003_1F_1 := RCON2_TxUInt[30];
        E005_Out_OUT31_2003_20_1 := RCON2_TxUInt[31];
        RCON2_AxisWritten[3] := TRUE;
    END_IF;

// 4軸目＝実機軸No.3。OUT32～OUT39の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON2_AxisApply[4] AND RCON2_EncodeOK[4] AND RCON2_IN[4].DataValid
       AND RCON2_MotionPermit[4] THEN
        E005_Out_OUT32_2003_21_1 := RCON2_TxUInt[32];
        E005_Out_OUT33_2003_22_1 := RCON2_TxUInt[33];
        E005_Out_OUT34_2003_23_1 := RCON2_TxUInt[34];
        E005_Out_OUT35_2003_24_1 := RCON2_TxUInt[35];
        E005_Out_OUT36_2003_25_1 := RCON2_TxUInt[36];
        E005_Out_OUT37_2003_26_1 := RCON2_TxUInt[37];
        E005_Out_OUT38_2003_27_1 := RCON2_TxUInt[38];
        E005_Out_OUT39_2003_28_1 := RCON2_TxUInt[39];
        RCON2_AxisWritten[4] := TRUE;
    END_IF;

// 5軸目＝実機軸No.4。OUT40～OUT47の8ワードをまとめて代入。
// AxisApply=この軸の更新許可、EncodeOK=変換OK、DataValid=入力情報の条件確認、MotionPermit=機械側の運転許可。
// 途中1ワードだけではなく、位置・幅・速度・加減速・押付け・制御を一組として渡します。
    IF RCON2_AxisApply[5] AND RCON2_EncodeOK[5] AND RCON2_IN[5].DataValid
       AND RCON2_MotionPermit[5] THEN
        E005_Out_OUT40_2003_29_1 := RCON2_TxUInt[40];
        E005_Out_OUT41_2003_2A_1 := RCON2_TxUInt[41];
        E005_Out_OUT42_2003_2B_1 := RCON2_TxUInt[42];
        E005_Out_OUT43_2003_2C_1 := RCON2_TxUInt[43];
        E005_Out_OUT44_2003_2D_1 := RCON2_TxUInt[44];
        E005_Out_OUT45_2003_2E_1 := RCON2_TxUInt[45];
        E005_Out_OUT46_2003_2F_1 := RCON2_TxUInt[46];
        E005_Out_OUT47_2003_30_1 := RCON2_TxUInt[47];
        RCON2_AxisWritten[5] := TRUE;
    END_IF;
END_IF;
// OUT01～07、OUT48～55は、このSTからは一切書き換えません。
// 現在の実機設定・別処理の用途が未確認なので、余剰領域を勝手にゼロクリアしません。
