"""ST7の保持回路を、正確な接続を保った新規説明画像として描く。"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parents[2] / 'outputs' / 'box-cycle-review-20261105'
OUT.mkdir(parents=True, exist_ok=True)
im = Image.new('RGB', (1600, 1800), '#f3f5f8')
d = ImageDraw.Draw(im)
INK, BLUE, GREEN, RED = '#202b3b', '#195cb0', '#227154', '#c43c27'

def font(n=27, bold=False):
    return ImageFont.truetype('C:/Windows/Fonts/meiryob.ttc' if bold else 'C:/Windows/Fonts/meiryo.ttc', n)

def txt(x,y,s,n=27,color=INK,bold=False,anchor='la'):
    d.text((x,y), s, font=font(n,bold), fill=color, anchor=anchor)

def line(points, color=INK, width=4):
    d.line(points, fill=color, width=width)

def panel(y,h,title,sub,color=BLUE):
    d.rounded_rectangle((35,y,1565,y+h),radius=18,fill='white',outline='#d7dfe9',width=2)
    d.rounded_rectangle((35,y,1565,y+67),radius=18,fill=color)
    d.rectangle((35,y+35,1565,y+67),fill=color)
    txt(62,y+14,title,31,'white',True)
    txt(65,y+79,sub,24)

def contact(x,y,tag,desc='',nc=False,color=INK,n=25):
    d.rectangle((x-24,y-24,x+24,y+24),fill='white')
    line([(x-19,y-22),(x-19,y+22)],color)
    line([(x+19,y-22),(x+19,y+22)],color)
    if nc:
        line([(x-31,y+30),(x+31,y-30)],color)
    txt(x,y-56,tag,n,BLUE if color==INK else color,anchor='ma')
    if desc: txt(x,y+30,desc,22,GREEN,anchor='ma')

def coil(x,y,tag,desc=''):
    d.ellipse((x-25,y-25,x+25,y+25),fill='white',outline=INK,width=4)
    txt(x,y-69,tag,24,BLUE,anchor='ma')
    if desc: txt(x,y+32,desc,25,GREEN,anchor='ma')

def waiting(y,modified=False):
    ys=[y,y+120,y+240]
    line([(100,y-15),(100,ys[-1]+30)],width=6)
    line([(1510,y-15),(1510,y+30)],width=6)
    for yy in ys: line([(100,yy),(850,yy)])
    line([(850,y),(850,ys[-1])])
    line([(850,y),(1510,y)])
    for yy in ys:
        d.ellipse((844,yy-6,856,yy+6),fill=INK)
    contact(300,y,'ST7_A_SF_M[3]','ターン戻側の工程')
    contact(650,y,'Out_CYw_SH_A_Turn_H_Done','ターン戻 動作完了',n=23)
    contact(300,ys[1],'ST7_A_SF_M[4]','ターン行側の工程')
    contact(650,ys[1],'Out_CYw_SH_A_Turn_F_Done','ターン行 動作完了',n=23)
    contact(300,ys[2],'ST7_A_SF_Wait_Pickup','自己保持',n=24)
    coil(1310,y,'ST7_A_SF_Wait_Pickup','A側 取出し待ち')
    if modified:
        d.rounded_rectangle((875,y-94,1170,y+82),radius=12,outline=RED,width=4)
        contact(1020,y,'A取出し・退避完了','仮称／b接点を追加',nc=True,color=RED,n=24)
        txt(930,y+145,'3本の枝の合流後に追加',28,RED,True)
        txt(930,y+193,'取出し・退避できるまで保持',26)
        txt(930,y+235,'完了したら、待ちをOFF',26)
    else:
        d.rounded_rectangle((915,y+104,1490,y+248),radius=12,fill='#fff1ec')
        txt(943,y+125,'解除条件がない',32,RED,True)
        txt(943,y+180,'一度ONすると保持し続ける',26)

txt(50,18,'ST7 A側｜取出し待ちの保持と解除',43,INK,True)
txt(52,82,'B側は対象外　／　プログラム変更前の検討図',26)
panel(135,505,'① 現在の31行目','回転完了、または自己保持で「取出し待ち」をON')
waiting(337)
panel(663,505,'② 解除条件を追加する案','追加するのは、自己保持を含む全3枝に共通のb接点',color='#315b81')
waiting(865,True)

panel(1191,393,'③「A取出し・退避完了」の条件候補','3条件がすべてONのとき成立。仮称であり、既存タグではありません。',color='#6f5a42')
y=1394
line([(100,y-18),(100,y+26)],width=6)
line([(1510,y-18),(1510,y+26)],width=6)
line([(100,y),(1510,y)])
contact(275,y,'BoxPacking_A_Busy','A側 取出し中',n=25)
contact(650,y,'BoxPacking_M[33]','取出し後のZ軸上昇工程',n=25)
contact(1030,y,'RCON2_4_MoveDone','箱詰めZ軸 移動完了',n=25)
coil(1390,y,'A取出し・退避完了','仮称')
txt(70,1480,'※ 上記は現在のF版の番号。初回完了M[2]の改番後は、旧M[33]→M[34]。',24)
txt(70,1525,'※ 完了信号の保持時間・実行順を確認し、ST7が確実に読み取れるようにします。',24)

txt(55,1610,'解除のタイミング',29,INK,True)
txt(55,1660,'「A側BusyがON」だけでは、まだ取出し開始です。',28)
txt(55,1704,'Z上昇位置で回転と干渉しないことが前提。X/Y退避が必要なら、その完了まで待ちます。',25)
txt(55,1752,'a接点：通常の接点　　b接点：斜線付きの接点　　○：通常コイル　　実機確認前・未反映',23,'#566479')

dest=OUT/'ST7_A_取出し待ち_ラダー比較.png'
im.save(dest)
print(dest)
