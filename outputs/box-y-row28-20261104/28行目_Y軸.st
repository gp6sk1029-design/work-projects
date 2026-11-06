// 箱詰めY位置：X方向4か所（20個）ごとに次の行へ進む。
// Y開始位置：HMI_RCON2_3_OUT_TargetPos[3] [mm]
// Yピッチ　：HMI_Box_Y_Pitch_mm [mm]（符号付き）
// 位置選択前に既存ラダーで5個加算。無効カウントでは目標を更新しない。

// 1行目：開始位置
IF (Box_Total_CT = INT#5) OR
   (Box_Total_CT = INT#10) OR
   (Box_Total_CT = INT#15) OR
   (Box_Total_CT = INT#20) THEN

    RCON2_3_OUT_TargetPos_mm := HMI_RCON2_3_OUT_TargetPos[3];

// 2行目：開始位置＋1ピッチ
ELSIF (Box_Total_CT = INT#25) OR
      (Box_Total_CT = INT#30) OR
      (Box_Total_CT = INT#35) OR
      (Box_Total_CT = INT#40) THEN

    RCON2_3_OUT_TargetPos_mm :=
        HMI_RCON2_3_OUT_TargetPos[3] + HMI_Box_Y_Pitch_mm;

// 3行目：開始位置＋2ピッチ
ELSIF (Box_Total_CT = INT#45) OR
      (Box_Total_CT = INT#50) OR
      (Box_Total_CT = INT#55) OR
      (Box_Total_CT = INT#60) THEN

    RCON2_3_OUT_TargetPos_mm :=
        HMI_RCON2_3_OUT_TargetPos[3] + HMI_Box_Y_Pitch_mm * LREAL#2.0;

// 4行目：開始位置＋3ピッチ
ELSIF (Box_Total_CT = INT#65) OR
      (Box_Total_CT = INT#70) OR
      (Box_Total_CT = INT#75) OR
      (Box_Total_CT = INT#80) THEN

    RCON2_3_OUT_TargetPos_mm :=
        HMI_RCON2_3_OUT_TargetPos[3] + HMI_Box_Y_Pitch_mm * LREAL#3.0;
END_IF;
