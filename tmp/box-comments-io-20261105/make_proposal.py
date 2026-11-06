from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
source=root/'outputs/box-comments-20261105/行間コメント詳細案.txt'
text=source.read_text(encoding='utf-8')
items={
0:'内部信号：Auto_Com_Start（自動開始）',
1:'入力：X1003 到着、X1010 空コンテナ送り戻／位置：RCON2_5 現在位置',
2:'出力：Y1204 排出戻／要求：Out_CYw_Ejc_Cont_H_Auto[1]',
3:'確認：X1016・X1018 戻完了／移動：RCON2_5_Auto[1]、位置設定[2]',
4:'確認：RCON2_5_MoveDone／入力：X1007 トレイ方向',
5:'移動：RCON2_5_Auto[2]、位置設定[3]（排出）',
6:'出力：Y1205 排出行／要求：Out_CYw_Ejc_Cont_F_Auto[1]',
7:'入力：X1005 コンテナ通過',
8:'入力：X1010 戻確認OFF／移動：RCON2_5_Auto[3]、位置設定[1]',
9:'確認：RCON2_5_MoveDone・現在位置[1]、X1003 到着／出力：Y1204、Auto[2]',
10:'確認：X1016・X1018 戻完了／出力：Y1206、Out_CYw_Box_Chuck_H_Auto[1]',
11:'確認：X1020 チャック戻完了／移動：RCON2_5_Auto[4]、位置設定[2]',
12:'確認：RCON2_5_MoveDone',
13:'内部信号：ST7_A_SF_Wait_Pickup／ST7_B_SF_Wait_Pickup（A・B取出し待ち）',
14:'内部信号：BoxPacking_A_Busy／個数：Box_Total_CTへ5加算',
15:'内部信号：BoxPacking_B_Busy／個数：Box_Total_CTへ5加算',
16:'移動：RCON2_4_Auto[1]（Z）、位置設定[1]（待機上昇）',
17:'確認：RCON2_4_MoveDone／移動：RCON2_2_Auto[1]（X）・RCON2_3_Auto[1]（Y）、両軸位置設定[1]',
18:'確認：RCON2_2_MoveDone（A側X）',
19:'確認：RCON2_3_MoveDone（A側Y）',
20:'内部信号：BoxPacking_M[24]・[25]（A側XY両方完了）',
21:'確認：RCON2_4_MoveDone／移動：RCON2_2_Auto[2]（X）・RCON2_3_Auto[2]（Y）、両軸位置設定[2]',
22:'確認：RCON2_2_MoveDone（B側X）',
23:'確認：RCON2_3_MoveDone（B側Y）',
24:'内部信号：BoxPacking_M[28]・[29]（B側XY両方完了）',
25:'移動：RCON2_4_Auto[2]（Z）、位置設定[2]（取出し下降）',
26:'確認：RCON2_4_MoveDone／出力：Y1207、Out_CYw_Box_Chuck_F_Auto[1]',
27:'確認：X1021 チャック行完了／移動：RCON2_4_Auto[3]（Z）、位置設定[1]',
28:'確認：RCON2_4_MoveDone／移動：RCON2_2_Auto[3]（X）／計算：[3]＋HMI_Box_X_Pitch_mm×列番号0～3',
29:'確認：RCON2_4_MoveDone／移動：RCON2_3_Auto[3]（Y）／計算：[3]＋HMI_Box_Y_Pitch_mm×行番号0～3',
30:'確認：RCON2_2_MoveDone（箱内X）',
31:'確認：RCON2_3_MoveDone（箱内Y）',
32:'内部信号：BoxPacking_M[36]・[37]（箱内XY両方完了）',
33:'移動：RCON2_4_Auto[4]（Z）、位置設定[3]（箱内配置下降）',
34:'確認：RCON2_4_MoveDone／出力：Y1206、Out_CYw_Box_Chuck_H_Auto[2]',
35:'確認：X1020 チャック戻完了／移動：RCON2_4_Auto[5]（Z）、位置設定[1]',
36:'確認：RCON2_4_MoveDoneのOFF／個数：Box_Total_CT < 80 または = 80',
37:'移動：RCON2_5_Auto[5]、位置設定[3]（排出）',
38:'確認：RCON2_5_MoveDone／出力：Y1205、Out_CYw_Ejc_Cont_F_Auto[2]',
39:'入力：X1005 通過／出力：Y1204、Out_CYw_Ejc_Cont_H_Auto[3]',
40:'確認：X1016・X1018 戻完了／移動：RCON2_5_Auto[6]、位置設定[1]',
41:'確認：RCON2_5_MoveDone／内部信号：BoxPacking_End',
}
def add(m):
 n=int(m[1]);return m[0]+'使用信号：'+items[n]+'\n'
text=re.sub(r'(?m)^(\d+)行：\n',add,text)
legend='''BoxPacking入出力・RCONを明示したコメント一覧案（提案のみ）
X/Y番号は変数コメントとAT割付から確認。BoxではTimerQ/Done経由で判定する箇所がある。
RCON2_2=X、RCON2_3=Y、RCON2_4=Z、RCON2_5=コンテナ軸。
位置設定[n]は該当軸のHMI_RCON2_軸番号_OUT_TargetPos[n]。
Auto[n]は移動要求番号で、位置設定[n]とは別。
RCONのMoveDoneは通信状態から作る内部信号で、物理X番号ではない。
Y1204=排出戻、完了はX1016/X1018の両方。
Y1205=排出行、行端はX1017/X1019。Boxの次工程ではX1005通過を確認する。
Y1206=チャック戻、完了はX1020。Y1207=チャック行、完了はX1021。
X1003=コンテナ到着、X1005=通過、X1007=トレイ方向、X1010=空コンテナ送り戻。
BoxはX1010を参照するが、Y1200空コンテナ送り戻の要求はこのセクションから発行していない。
入力のTimerQは該当Inputセクションで0.5秒のON確認を通る。
参考：HMI_RCON2_3_OUT_TargetPos[1]は元コメントがB側だが、17行のA側工程で使用するため、案ではA側位置として扱う。

'''
(root/'outputs/box-comments-20261105/入出力RCON付き行間コメント案.txt').write_text(legend+text,encoding='utf-8')
assert len(items)==42
print('42行の使用信号を追記。smc2未編集。')
