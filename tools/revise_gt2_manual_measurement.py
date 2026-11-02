"""既存のGT2対応表を保持し、測定値変換の解説4ページを追加する。"""
import argparse
import hashlib
import io
import json
import shutil
import sys
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader

sys.stdout.reconfigure(encoding='utf-8')
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('source',type=Path)
p.add_argument('destination',type=Path)
p.add_argument('image',type=Path)
p.add_argument('--replace-own-sha256',default=None)
a=p.parse_args()
assert a.source.resolve()!=a.destination.resolve()
if a.destination.exists():
    assert a.replace_own_sha256 and hashlib.sha256(a.destination.read_bytes()).hexdigest()==a.replace_own_sha256, '既存の資料は上書きしない'
original=a.source.read_bytes()
src=PdfReader(io.BytesIO(original))
assert len(src.pages)==6
pdfmetrics.registerFont(TTFont('JP','C:/Windows/Fonts/msgothic.ttc',subfontIndex=0))
W,H=landscape(A4); M=36; WIDTH=W-2*M
NAVY=colors.HexColor('#183B56'); BLUE=colors.HexColor('#136F87')
INK=colors.HexColor('#20313C'); GRAY=colors.HexColor('#536775')
LINE=colors.HexColor('#D6E1E7'); LIGHT=colors.HexColor('#EFF6F8'); WARN=colors.HexColor('#FFF3DC')
BODY=ParagraphStyle('body',fontName='JP',fontSize=10,leading=15,textColor=INK)
SMALL=ParagraphStyle('small',parent=BODY,fontSize=8.5,leading=12)
HEAD=ParagraphStyle('header',parent=BODY,fontSize=9,leading=12,textColor=colors.white,alignment=1)
CELL=ParagraphStyle('cell',parent=BODY,fontSize=10,leading=13,alignment=1)
buffer=io.BytesIO(); c=canvas.Canvas(buffer,pagesize=(W,H))

def para(text,top,x=M,width=WIDTH,style=BODY):
    obj=Paragraph(text,style); _,height=obj.wrap(width,H)
    assert top-height>33, '本文の見切れ'
    obj.drawOn(c,x,top-height)
    return top-height

def title(page,text,sub):
    c.setFillColor(NAVY); c.rect(0,H-12,W,12,fill=1,stroke=0)
    c.setFillColor(BLUE); c.setFont('JP',9)
    c.drawString(M,H-32,'GT2 / DL-EP1  |  SYSMAC STUDIO  |  MEASUREMENT GUIDE - REV.2')
    c.setFillColor(INK); c.setFont('JP',20); c.drawString(M,H-62,f'{page:02d}  {text}')
    para(sub,H-77,style=SMALL)
    c.setStrokeColor(LINE); c.line(M,30,W-M,30)
    c.setFillColor(GRAY); c.setFont('JP',8)
    c.drawString(M,18,'2026/10/15 改訂  |  この章の受信配列はBYTE / 標準割付・0始まりが前提')
    c.drawRightString(W-M,18,f'{page} / 10')
    return H-110

def table(headers,rows,top,widths=None,rowheight=25,fontsize=10):
    widths=widths or [WIDTH/len(headers)]*len(headers)
    assert abs(sum(widths)-WIDTH)<0.01
    style=ParagraphStyle('local-cell',parent=CELL,fontSize=fontsize,leading=fontsize+3)
    data=[[Paragraph(str(x),HEAD) for x in headers]]+[[Paragraph(str(x),style) for x in row] for row in rows]
    t=Table(data,colWidths=widths,rowHeights=[32]+[rowheight]*len(rows))
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),
        ('LINEBELOW',(0,0),(-1,-1),0.3,LINE),
        ('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
    ]))
    _,height=t.wrap(WIDTH,H); assert top-height>=40, '表の見切れ'
    t.drawOn(c,M,top-height); return top-height-12

