"""GT2/DL-EP1の固定割付を0始まりBOOL配列に換算したPDFを作る。"""
import json
import shutil
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from pypdf import PdfReader

ROOT = Path('C:/Users/SEIGI-N13/work-projects')
OUT = ROOT / 'output/pdf/GT2_DL-EP1_BOOL配列_入出力対応表_ID01-ID15_20261015.pdf'
DESKTOP = Path('C:/Users/SEIGI-N13/Desktop') / OUT.name
OUT.parent.mkdir(parents=True, exist_ok=True)
assert not OUT.exists() and not DESKTOP.exists(), '既存の資料は上書きしない'
pdfmetrics.registerFont(TTFont('JP', 'C:/Windows/Fonts/msgothic.ttc', subfontIndex=0))
W,H = landscape(A4)
M = 36
WIDTH = W - M*2
NAVY = colors.HexColor('#183B56')
BLUE = colors.HexColor('#136F87')
LIGHT = colors.HexColor('#EFF6F8')
INK = colors.HexColor('#20313C')
GRAY = colors.HexColor('#536775')
LINE = colors.HexColor('#D6E1E7')
WARN = colors.HexColor('#FFF3DC')
STYLE = ParagraphStyle('body', fontName='JP', fontSize=10, leading=15, textColor=INK)
SMALL = ParagraphStyle('small', parent=STYLE, fontSize=8.5, leading=12)
HEAD = ParagraphStyle('head', parent=STYLE, fontSize=9, leading=12, textColor=colors.white, alignment=1)
CELL = ParagraphStyle('cell', parent=STYLE, fontSize=10, leading=13, alignment=1)
c = canvas.Canvas(str(OUT), pagesize=(W,H))
c.setTitle('GT2 / DL-EP1 BOOL配列 入出力対応表 ID01-ID15')
c.setAuthor('生産技術資料 / Codex')
page = 0
checks = []
SRC = 'https://manualmachine.com/keyence/dlep1/1579627-user-manual/'
OFFICIAL = 'https://www.keyence.com/support/user/controls/plc/connection_guide/kv-x_dl-ep1/'

def paragraph(text, x, top, width=WIDTH, style=STYLE):
    obj = Paragraph(text, style)
    _,height = obj.wrap(width, H)
    assert top-height >= 31, '本文がページ下端を超えている'
    obj.drawOn(c,x,top-height)
    return top-height

def begin(number, title, subtitle):
    global page
    page += 1
    c.setFillColor(NAVY); c.rect(0,H-12,W,12,fill=1,stroke=0)
    c.setFillColor(BLUE); c.setFont('JP',9); c.drawString(M,H-32,'GT2 / DL-EP1  |  SYSMAC STUDIO  |  BOOL ARRAY MAP')
    c.setFillColor(INK); c.setFont('JP',20); c.drawString(M,H-62,f'{number}  {title}')
    paragraph(subtitle,M,H-77,style=SMALL)
    c.setStrokeColor(LINE); c.line(M,30,W-M,30)
    c.setFillColor(GRAY); c.setFont('JP',8)
    c.drawString(M,18,'2026/10/15  |  0始まりのBOOL配列・先頭オフセット0・標準Assembly100/101が前提')
    c.drawRightString(W-M,18,f'{page} / 6')
    return H-110

def section(title, top):
    c.setFillColor(BLUE); c.setFont('JP',12); c.drawString(M,top-12,title)
    return top-24

