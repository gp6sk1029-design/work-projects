// 【RCON1／Node1／6軸】直接数値指定の通信変換。加速と減速は共通値です。
// 前提：全軸が直接数値指定、直動軸、共通8ワード＋軸番号順に各8ワード。実機の設定は別途照合。
// OUTはPLC→RCONの指令、INはRCON→PLCの現在値・状態。名前はPLCから見た方向です。
// 構造体は人が扱いやすい箱、Eで始まる変数はI/Oマップに割付済みの通信の出入口です。
// このSTは変換と許可付き代入までです。自動運転、通信正常判定、安全停止、開始受付の管理は含みません。
// Sysmacでの全体再ビルドと実機照合は未実施です。このファイルだけで実機へ転送しないでください。
// 【① 入力を読む → 単位を戻す → 構造体INへ入れる】
// まず72個のUINTをRxRawへコピーします。ここでは実入力変数へ一切代入しません。
// 軸データはIN08～55。IN56～71は読みますが、用途を勝手に決めません。
// RxRawは通信のまま、RxWordは必要なら上下バイトを入れ替えた後の値です。
// 注意：確認前も数値・状態は仮に復元します。DataValid=FALSEの値で機械を動かさないでください。
RCON1_RxRaw[0] := E001_In_IN00_2004_01;
RCON1_RxRaw[1] := E001_In_IN01_2004_02;
RCON1_RxRaw[2] := E001_In_IN02_2004_03;
RCON1_RxRaw[3] := E001_In_IN03_2004_04;
RCON1_RxRaw[4] := E001_In_IN04_2004_05;
RCON1_RxRaw[5] := E001_In_IN05_2004_06;
RCON1_RxRaw[6] := E001_In_IN06_2004_07;
RCON1_RxRaw[7] := E001_In_IN07_2004_08;
RCON1_RxRaw[8] := E001_In_IN08_2004_09;
RCON1_RxRaw[9] := E001_In_IN09_2004_0A;
RCON1_RxRaw[10] := E001_In_IN10_2004_0B;
RCON1_RxRaw[11] := E001_In_IN11_2004_0C;
RCON1_RxRaw[12] := E001_In_IN12_2004_0D;
RCON1_RxRaw[13] := E001_In_IN13_2004_0E;
RCON1_RxRaw[14] := E001_In_IN14_2004_0F;
RCON1_RxRaw[15] := E001_In_IN15_2004_10;
RCON1_RxRaw[16] := E001_In_IN16_2004_11;
RCON1_RxRaw[17] := E001_In_IN17_2004_12;
RCON1_RxRaw[18] := E001_In_IN18_2004_13;
RCON1_RxRaw[19] := E001_In_IN19_2004_14;
RCON1_RxRaw[20] := E001_In_IN20_2004_15;
RCON1_RxRaw[21] := E001_In_IN21_2004_16;
RCON1_RxRaw[22] := E001_In_IN22_2004_17;
RCON1_RxRaw[23] := E001_In_IN23_2004_18;
RCON1_RxRaw[24] := E001_In_IN24_2004_19;
RCON1_RxRaw[25] := E001_In_IN25_2004_1A;
RCON1_RxRaw[26] := E001_In_IN26_2004_1B;
RCON1_RxRaw[27] := E001_In_IN27_2004_1C;
RCON1_RxRaw[28] := E001_In_IN28_2004_1D;
RCON1_RxRaw[29] := E001_In_IN29_2004_1E;
RCON1_RxRaw[30] := E001_In_IN30_2004_1F;
RCON1_RxRaw[31] := E001_In_IN31_2004_20;
RCON1_RxRaw[32] := E001_In_IN32_2004_21;
RCON1_RxRaw[33] := E001_In_IN33_2004_22;
RCON1_RxRaw[34] := E001_In_IN34_2004_23;
RCON1_RxRaw[35] := E001_In_IN35_2004_24;
RCON1_RxRaw[36] := E001_In_IN36_2004_25;
RCON1_RxRaw[37] := E001_In_IN37_2004_26;
RCON1_RxRaw[38] := E001_In_IN38_2004_27;
RCON1_RxRaw[39] := E001_In_IN39_2004_28;
RCON1_RxRaw[40] := E001_In_IN40_2004_29;
RCON1_RxRaw[41] := E001_In_IN41_2004_2A;
RCON1_RxRaw[42] := E001_In_IN42_2004_2B;
RCON1_RxRaw[43] := E001_In_IN43_2004_2C;
RCON1_RxRaw[44] := E001_In_IN44_2004_2D;
RCON1_RxRaw[45] := E001_In_IN45_2004_2E;
RCON1_RxRaw[46] := E001_In_IN46_2004_2F;
RCON1_RxRaw[47] := E001_In_IN47_2004_30;
RCON1_RxRaw[48] := E001_In_IN48_2004_31;
RCON1_RxRaw[49] := E001_In_IN49_2004_32;
RCON1_RxRaw[50] := E001_In_IN50_2004_33;
RCON1_RxRaw[51] := E001_In_IN51_2004_34;
RCON1_RxRaw[52] := E001_In_IN52_2004_35;
RCON1_RxRaw[53] := E001_In_IN53_2004_36;
RCON1_RxRaw[54] := E001_In_IN54_2004_37;
RCON1_RxRaw[55] := E001_In_IN55_2004_38;
RCON1_RxRaw[56] := E001_In_IN56_2004_39;
RCON1_RxRaw[57] := E001_In_IN57_2004_3A;
RCON1_RxRaw[58] := E001_In_IN58_2004_3B;
RCON1_RxRaw[59] := E001_In_IN59_2004_3C;
RCON1_RxRaw[60] := E001_In_IN60_2004_3D;
RCON1_RxRaw[61] := E001_In_IN61_2004_3E;
RCON1_RxRaw[62] := E001_In_IN62_2004_3F;
RCON1_RxRaw[63] := E001_In_IN63_2004_40;
RCON1_RxRaw[64] := E001_In_IN64_2004_41;
RCON1_RxRaw[65] := E001_In_IN65_2004_42;
RCON1_RxRaw[66] := E001_In_IN66_2004_43;
RCON1_RxRaw[67] := E001_In_IN67_2004_44;
RCON1_RxRaw[68] := E001_In_IN68_2004_45;
RCON1_RxRaw[69] := E001_In_IN69_2004_46;
RCON1_RxRaw[70] := E001_In_IN70_2004_47;
RCON1_RxRaw[71] := E001_In_IN71_2004_48;

