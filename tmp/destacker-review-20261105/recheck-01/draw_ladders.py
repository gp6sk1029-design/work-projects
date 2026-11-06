"""ラダー提案を配線図として描画する。元プロジェクトは変更しない。"""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
out=Path('C:/Users/SEIGI-N13/work-projects/outputs/destacker-recheck-20261105');out.mkdir(exist_ok=True)
font='C:/Windows/Fonts/meiryo.ttc'
ink='#17212b';blue='#0068a8';muted='#445565'
class Fig:
    def __init__(self,title,subtitle,h,w=1600):
        self.w=w;self.h=h;self.im=Image.new('RGB',(w,h),'white');self.d=ImageDraw.Draw(self.im)
        self.text(65,35,title,36);self.text(65,100,subtitle,23,muted)
    def text(self,x,y,t,size=24,color=ink,center=False):
        self.d.text((x,y),t,font=ImageFont.truetype(font,size),fill=color,anchor='mt' if center else 'lt')
    def line(self,x1,y1,x2,y2,color=ink):self.d.line((x1,y1,x2,y2),fill=color,width=3)
    def contact(self,x,y,t,nc=False,w=130,color=ink):
        a=x+w/2-13;b=x+w/2+13
        self.line(x,y,a,y);self.line(b,y,x+w,y)
        self.line(a,y-20,a,y+20,color);self.line(b,y-20,b,y+20,color)
        if nc:self.line(a-5,y+22,b+5,y-22,color)
        self.text(x+w/2,y-62,t,24,color,True)
        return x+w
    def coil(self,x,y,t,color=ink,w=100):
        self.line(x,y,x+20,y);self.line(x+w-20,y,x+w,y)
        self.d.arc((x+20,y-22,x+58,y+22),90,270,fill=color,width=3)
        self.d.arc((x+w-58,y-22,x+w-20,y+22),270,450,fill=color,width=3)
        self.text(x+w/2,y-64,t,24,color,True)
    def box(self,x,y,t,w=200,color=ink):
        self.d.rectangle((x,y-38,x+w,y+38),outline=color,width=3)
        lines=t.split('\n')
        for j,line in enumerate(lines):self.text(x+w/2,y-29+j*29,line,22,color,True)
    def rails(self,y1,y2):
        self.line(70,y1,70,y2);self.line(self.w-70,y1,self.w-70,y2)
    def end(self,x,y):self.line(x,y,self.w-70,y)
    def save(self,name):self.im.save(out/name)

f=Fig('① 確認OKを待って、1段目へ移動する','11～12行の一体対策案｜M[n]＝Destacker_M[n]｜青：変更・追加する条件',1450)
f.rails(165,1100)
f.contact(100,210,'M[13]');f.line(70,210,100,210);f.line(230,210,300,210)
f.contact(340,210,'送り戻り完了',color=blue);f.line(300,210,340,210);f.line(470,210,590,210)
f.line(300,210,300,310);f.line(300,310,340,310);f.box(340,310,'↑ Retry OFF',170);f.line(510,310,590,310)
f.line(70,420,100,420);f.contact(100,420,'M[14]');f.line(230,420,590,420);f.line(590,210,590,420)
for x,t,nc,col in [(620,'Retry[13]',True,ink),(820,'M[16]',True,ink),(1030,'X1010',False,blue)]:
    f.contact(x,210,t,nc,color=col)
f.line(590,210,620,210);f.line(750,210,820,210);f.line(950,210,1030,210);f.line(1160,210,1320,210)
f.coil(1320,210,'M[14]');f.end(1420,210)
f.text(85,475,'Retryの迂回枝にも、共通のX1010「送り戻り端」を必要にする。',24,blue)
xs=[100,335,570,805,1040];labels=['M[14]','X1000','X1010','X1004','X1001']
f.line(70,625,100,625)
for j,(x,t) in enumerate(zip(xs,labels)):
    f.contact(x,625,t,nc=j==1,color=blue if t=='X1010' else ink)
    f.line(x+130,625,xs[j+1] if j<4 else 1320,625)
