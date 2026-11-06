// 箱詰めX位置：4列×4行、1か所5個積み、合計80個
// Box_Total_CTは既存ラダーで5個ずつ加算済みの値を使用する。
// X開始位置：HMI_RCON2_2_OUT_TargetPos[3] [mm]
// Xピッチ　：HMI_Box_X_Pitch_mm [mm]（符号付き）
// 無効カウントでは目標を更新しない。加算・リセット・移動開始は行わない。

// 1列目：開始位置
IF (Box_Total_CT = INT#5) OR
   (Box_Total_CT = INT#25) OR
   (Box_Total_CT = INT#45) OR
   (Box_Total_CT = INT#65) THEN

    RCON2_2_OUT_TargetPos_mm := HMI_RCON2_2_OUT_TargetPos[3];

// 2列目：開始位置＋1ピッチ
ELSIF (Box_Total_CT = INT#10) OR
      (Box_Total_CT = INT#30) OR
      (Box_Total_CT = INT#50) OR
      (Box_Total_CT = INT#70) THEN

    RCON2_2_OUT_TargetPos_mm :=
        HMI_RCON2_2_OUT_TargetPos[3] +
        HMI_Box_X_Pitch_mm;

// 3列目：開始位置＋2ピッチ
ELSIF (Box_Total_CT = INT#15) OR
      (Box_Total_CT = INT#35) OR
      (Box_Total_CT = INT#55) OR
      (Box_Total_CT = INT#75) THEN

    RCON2_2_OUT_TargetPos_mm :=
        HMI_RCON2_2_OUT_TargetPos[3] +
        HMI_Box_X_Pitch_mm * LREAL#2.0;

// 4列目：開始位置＋3ピッチ
ELSIF (Box_Total_CT = INT#20) OR
      (Box_Total_CT = INT#40) OR
      (Box_Total_CT = INT#60) OR
      (Box_Total_CT = INT#80) THEN

    RCON2_2_OUT_TargetPos_mm :=
        HMI_RCON2_2_OUT_TargetPos[3] +
        HMI_Box_X_Pitch_mm * LREAL#3.0;
END_IF;
