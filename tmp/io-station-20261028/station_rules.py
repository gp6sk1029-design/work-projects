"""利用者が確認した所属と、既存工程名に一致する機器だけを対象にする。"""
import re

SEGMENT=re.compile(r'【[XY][0-9A-F]+】[^【\r\n]*')
EXISTING_ST=re.compile(r'ST\d+')
SIDE=re.compile(r'[AB]\([左右]側\)')

def station(segment):
    # これらの共通信号は利用者指定により元のまま残す。
    if re.search(r'アキューム|コンテナ|段バラシ|箱入れ|箱詰|受渡|受け渡|取出しコンベア|搬送コンベア|非常停止|ドア|エア圧|シグナル|プレス|入口|スタート|ストップ|リセット',segment):
        return None
    m=re.search(r'ワーク位置([0-7])|位置([1-6])ストッパー',segment)
    if m:return int(m[1] or m[2])
    if re.search(r'NG1',segment):return 3
    if re.search(r'NG2|ストック(?:フォルダ|機種)|排出(?:チャック|フォルダ|ホルダ)',segment):return 7
    m=re.search(r'反転\s*([12])|反転\s*オリエンタルモータ([12])',segment)
    if m:return {1:4,2:6}[int(m[1] or m[2])]
    if '高さ検査' in segment:return 2
    if re.search(r'供給(?:スライド|ピックアップ|チャック)',segment):return 0
    return None

def update(comment):
    if EXISTING_ST.search(comment):return comment
    def add(m):
        text=m[0]
        if EXISTING_ST.search(text):return text
        st=station(text)
        if st is None:return text
        side=SIDE.search(text)
        end=side.end() if side else text.index('】')+1
        return text[:end]+f'ST{st} '+text[end:].lstrip(' ')
    return SEGMENT.sub(add,comment)