def note(text,top,warning=False):
    obj=Paragraph(text,SMALL); _,height=obj.wrap(WIDTH-20,H)
    assert top-height-14>33
    c.setFillColor(WARN if warning else LIGHT); c.rect(M,top-height-14,WIDTH,height+14,fill=1,stroke=0)
    obj.drawOn(c,M+10,top-height-7); return top-height-24

def heading(text,top):
    c.setFillColor(BLUE); c.setFont('JP',12); c.drawString(M,top-12,text); return top-25

# 7: 原画像と実際の指定位置を対にする。
y=title(7,'ラダー画像で見る「測定値の復元」','AryByteToは、通信で受信済みの4個のBYTEを組み立てて、1個の数値へ戻す命令です。')
img=ImageReader(str(a.image)); iw,ih=img.getSize(); dw=400; dh=dw*ih/iw
c.drawImage(img,M,y-dh,width=dw,height=dh,preserveAspectRatio=True,mask='auto')
right=M+422; rw=WIDTH-422
top=y
top=para('画像はユーザー提供の実回路です。',top,x=right,width=rw,style=SMALL)-16
top=para('<b>上段：右側</b><br/>DLEP1_IN[52]を先頭として、[52]・[53]・[54]・[55]の4個を読み、<br/>GT2_R_CurrentValへ格納します。',top,x=right,width=rw)-16
top=para('<b>下段：左側</b><br/>DLEP1_IN[48]を先頭として、[48]・[49]・[50]・[51]の4個を読み、<br/>GT2_L_CurrentValへ格納します。',top,x=right,width=rw)-16
top=para('0始まりの標準割付なら、画像の左側はID01、右側はID02です。右・左はコメントではなく、読取位置と実IDの対応で決まります。',top,x=right,width=rw,style=SMALL)
y=min(y-dh,top)-16
y=table(['画像の回路','入力の読取範囲（BYTE）','標準ID','復元した数値の保存先'],[
    ['右側 / 上段','DLEP1_IN[52]-[55]','ID02','GT2_R_CurrentVal'],
    ['左側 / 下段','DLEP1_IN[48]-[51]','ID01','GT2_L_CurrentVal'],
],y,[125,250,95,WIDTH-470],rowheight=25,fontsize=10)
y=note('重要：AryByteToのInはBYTE配列です。この画像の[48]は「48バイト目」であり、BOOL表の「48ビット目」ではありません。先ほどの1-6ページはBOOL換算の参考表で、画像の配列型とは区別して参照してください。',y,True)
c.showPage()

# 8: パラメータと数値の復元例。
y=title(8,'AryByteToの設定と、4バイトの意味','4個の箱に分かれた数値を、通信と同じ順序で1つへ戻します。4台分を読む意味ではありません。')
y=table(['項目','画像の指定','分かりやすい意味'],[
    ['In','DLEP1_IN[52] または [48]','ここを先頭として連続したデータを読む'],
    ['Size','4','4個のBYTE = 32 bit = 1個の測定値'],
    ['Order','_eBYTE_ORDER#_LOW_HIGH','先頭BYTEを下位側として組み立てる（下位 → 上位）'],
    ['OutVal','GT2_R_CurrentVal / GT2_L_CurrentVal','組み立てた結果を入れる変数。左下と右下は同じ入出力変数'],
    ['EN','画像では手前に条件接点なし','このプログラムが実行される周期ごとに変換する'],
],y,[90,280,WIDTH-370],rowheight=34,fontsize=9.5)
y=heading('例：ID01から数値1000が届いた場合（受信データを16進数で表示）',y)
y=table(['BYTE配列の位置','[48]','[49]','[50]','[51]'],[
    ['入っているデータ','E8','03','00','00'],
    ['数値内の位置','下位8 bit','次の8 bit','次の8 bit','上位8 bit'],
],y,[190]+[(WIDTH-190)/4]*4,rowheight=24,fontsize=10)
y=para('E8は十進数で232、03は3です。復元の計算は 232 + 3 × 256 = 1000 です。<br/>4BYTEを、保存先のデータ型に対応するビット表現として組み立てます。',y)-12
y=note('この1000は説明用の例です。1000が何mmかはアンプの換算条件次第で、AryByteTo自体はmm換算を行いません。GT2の現在値0は符号付き32 bitなので、通常は保存先をDINTにします。画像では保存先の型は未確認です。',y,True)
c.showPage()