// 取説の論理ワードへ正規化。Swapは1ワード内の上下バイト交換です。
// SwapBytesは推測で設定せず、既知の位置とbitで実機照合してください。
FOR ConvWordIndex := INT#0 TO INT#71 DO
    RCON1_RxWord[ConvWordIndex] := UINT_TO_WORD(RCON1_RxRaw[ConvWordIndex]);
    IF RCON1_SwapBytes THEN
        RCON1_RxWord[ConvWordIndex] := Swap(RCON1_RxWord[ConvWordIndex]);
    END_IF;
END_FOR;

ConvUnitOK := (RCON1_SpeedUnit_mm_s = LREAL#1.0) OR
              (RCON1_SpeedUnit_mm_s = LREAL#0.1);

// 【①-2 共通状態】IN00はユニット全体、IN01は各軸のリンク情報です。
// TestABit(ワード, bit番号)は、そのスイッチがONかをBOOLで取り出す命令です。
// 例：IN01のb0は軸No.0→配列[1]、b1は軸No.1→配列[2]。配列番号と実機軸番号は1違います。
// 共通固定領域。ここで使うbit番号は取説の論理bitです（MJ0384 6-24～6-25）。
RCON1_GwRun := TestABit(RCON1_RxWord[0], USINT#15);
RCON1_GwControllerCommLatch := TestABit(RCON1_RxWord[0], USINT#14);
RCON1_GwAxisCommError := TestABit(RCON1_RxWord[0], USINT#13);
RCON1_GwManual := TestABit(RCON1_RxWord[0], USINT#12);
RCON1_GwHeavyAlarm := TestABit(RCON1_RxWord[0], USINT#11);
RCON1_GwLightAlarm := TestABit(RCON1_RxWord[0], USINT#10);
RCON1_GwSystemStop := TestABit(RCON1_RxWord[0], USINT#8);
RCON1_GwAlarmCode := WORD_TO_UINT(RCON1_RxWord[0] AND WORD#16#00FF);
FOR ConvWordIndex := INT#0 TO INT#4 DO
    RCON1_PowerStateRaw[ConvWordIndex] := RCON1_RxWord[ConvWordIndex + INT#2];
END_FOR;

// 【①-3 軸ごとに同じ読取りを繰り返す】
// FORは1～6軸を順番に処理します。ConvBaseはその軸の先頭番号です。
// 計算：8+(軸番号-1)×8。1軸目=8、2軸目=16、3軸目=24。先頭8ワードは共通領域です。
FOR ConvAxisIndex := INT#1 TO INT#6 DO
    ConvBase := INT#8 + (ConvAxisIndex - INT#1) * INT#8;
    RCON1_AxisLinked[ConvAxisIndex] :=
        TestABit(RCON1_RxWord[1], INT_TO_USINT(ConvAxisIndex - INT#1));

// 例：下位2540／上位0なら32bit値2540→25.40mm。
// 上位を16bit左に動かして下位とORで重ねます。SHLが左シフト、ORがビットの合成です。
// 負位置はDWORD_TO_DINTで符号を復元。下位62996／上位65535なら-2540→-25.40mm。
    // 現在位置：下位・上位を結合、符号付き32bitとして解釈、0.01mmをmmへ。
    ConvDWord := SHL(WORD_TO_DWORD(RCON1_RxWord[ConvBase + INT#1]), ULINT#16)
                 OR WORD_TO_DWORD(RCON1_RxWord[ConvBase]);
    RCON1_IN[ConvAxisIndex].ActualPos_mm :=
        DINT_TO_LREAL(DWORD_TO_DINT(ConvDWord)) * LREAL#0.01;

    // 電流：32bitのmA。RCON-PCでは指令電流であり、実測トルクではありません。
    ConvDWord := SHL(WORD_TO_DWORD(RCON1_RxWord[ConvBase + INT#3]), ULINT#16)
                 OR WORD_TO_DWORD(RCON1_RxWord[ConvBase + INT#2]);
    RCON1_IN[ConvAxisIndex].Current_mA := DWORD_TO_DINT(ConvDWord);

    // 現在速度：16bitの負数をINTとして読む。UINTのまま速度にしません。
    IF ConvUnitOK THEN
        RCON1_IN[ConvAxisIndex].ActualSpeed_mm_s :=
            INT_TO_LREAL(WORD_TO_INT(RCON1_RxWord[ConvBase + INT#4])) * RCON1_SpeedUnit_mm_s;
    END_IF;
    // 単位不明のとき速度は前値を保持し、DataValidはFALSEにします。
    // 軸内の+5ワードは予約のため値を使用しません。
    RCON1_IN[ConvAxisIndex].AlarmCode := WORD_TO_UINT(RCON1_RxWord[ConvBase + INT#6]);

// 例：Status.ServoReady=TRUEは「サーボON状態を受信した」という意味。
// OUT側Control.ServoOn=TRUEは「サーボONを要求する」という意味で、指令と結果を区別します。
    // 状態ワード：12個のBOOLへ分解。予約b6,b9～11は使いません。
    RCON1_IN[ConvAxisIndex].Status.PositionDone := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#0);
    RCON1_IN[ConvAxisIndex].Status.HomeDone := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#1);
    RCON1_IN[ConvAxisIndex].Status.Moving := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#2);
    RCON1_IN[ConvAxisIndex].Status.Alarm := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#3);
    RCON1_IN[ConvAxisIndex].Status.ServoReady := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#4);
    RCON1_IN[ConvAxisIndex].Status.PushMiss := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#5);
    RCON1_IN[ConvAxisIndex].Status.OverloadWarning := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#7);
    RCON1_IN[ConvAxisIndex].Status.CommandDone := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#8);
    RCON1_IN[ConvAxisIndex].Status.Zone1 := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#12);
    RCON1_IN[ConvAxisIndex].Status.Zone2 := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#13);
    RCON1_IN[ConvAxisIndex].Status.ControllerReady := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#14);
    RCON1_IN[ConvAxisIndex].Status.EmergencyStop := TestABit(RCON1_RxWord[ConvBase + INT#7], USINT#15);

    // DataValidは直接受信bitではなく、今回の内部設計で決めた内部判定です。
    // CommOKはCPUの実通信状態から別途作成。単にTRUE固定にしないでください。
    // DataValidは運転許可や安全保証ではありません。各異常・原点等は別途確認。
    RCON1_IN[ConvAxisIndex].DataValid := RCON1_CommOK AND RCON1_LayoutConfirmed
        AND RCON1_ByteOrderConfirmed AND ConvUnitOK AND RCON1_GwRun
        AND RCON1_AxisLinked[ConvAxisIndex] AND NOT RCON1_GwAxisCommError;
END_FOR;