f.coil(1320,625,'M[15] 確認OK',blue);f.end(1420,625)
f.text(85,690,'X1000：供給部コンテナ有／X1010：空コンテナ送り戻',23,muted)
f.text(85,735,'X1004：コンテナ方向確認／X1001：段バラシ1段目有',23,muted)
f.line(70,875,100,875);f.contact(100,875,'M[15]',color=blue);f.line(230,875,350,875)
f.line(70,985,100,985);f.contact(100,985,'M[16]');f.line(230,985,350,985);f.line(350,875,350,985)
f.line(350,875,410,875);f.contact(410,875,'M[17]',True);f.line(540,875,640,875)
f.box(640,875,'MOVE 設定[2]\n→ 軸目標位置',310);f.line(950,875,1320,875)
f.coil(1320,875,'M[16]');f.end(1420,875)
f.line(1200,875,1200,1045);f.line(1200,1045,1320,1045);f.coil(1320,1045,'軸要求[5]');f.end(1420,1045)
f.text(85,1140,'送り戻り完了＝Out_CYw_Empty_Container_CY_H_Done',23)
f.text(85,1190,'軸要求[5]＝RCON2_1_Auto[5]（段バラシ軸）',23)
f.text(85,1240,'11行の誤った爪戻りDoneを、送り戻りDoneへ置換する。',23)
f.text(85,1290,'異常監視側のX1010もON条件へ整合。既存の5秒TONは維持する。',23)
f.text(85,1360,'提案・未反映｜10行の送り戻り完了後に確認する前提。実機未検証。',22,muted)
f.save('01-confirmation.png')

f=Fig('② 初回処理中と、初回完了を分ける','0～2行の開始制限＋補助回路案｜M[n]＝Destacker_M[n]',1260)
f.rails(160,1000)
f.line(70,220,100,220);f.contact(100,220,'自動開始');f.line(230,220,350,220);f.contact(350,220,'Init_Busy',True,color=blue);f.line(480,220,610,220)
f.line(70,330,100,330);f.contact(100,330,'M[1]');f.line(230,330,610,330);f.line(610,220,610,330)
f.line(610,220,680,220);f.contact(680,220,'M[2]',True);f.line(810,220,940,220);f.contact(940,220,'M[26]',True,color=blue);f.line(1070,220,1320,220);f.coil(1320,220,'M[1]');f.end(1420,220)
f.text(85,385,'Busyは自動開始の枝だけに置き、M[1]の自己保持は迂回させる。',24,blue)
for y,t in [(520,'M[1]'),(630,'Init_Busy')]:
    f.line(70,y,100,y);f.contact(100,y,t,color=blue if y==630 else ink);f.line(230,y,610,y)
f.line(610,520,610,630);f.line(610,520,780,520);f.contact(780,520,'M[26]',True,color=blue);f.line(910,520,1320,520);f.coil(1320,520,'Init_Busy',blue);f.end(1420,520)
f.line(70,820,100,820)
for x,t,nxt in [(100,'M[11]',350),(350,'M[12]',600),(600,'送り戻り完了',1050)]:
    f.contact(x,820,t);f.line(x+130,820,nxt,820)
f.line(70,930,100,930);f.contact(100,930,'M[26]',color=blue);f.line(230,930,1050,930);f.line(1050,820,1050,930);f.line(1050,820,1320,820);f.coil(1320,820,'M[26] 初回済',blue);f.end(1420,820)
f.text(85,1030,'Init_Busy＝新規BOOL Destacker_Init_Busy（初回処理中）',23)
f.text(85,1080,'M[26]＝未使用番の活用案。通常の完了や次サイクルでは解除しない。',23)
f.text(85,1130,'1・2行の初回回路にも、共通のNC M[26]を追加する。',23)
f.text(85,1190,'提案・未反映｜非保持設定を確認し、電源再投入時には初回処理へ戻す。',22,muted)
f.save('02-initial-cycle.png')

f=Fig('③ 前の完了を捨てて、今回の完了を待つ','例：5→6行の1段目移動｜Done＝RCON2_1_MoveDone',1490)
f.rails(160,1180)
f.line(70,220,100,220);f.contact(100,220,'M[8]');f.line(230,220,350,220)
for y,t,nc in [(220,'Done',True),(330,'M[28]',False)]:
    f.line(350,y,440,y);f.contact(440,y,t,nc,color=blue);f.line(570,y,790,y)
f.line(350,220,350,330);f.line(790,220,790,330);f.line(790,220,1320,220);f.coil(1320,220,'M[28]',blue);f.end(1420,220)
f.text(85,390,'M[28]：M[8]が有効な間に、DoneのOFFを一度確認した記憶。',24,blue)
f.line(70,520,100,520)
for x,t,nxt in [(100,'M[8]',340),(340,'M[28]',580),(580,'Done',850)]:
    f.contact(x,520,t,color=blue if t=='M[28]' else ink);f.line(x+130,520,nxt,520)