# 9: 既存BOOL資料と実回路BYTEの橋渡しを全15台で示す。
y=title(9,'最大15台：BYTEとBOOLの測定値対応','通信データは同じです。BYTEは8 bitずつ、BOOLは1 bitずつ数えるため、添字の数字が違います。')
rows=[]
for ident in range(1,16):
    b=48+4*(ident-1); bit=b*8
    rows.append([f'ID{ident:02d}',f'[{b}]-[{b+3}]',f'DLEP1_IN[{b}]','4',f'[{bit}]-[{bit+31}]'])
y=table(['センサID','4BYTEの格納範囲','BYTE配列でAryByteToへ渡す先頭','Size','BOOL換算の32bit範囲'],rows,y,[90,155,275,65,WIDTH-585],rowheight=20,fontsize=10)
y=note('BYTE[48]-[51]とBOOL[384]-[415]は、同じ32ビットを別の単位で表したものです。どちらも0始まり・先頭オフセット0の別表現を比較しています。1つの変数を同時にBYTE型とBOOL型へ変更する指示ではありません。',y,True)
y=para('現在のDLEP1_INがBYTE配列なら、測定値は上表のBYTE位置で復元し、判定などのBOOL信号は該当BYTEのbitを参照します。入力をBYTE配列、出力をBOOL配列とする設計も可能ですが、各タグのサイズと並びをそれぞれ確認してください。',y,style=SMALL)
c.showPage()

# 10: 読取・測定開始・有効性・換算を混同しない。
y=title(10,'測定値を安全に使うための確認','数値が表示されていることと、新しく正常に測定できたことは同じではありません。')
y=table(['処理の役割','この回路で行うこと','別途必要なこと'],[
    ['受信','受信配列にあるデータを利用する','EtherNet/IP接続と通信正常の確認'],
    ['数値の復元','4BYTEを1つの数値に組み立てる','OutValのDINT定義と読取範囲の確認'],
    ['測定開始・採用タイミング','この回路だけでは指令・完了を判断しない','アンプの測定モード・指令・応答と採用条件の設計'],
    ['mm換算・合否判定','この命令自体では行わない','小数桁・倍率・しきい値と実機表示の照合'],
],y,[130,270,WIDTH-400],rowheight=30,fontsize=9)
y=note('GT2は現在値0が範囲外・無効になった場合、前の値を保持することがあります。AryByteToが毎周期動いていても、保持された古い値を読み直す可能性があります。通信異常時の受信値の扱いも設定に依存するため、数値だけで正常・最新と判定しないでください。',y,True)
y=heading('画像の左右に対応する現在値0の状態（BYTE配列の場合）',y)
y=table(['対象','上限オーバー','下限オーバー','無効'],[
    ['左側 / ID01','DLEP1_IN[6] のbit0','DLEP1_IN[8] のbit0','DLEP1_IN[10] のbit0'],
    ['右側 / ID02','DLEP1_IN[6] のbit1','DLEP1_IN[8] のbit1','DLEP1_IN[10] のbit1'],
],y,[145]+[(WIDTH-145)/3]*3,rowheight=26,fontsize=9)
y=para('適用前の確認：受信配列型・添字起点・通信サイズ、左右とIDの実対応、OutVal型、GT2表示と復元値の倍率を確認します。状態フラグと通信が正常なときだけ、設備の採用タイミングに応じて測定値を利用します。',y,style=SMALL)-12
y=para('出典：<link href="https://files.omron.eu/downloads/latest/manual/en/w502_nj_nx-series_instructions_reference_manual_en.pdf?v=3" color="#136F87">オムロン NJ/NX命令リファレンス W502 / AryByteTo</link><br/><link href="https://manualmachine.com/keyence/dlep1/1579627-user-manual/" color="#136F87">KEYENCE DL-EP1 User\'s Manual (GT2) 公開コピー / 3-8-3-12、3-19</link><br/>画像：ユーザー提供のラダー画面。本章の左右とIDは画像の指定位置から読み取った標準割付上の対応であり、実配線確認済みではありません。',y,style=SMALL)
c.showPage(); c.save()
added=PdfReader(io.BytesIO(buffer.getvalue()))
assert len(added.pages)==4
writer=PdfWriter()
# 元の1-6ページは内容をそのまま残し、ページ総数だけ更新する。
for num,pg in enumerate(src.pages,1):
    overlay_buffer=io.BytesIO(); ov=canvas.Canvas(overlay_buffer,pagesize=(W,H))
    ov.setFillColor(colors.white); ov.rect(W-100,11,70,16,fill=1,stroke=0)
    ov.setFont('JP',8); ov.setFillColor(GRAY); ov.drawRightString(W-M,18,f'{num} / 10')
    ov.save(); overlay=PdfReader(io.BytesIO(overlay_buffer.getvalue()))
    pg.merge_page(overlay.pages[0]); writer.add_page(pg)
