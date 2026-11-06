"""保存候補の完了回路と補助記憶を、実際の新行番号で表示する。"""
from pathlib import Path
import sys,json
sys.path.insert(0,'C:/Users/SEIGI-N13/.codex/skills/sysmac-studio/scripts')
from render_ladder import render
import sysmac as sm
b=Path(__file__).parent;m=json.loads((b/'build.json').read_text(encoding='utf-8'));mp={int(k):v for k,v in m['old_to_new_rows'].items()};out=Path('C:/Users/SEIGI-N13/work-projects/outputs/st7-dis2-fix-20261106')
e=[]
def text(x,y,t,size=24,blue=False):e.append({'type':'text','x':x,'y':y,'text':t,'size':size,'color':'change' if blue else 'ink','width':1580})
def wire(*points):e.append({'type':'wire','points':points})
def ld(x,y,label,nc=False,blue=False,w=180):e.append({'type':'contact','x':x,'y':y,'width':w,'label':label,'nc':nc,'color':'change' if blue else 'ink'})
def coil(x,y,label):e.append({'type':'coil','x':x,'y':y,'width':130,'label':label})
text(60,30,'20261106A：ワークなしの完了と、次サイクルの解除',34)
text(60,94,f'ST7_A_Dis2_左SF排出／新{mp[26]}行｜黒：維持した回路　青：追加した条件・枝')
wire((60,175),(60,590));wire((1680,175),(1680,590))
wire((60,270),(100,270));ld(100,270,'M33');wire((280,270),(400,270));ld(400,270,'送り戻Done',w=230);wire((630,270),(900,270))
wire((60,385),(100,385));ld(100,385,'M8',blue=True);wire((280,385),(400,385));ld(400,385,'M10：なし',blue=True,w=230);wire((630,385),(900,385),(900,270))
wire((60,505),(100,505));ld(100,505,'End');wire((280,505),(900,505),(900,270))
wire((900,270),(970,270));ld(970,270,'Retry[12]',True);wire((1150,270),(1210,270));ld(1210,270,'Next',True,True);wire((1390,270),(1510,270));coil(1510,270,'End');wire((1640,270),(1680,270))
text(80,645,'M8＝ワーク有無判定中／M10＝実物もデータもなし／M33＝最後の送り戻工程')
text(80,700,'M＝ST7_A_Dis2_M／End＝ST7_A_Dis2_End／Next＝Ins_A_Next_Cycle')
text(80,755,'送り戻Done＝Out_CYw_Ejc_Hldr_Feed_A_H_Done')
text(80,820,'有無判定は今回の初期位置確認済みM46で許可。起動直後のRetry解除だけでは開始しない。',25,True)
text(80,880,'有無判定の保持もEndで解除。最後の送り戻要求は、受け接点のあるAuto[2]へ修正。',25,True)
text(80,970,'A版ファイルへ反映｜局所検算・仮想応答モデルで確認。登録Jは未変更、実機未確認。',22)
spec={'width':1740,'height':1030,'elements':e};(b/'result-ladder.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2),encoding='utf-8')
print(render(spec,out/'A版の完了・次サイクル回路.png'))