f.line(70,630,100,630);f.contact(100,630,'M[9]');f.line(230,630,850,630);f.line(850,520,850,630)
f.line(850,520,950,520);f.contact(950,520,'M[10]',True);f.line(1080,520,1320,520);f.coil(1320,520,'M[9]');f.end(1420,520)
f.text(85,700,'既存の爪行要求 Out_CYw_Sep_Claw_F_Auto[2] も同じ条件で出す。',23)
f.text(85,780,'8行も同様：安全位置移動の完了を、M[10]の枝で待つ。',25,blue)
f.line(70,900,100,900)
for x,t,nxt in [(100,'M[10]',350),(350,'M[29]',600),(600,'Done',880)]:
    f.contact(x,900,t,color=blue if t!='M[10]' else ink);f.line(x+130,900,nxt,900)
f.line(70,1010,100,1010);f.contact(100,1010,'M[3]');f.line(230,1010,350,1010);f.contact(350,1010,'M[4]');f.line(480,1010,880,1010)
f.line(70,1120,100,1120);f.contact(100,1120,'M[11]');f.line(230,1120,880,1120);f.line(880,900,880,1120)
f.line(880,900,1000,900);f.contact(1000,900,'M[12]',True);f.line(1130,900,1320,900);f.coil(1320,900,'M[11]');f.end(1420,900)
f.text(85,1225,'M[29]はM[10]用のDone OFF記憶（上段M[28]と同じ回路）。',23)
f.text(85,1275,'M[3]＋M[4]：すでに安全位置なら、既存の合流枝を維持する。',23)
f.text(85,1325,'RCON受け側の「今回のPEND OFF→ON」対策とセットで使用する。',23)
f.text(85,1400,'提案・未反映｜単にDone接点を1個足すだけでは、旧Doneの流用が残る。',22,muted)
f.save('03-fresh-completion.png')

f=Fig('④ RCON2_1：次の要求を受付し、今回の完了を作る','既存RCON2_2の受付・完了回路を参考にする案｜M1/M2＝RCON2_1_M[1]/[2]',1520,w=1700)
f.rails(160,1110)
f.line(70,220,100,220);f.box(100,220,'要求[1]～[6] OR\nAND Ready AND 許可',330);f.line(430,220,490,220)
f.contact(490,220,'Done',True,color=blue,w=100);f.line(590,220,650,220);f.box(650,220,'TON[1]\n100ms',180);f.line(830,220,890,220);f.box(890,220,'Up',100);f.line(990,220,1050,220)
f.line(70,340,100,340);f.contact(100,340,'M1');f.line(230,340,1050,340);f.line(1050,220,1050,340)
f.line(1050,220,1090,220);f.contact(1090,220,'許可',w=100);f.line(1190,220,1230,220);f.contact(1230,220,'Done',True,w=100);f.line(1330,220,1460,220);f.coil(1460,220,'M1');f.end(1560,220)
f.text(85,405,'前回DoneがONの間はTONをリセット。要求ORが切れなくても次を受付できる。',24,blue)
f.line(70,550,100,550);f.contact(100,550,'M1');f.line(230,550,350,550)
for y,t,nc in [(550,'PEND',True),(660,'M2',False)]:
    f.line(350,y,450,y);f.contact(450,y,t,nc,color=blue);f.line(580,y,820,y)
f.line(350,550,350,660);f.line(820,550,820,660);f.line(820,550,1460,550);f.coil(1460,550,'M2',blue);f.end(1560,550)
f.text(85,720,'M2：開始保持中にPEND OFFを見た記憶。M1がOFFで解除する。',24,blue)
f.line(70,865,100,865)
for x,t,nxt in [(100,'M1',330),(330,'M2',560),(560,'PEND',800)]:
    f.contact(x,865,t,color=blue if t=='M2' else ink);f.line(x+130,865,nxt,865)
f.box(800,865,'Up',100);f.line(900,865,1060,865)
f.line(70,975,100,975);f.contact(100,975,'Done');f.line(230,975,1060,975);f.line(1060,865,1060,975)
f.line(1060,865,1150,865);f.contact(1150,865,'TON[2].Q',True,w=150);f.line(1300,865,1460,865);f.coil(1460,865,'Done');f.end(1560,865)
f.line(1380,865,1380,1080);f.line(1380,1080,1430,1080);f.box(1430,1080,'TON[2]\n100ms',170)
f.text(85,1190,'PEND＝RCON2_1_IN_PositionDone／Done＝RCON2_1_MoveDone',24)
f.text(85,1240,'許可の生成と通信・I/O配置は未確認。許可をTRUE固定して使わない。',24)
f.text(85,1290,'P_Offの転送・Start経路は、通信・配置・軸許可の確認後に別途接続する。',24)
f.text(85,1340,'同じ位置への指令などでPENDがOFFにならない場合は、実機仕様の確認が必要。',24)
f.text(85,1430,'提案・未反映｜通信・実機・安全回路の完成図ではなく、受付と完了の論理案。',22,muted)
f.save('04-rcon-receiver.png')
print(out)
