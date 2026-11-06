from pathlib import Path
import re
root=Path(__file__).resolve().parents[2]
p=root/'outputs/box-comments-20261105/入出力RCON付き行間コメント案.txt'
text=p.read_text(encoding='utf-8')
names={'X1003':'コンテナ到着','X1005':'コンテナ通過','X1007':'コンテナトレイ方向','X1010':'空コンテナ送り戻確認','X1016':'コンテナ排出1 戻確認','X1017':'コンテナ排出1 行確認','X1018':'コンテナ排出2 戻確認','X1019':'コンテナ排出2 行確認','X1020':'箱入れチャック戻確認','X1021':'箱入れチャック行確認','Y1204':'コンテナ排出戻','Y1205':'コンテナ排出行','Y1206':'箱入れチャック戻','Y1207':'箱入れチャック行'}
text=re.sub(r'\b[XY]\d{4}\b',lambda m:m[0]+'（'+names[m[0]]+'）' if m[0] in names else m[0],text)
axes={'2':'箱詰めX軸','3':'箱詰めY軸','4':'箱詰めZ軸','5':'コンテナ設置・排出軸'}
text=re.sub(r'(?<!\w)RCON2_([2345])(?:_Auto\[\d+\]|_MoveDone)?',lambda m:m[0]+'（'+axes[m[1]]+'）',text)
(root/'outputs/box-comments-20261105/番号名称・軸名を明記したコメント案.txt').write_text(text,encoding='utf-8')
print('コメント案のみ更新。smc2変更なし。')