def table(headers, rows, top, widths=None, rowheight=20, fontsize=10):
    if widths is None: widths=[WIDTH/len(headers)]*len(headers)
    assert abs(sum(widths)-WIDTH)<0.01
    cell_style=ParagraphStyle('table-cell',parent=CELL,fontSize=fontsize,leading=fontsize+3)
    cells=[[Paragraph(str(h),HEAD) for h in headers]]
    cells += [[Paragraph(str(v),cell_style) for v in row] for row in rows]
    t=Table(cells,colWidths=widths,rowHeights=[31]+[rowheight]*len(rows))
    t.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(-1,0),NAVY),('VALIGN',(0,0),(-1,-1),'MIDDLE'),
        ('TOPPADDING',(0,0),(-1,-1),3),('BOTTOMPADDING',(0,0),(-1,-1),3),
        ('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,LIGHT]),
        ('LINEBELOW',(0,0),(-1,0),0.6,NAVY),
        ('LINEBELOW',(0,1),(-1,-1),0.3,LINE),
        ('LEFTPADDING',(0,0),(-1,-1),5),('RIGHTPADDING',(0,0),(-1,-1),5),
    ]))
    _,height=t.wrap(WIDTH,H)
    assert top-height>=40, f'表がページ下端を超える: {page}'
    t.drawOn(c,M,top-height)
    return top-height-12

def note(text,top,warning=False):
    obj=Paragraph(text,SMALL); _,height=obj.wrap(WIDTH-20,H)
    assert top-height-14>=33
    c.setFillColor(WARN if warning else LIGHT)
    c.rect(M,top-height-14,WIDTH,height+14,stroke=0,fill=1)
    obj.drawOn(c,M+10,top-height-7)
    return top-height-24

def end(): c.showPage()
def pos(base,ident): return f'[{base+ident-1}]'

# 1: 型と単位、機器認識と固定割付を最初に明確にする。
y=begin('01','最初に確認すること','台数が増えても番号は動きません。未接続IDの場所も、あらかじめ確保されています。')
y=table(['方向（PLC基準）','参考の変数定義','通信サイズ','接続先Assembly'],[
    ['出力：PLC → GT2','DLEP1_OUT : ARRAY[0..79] OF BOOL','80 bit = 10 Byte','101 (65H)'],
    ['入力：GT2 → PLC','DLEP1_IN : ARRAY[0..1343] OF BOOL','1344 bit = 168 Byte','100 (64H)'],
],y,[133,350,140,WIDTH-623],rowheight=28,fontsize=10)
y=note('本表は標準通信データをBOOLの添字へ換算した参考表です。現在の変数型・タグの並び・サイズ・接続先Assemblyは未確認です。BYTE/WORD配列、1始まり、前置きデータがある構成には、この番号をそのまま適用しないでください。',y,True)
y=section('接続した機器のIDと、PLCが使う番号は別のしくみ',y)
y=paragraph('親機をID01として、増設した子機がID02、ID03…となります。任意のIDをコメントで設定するのではなく、機器側の接続順で割り当てられます。右・左・A・Bなどの設置位置は、実機とIDを確認してからコメントに記入します。',M,y)
y-=14
y=table(['固定の指令領域','BOOLの番号','2台接続時','3台接続時'],[
    ['プリセット：ID01','OUT[0]','1台目に使用','1台目に使用'],
    ['プリセット：ID02','OUT[1]','2台目に使用','2台目に使用'],
    ['プリセット：ID03','OUT[2]','未使用（タイミングにはならない）','3台目に使用'],
    ['タイミング：ID01','OUT[16]','1台目に使用','1台目に使用'],
],y,[175,120,240,WIDTH-535],rowheight=22,fontsize=9)
y=paragraph('1つの指令に16 bit（ID01-ID15の15 bit＋予約1 bit）を固定確保します。したがって、タイミングは台数に関係なくOUT[16]からです。本資料のOUT[n]はDLEP1_OUT[n]、IN[n]はDLEP1_IN[n]を表します。',M,y,style=SMALL)
end()

# 2: 指令出力。未使用・予約を含め80 bitを網羅。
y=begin('02','PLC出力 / 操作指令','各セルはDLEP1_OUTのBOOL配列番号です。ON条件・OFF復帰条件は機能別に設計してください。')
rows=[]
for ident in range(1,16):
    rows.append([f'ID{ident:02d}','親機' if ident==1 else f'子機{ident-1}',pos(0,ident),pos(16,ident),pos(32,ident),pos(48,ident)])
    for base in (0,16,32,48): checks.append(('OUT',ident,base+ident-1))