for pg in added.pages: writer.add_page(pg)
writer.add_metadata({'/Title':'GT2 / DL-EP1 BOOL対応表 + 測定値読取解説 改訂版','/Author':'生産技術資料 / Codex','/Subject':'最大15台の入出力表・AryByteTo・BYTEとBOOLの換算'})
for ix,label in [(0,'使い方と前提'),(1,'出力指令'),(2,'入力判定'),(3,'入力応答'),(4,'測定値BOOL'),(5,'共通領域と注意'),(6,'ラダー画像の解説'),(7,'AryByteTo設定と例'),(8,'15台のBYTE/BOOL対応'),(9,'測定値の有効性')]: writer.add_outline_item(label,ix)
with a.destination.open('wb' if a.replace_own_sha256 else 'xb') as f: writer.write(f)
checked=PdfReader(a.destination)
assert len(checked.pages)==10
for i in range(6):
    before=PdfReader(io.BytesIO(original)).pages[i].extract_text()
    after=checked.pages[i].extract_text()
    assert before in after, f'元ページ{i+1}の本文変更'
all_added='\n'.join(p.extract_text() for p in checked.pages[6:])
for required in ['GT2_R_CurrentVal','GT2_L_CurrentVal','ID15','[104]-[107]','[832]-[863]','1000','DINT','前の値を保持']:
    assert required in all_added, required
assert len(checked.pages[6].images)>=1, 'ラダー画像の埋込を確認できない'
assert a.source.read_bytes()==original, '原本が変更された'
copy_path=Path('C:/Users/SEIGI-N13/work-projects/output/pdf')/a.destination.name
if copy_path.exists():
    assert a.replace_own_sha256 and hashlib.sha256(copy_path.read_bytes()).hexdigest()==a.replace_own_sha256
shutil.copy2(a.destination,copy_path)
assert copy_path.read_bytes()==a.destination.read_bytes()
verification={'ページ数':10,'既存本文保持':6,'追加ページ':4,'15台BYTE_BOOL換算':15,'原本不変':True,'元PDF_SHA256':hashlib.sha256(original).hexdigest(),'新PDF_SHA256':hashlib.sha256(a.destination.read_bytes()).hexdigest(),'出力':str(a.destination)}
Path('C:/Users/SEIGI-N13/work-projects/tmp/pdfs/gt2-bool/revision-verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(verification,ensure_ascii=False,indent=2))
