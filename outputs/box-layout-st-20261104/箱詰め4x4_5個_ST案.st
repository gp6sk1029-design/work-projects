(*
箱詰め：4列×4行、1か所に5個積み、合計80個

前提：1回に5個積みを置く。
      位置を選ぶ前に、別ラダーでBox_Total_CTへ5を加算する。
      初回は5、最後の16か所目は80。

Box_Total_CT          : INT  箱へ入れる製品総数（5、10、…80）
Box_PackPos_Calc      : BOOL 箱内の目標位置を設定する時だけON
Box_PackCount_Valid   : BOOL カウント範囲と5個単位の確認結果

既存配列の空き要素を、次の設定用途へ割り当てる案。
HMI_RCON2_2_OUT_TargetPos[3] : 箱内X開始位置 [mm]
HMI_RCON2_2_OUT_TargetPos[4] : 箱内Xピッチ   [mm]
HMI_RCON2_3_OUT_TargetPos[3] : 箱内Y開始位置 [mm]
HMI_RCON2_3_OUT_TargetPos[4] : 箱内Yピッチ   [mm]

位置設定[1][2]は現行のストックフォルダ取出し位置なので維持する。
ピッチは符号付き。正なら位置数値が増え、負なら減る。
このSTでは移動開始指令、Z軸、カウンター加算・リセットは行わない。
*)

// カウントは5～80、かつ5の倍数だけを有効にする。
Box_PackCount_Valid :=
    (Box_Total_CT >= INT#5) AND
    (Box_Total_CT <= INT#80) AND
    ((Box_Total_CT MOD INT#5) = INT#0);

// 箱内位置を設定する時だけ、実際のX・Y目標値へ転送する。
// 取出し動作中はBox_PackPos_CalcをOFFにする。
IF Box_PackPos_Calc AND Box_PackCount_Valid THEN

    // X方向：各行で1列目→2列目→3列目→4列目の順に配置。
    // 1列目：総数が5、25、45、65の時。
    IF (Box_Total_CT = INT#5) OR
       (Box_Total_CT = INT#25) OR
       (Box_Total_CT = INT#45) OR
       (Box_Total_CT = INT#65) THEN

        RCON2_2_OUT_TargetPos_mm := HMI_RCON2_2_OUT_TargetPos[3];

    // 2列目：開始位置＋1ピッチ。
    ELSIF (Box_Total_CT = INT#10) OR
          (Box_Total_CT = INT#30) OR
          (Box_Total_CT = INT#50) OR
          (Box_Total_CT = INT#70) THEN

        RCON2_2_OUT_TargetPos_mm :=
            HMI_RCON2_2_OUT_TargetPos[3] +
            HMI_RCON2_2_OUT_TargetPos[4];

    // 3列目：開始位置＋2ピッチ。
    ELSIF (Box_Total_CT = INT#15) OR
          (Box_Total_CT = INT#35) OR
          (Box_Total_CT = INT#55) OR
          (Box_Total_CT = INT#75) THEN

        RCON2_2_OUT_TargetPos_mm :=
            HMI_RCON2_2_OUT_TargetPos[3] +
            HMI_RCON2_2_OUT_TargetPos[4] * LREAL#2.0;

    // 4列目：開始位置＋3ピッチ。
    ELSIF (Box_Total_CT = INT#20) OR
          (Box_Total_CT = INT#40) OR
          (Box_Total_CT = INT#60) OR
          (Box_Total_CT = INT#80) THEN

        RCON2_2_OUT_TargetPos_mm :=
            HMI_RCON2_2_OUT_TargetPos[3] +
            HMI_RCON2_2_OUT_TargetPos[4] * LREAL#3.0;
    END_IF;

    // Y方向：4か所（20個）ごとに次の行へ進む。
    // 1行目：5、10、15、20。
    IF Box_Total_CT <= INT#20 THEN

        RCON2_3_OUT_TargetPos_mm := HMI_RCON2_3_OUT_TargetPos[3];

    // 2行目：25、30、35、40。
    ELSIF Box_Total_CT <= INT#40 THEN

        RCON2_3_OUT_TargetPos_mm :=
            HMI_RCON2_3_OUT_TargetPos[3] +
            HMI_RCON2_3_OUT_TargetPos[4];

    // 3行目：45、50、55、60。
    ELSIF Box_Total_CT <= INT#60 THEN

        RCON2_3_OUT_TargetPos_mm :=
            HMI_RCON2_3_OUT_TargetPos[3] +
            HMI_RCON2_3_OUT_TargetPos[4] * LREAL#2.0;

    // 4行目：65、70、75、80。
    ELSE

        RCON2_3_OUT_TargetPos_mm :=
            HMI_RCON2_3_OUT_TargetPos[3] +
            HMI_RCON2_3_OUT_TargetPos[4] * LREAL#3.0;
    END_IF;

END_IF;