y=table(['センサID','通常の構成','プリセット','タイミング','リセット','エラークリア'],rows,y,[95,150,130,130,130,WIDTH-635],rowheight=20,fontsize=10)
y=note('予約：OUT[15]・[31]・[47]・[63]はシステム予約。OUT[64]-[79]はGT2の外部入力5（未割付）。予約・未割付は操作しないでください。',y)
y=paragraph('プリセット先が0の場合に「ゼロセット」になります。プリセットとリセットは別機能です。タイミングはアンプ側の「個別入力」「外部タイミング入力」設定を確認してください。指令は対応する応答と通信状態を確認し、応答待ちの時間上限を設けます。',M,y,style=SMALL)
end()

# 3: センサごとの判定とエラー。
y=begin('03','PLC入力 / 判定・センサエラー','各セルはDLEP1_INのBOOL配列番号です。HIGH/LOW/GOはGT2からPLCへ入る信号です。')
headers=['センサID','センサエラー','HIGH','LOW','GO','HH','LL']
bases=[16,144,160,176,192,208]
rows=[[f'ID{i:02d}']+[pos(base,i) for base in bases] for i in range(1,16)]
for i in range(1,16):
    for base in bases: checks.append(('IN',i,base+i-1))
y=table(headers,rows,y,[95]+[(WIDTH-95)/6]*6,rowheight=20,fontsize=10)
y=note('各列の15台分の直後の1 bitは予約です。例：GOはIN[176]-[190]がID01-ID15、IN[191]は予約です。未接続センサの判定を合否判定に使わないでください。',y)
y=paragraph('HH/LLを使う場合はアンプ側の特殊出力設定を確認します。GT2-71MC系では出力の割付がない機種があります。GOのON/OFFだけでなく、通信正常・センサエラー・現在値の有効性を合わせて判断してください。',M,y,style=SMALL)
end()

# 4: 応答と値の有効性。
y=begin('04','PLC入力 / 指令応答・現在値の状態','応答4種類と現在値0の異常3種類。各セルはDLEP1_INのBOOL配列番号です。')
bases=[224,240,256,272,48,64,80]
rows=[[f'ID{i:02d}']+[pos(base,i) for base in bases] for i in range(1,16)]
for i in range(1,16):
    for base in bases: checks.append(('IN',i,base+i-1))
y=table(['センサID','プリセット<br/>応答','タイミング<br/>応答','リセット<br/>応答','エラークリア<br/>応答','現在値0<br/>上限オーバー','現在値0<br/>下限オーバー','現在値0<br/>無効'],rows,y,[83]+[(WIDTH-83)/7]*7,rowheight=20,fontsize=10)
y=note('「上限/下限オーバー」は測定可能範囲の逸脱であり、HIGH/LOWの合否判定とは別です。「現在値0 無効」がONのときは、その測定値を有効な高さとして使用しないでください。',y)
y=paragraph('指令に対応する応答は、測定完了・測定値安定や機器接続の証明とは限りません。マニュアル上は存在しない外部入力のIDでも応答が出る場合があります。通信診断・実際の接続ID・測定条件を別に確認してください。',M,y,style=SMALL)
end()

# 5: 数値領域をBOOL添字で示すが、値を1bitと誤解させない。
y=begin('05','PLC入力 / 測定値（現在値0）','測定値1個 = 32 bitの符号付き整数です。BOOLを1個だけ読んでも高さにはなりません。')
rows=[]
for i in range(1,16):
    start=384+32*(i-1)
    rows.append([f'ID{i:02d}',f'[{start}]-[{start+31}]',f'[{start}]-[{start+15}]',f'[{start+16}]-[{start+31}]'])
    checks.append(('VALUE0',i,start))
y=table(['センサID','現在値0：32 bit全体','下位16 bit','上位16 bit'],rows,y,[115,245,205,WIDTH-565],rowheight=20,fontsize=10)
y=note('各行の先頭が数値のbit0、末尾がbit31（符号bit）です。下位バイトから格納されます。符号付きDINTへ正しく復元し、アンプの小数桁・換算条件に合わせて扱ってください。',y)
y=paragraph('現在値0がP.V.（判定値）かR.V.（生値）かは、アンプの演算設定で変わります。mmへの換算倍率は本表では確定していません。GT2では現在値1の測定領域IN[864]-[1343]は未割付です。',M,y,style=SMALL)
end()

