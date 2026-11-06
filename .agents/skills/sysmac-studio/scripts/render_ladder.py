"""明示配置JSONから、白背景・黒線・青変更点の説明用ラダーPNGを描く。"""
from pathlib import Path
from functools import lru_cache
import argparse,json
from PIL import Image,ImageDraw,ImageFont

INK='#17212b'
BLUE='#0068a8'

def render(spec, output):
    width=int(spec.get('width',1740));height=int(spec.get('height',1050))
    if not (400<=width<=1800 and 250<=height<=1800):raise ValueError('画像は幅400～1800、高さ250～1800px。大きい図は分割する。')
    fontfile=Path(spec.get('font','C:/Windows/Fonts/meiryo.ttc'))
    if not fontfile.is_file():raise ValueError('日本語フォントの絶対パスをfontに指定する。')
    scale=2
    im=Image.new('RGB',(width*scale,height*scale),'white');d=ImageDraw.Draw(im)
    @lru_cache(maxsize=48)
    def font(size):return ImageFont.truetype(str(fontfile),int(size*scale))
    def color(item):
        key=item.get('color','ink')
        if key not in ['ink','change']:raise ValueError('colorはinkまたはchange。')
        return BLUE if key=='change' else INK
    def point(x,y):
        if not (0<=x<width and 0<=y<height):raise ValueError(f'図の外の座標：{x},{y}')
        return (round(x*scale),round(y*scale))
    def wire(points,fill=INK):
        if len(points)<2:raise ValueError('結線は2点以上必要。')
        d.line([point(*p) for p in points],fill=fill,width=3*scale)
    def lines(text,size,limit):
        result=[]
        for paragraph in str(text).split('\n'):
            buf=''
            for ch in paragraph:
                if buf and limit and d.textlength(buf+ch,font=font(size))>limit*scale:result.append(buf);buf=''
                buf+=ch
            result.append(buf)
        return result
    def text(x,y,value,size=24,fill=INK,limit=None,align='left'):
        if align not in ['left','center']:raise ValueError('alignはleftまたはcenter。')
        for n,line in enumerate(lines(value,size,limit)):
            length=d.textlength(line,font=font(size))/scale
            left=x-length/2 if align=='center' else x
            if left<0 or left+length>width or y+n*size*1.35+size>height:raise ValueError(f'文字が画像外：{line}')
            d.text(point(left,y+n*size*1.35),line,font=font(size),fill=fill,anchor='lt')
    for item in spec['elements']:
        kind=item['type'];fill=color(item)
        if kind=='wire':wire(item['points'],fill);continue
        x=float(item['x']);y=float(item['y'])
        if kind=='text':
            text(x,y,item['text'],item.get('size',24),fill,item.get('width'),item.get('align','left'));continue
        w=float(item.get('width',150));label=item.get('label','')
        if kind=='contact':
            a=x+w/2-13;b=x+w/2+13
            wire([[x,y],[a,y]]);wire([[b,y],[x+w,y]])
            wire([[a,y-21],[a,y+21]],fill);wire([[b,y-21],[b,y+21]],fill)
            if item.get('nc'):wire([[a-5,y+24],[b+5,y-24]],fill)
            text(x+w/2,y-65,label,item.get('size',24),fill,w+25,'center')
        elif kind=='block':
            h=float(item.get('height',76));d.rectangle([point(x,y-h/2),point(x+w,y+h/2)],outline=fill,width=3*scale)
            size=item.get('size',23);ll=lines(label,size,w-18)
            if len(ll)*size*1.35>h-10:raise ValueError(f'ブロックの文字が収まらない：{label}')
            text(x+w/2,y-len(ll)*size*1.35/2,'\n'.join(ll),size,fill,w-18,'center')
        elif kind=='coil':
            if w<100:raise ValueError('コイルの幅は100px以上。')
            center=x+w/2;wire([[x,y],[center-30,y]]);wire([[center+30,y],[x+w,y]])
            d.arc([point(center-30,y-23),point(center+8,y+23)],90,270,fill=fill,width=3*scale)
            d.arc([point(center-8,y-23),point(center+30,y+23)],270,450,fill=fill,width=3*scale)
            mode=item.get('mode','normal')
            if mode not in ['normal','set','reset']:raise ValueError('modeはnormal/set/reset。')
            if mode!='normal':text(center,y-15,'S' if mode=='set' else 'R',22,fill,align='center')
            text(center,y-65,label,item.get('size',24),fill,w+25,'center')
        else:raise ValueError('不明な図要素：'+kind)
    output=Path(output);output.parent.mkdir(parents=True,exist_ok=True)
    im.resize((width,height),Image.Resampling.LANCZOS).save(output,format='PNG')
    return {'output':str(output.resolve()),'width':width,'height':height,'elements':len(spec['elements']),'logic_verified':False}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args();spec=json.loads(Path(args.input).read_text(encoding='utf-8-sig'))
    result=render(spec,args.output)
    print(json.dumps(result,ensure_ascii=False))

if __name__=='__main__':main()