# 6: 共通・未使用領域を区別して入力全体の抜けを防止。
y=begin('06','共通領域・予約領域 / 使用前チェック','センサごとのBOOL信号と、複数bitで構成する数値・共通状態を区別してください。')
y=table(['入力BOOLの範囲','内容','扱い'],[
    ['[0]-[15]','DL-EP1共通ステータス','ID別ではない。個別bitの意味はマニュアル3-9を確認'],
    ['[32]-[47]','センサ警告状態の枠','GT2では未割付（各枠末尾は予約）'],
    ['[96]-[143]','現在値1の上限/下限/無効の枠','GT2では現在値1なし。使用しない'],
    ['[288]-[303]','外部入力5応答の枠','GT2では未割付（末尾は予約）'],
    ['[304]-[319]','システム予約','使用しない'],
    ['[320]-[335]','エラー対象ID','16 bit全体をUINTとして復元（単一BOOLではない）'],
    ['[336]-[351]','エラーコード','16 bit全体をUINTとして復元（単一BOOLではない）'],
    ['[352]-[383]','警告ID・警告コードの枠','GT2では未割付'],
    ['[864]-[1343]','現在値1の枠','GT2では未割付'],
],y,[115,190,WIDTH-305],rowheight=21,fontsize=9)
y=paragraph('入力のID別16 bit枠では、各枠の末尾bit（31・47・63…303）は予約です。ページ3・4の表では有効なID01-ID15だけを示しています。共通状態[0]-[15]は予約末尾の規則を適用しません。',M,y,style=SMALL)-12
y=section('使用前の確認',y)
y=paragraph('1. 現在の変数型がBOOL・0始まりで、タグ先頭に別データがないことを確認。<br/>2. 入力100/168 Byte、出力101/10 Byteと接続先IPを確認。別のDL-EP1は別のID系列です。<br/>3. 親機・子機の型式と実ID、設置位置の対応を確認。通常は最大15台。GT2-100系等は別の制約あり。<br/>4. 設備を安全に停止し、全体再ビルドと通信・指令・応答の動作確認後に運転へ適用。増設接続は電源OFF。',M,y,style=SMALL)-10
y=paragraph('出典：KEYENCE「DL-EP1 User\'s Manual (GT2)」2-6/2-7、3-9/3-10、3-11/3-12、3-15-3-18（公開コピー）。<br/><link href="'+SRC+'" color="#136F87">メーカー作成マニュアルの公開コピーを開く</link> / <link href="'+OFFICIAL+'" color="#136F87">KEYENCE公式 接続ガイド・台数制約</link><br/>この資料は標準割付の換算表であり、現在の実機設定を確認済みとするものではありません。',M,y,style=SMALL)
end()
assert page==6
# 境界・予約bit除外・主要既知点を機械検証する。
assert len(checks)==270
assert len(set(checks))==len(checks)
assert all(0<=v<80 for typ,ident,v in checks if typ=='OUT')
assert all(0<=v<1344 for typ,ident,v in checks if typ!='OUT')
assert ('OUT',3,2) in checks and ('OUT',3,18) in checks
assert ('IN',15,190) in checks and ('VALUE0',15,832) in checks
c.save()
reader=PdfReader(OUT)
assert len(reader.pages)==6
texts=[p.extract_text() for p in reader.pages]
assert all('ID15' in texts[i] for i in (1,2,3,4))
assert '[862]' not in texts[4]
assert '[832]-[863]' in texts[4]
shutil.copy2(OUT,DESKTOP)
assert OUT.read_bytes()==DESKTOP.read_bytes()
info={'ページ数':6,'ID範囲':'ID01-ID15','検証したID別対応数':len(checks),'型':'0始まりBOOL配列の換算表','現行設定確認':'未実施','成果物':str(DESKTOP),'出典':SRC}
(ROOT/'tmp/pdfs/gt2-bool/verification.json').write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(info,ensure_ascii=False,indent=2))
