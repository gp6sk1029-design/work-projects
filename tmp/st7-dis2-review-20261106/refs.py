"""関係節と入出力の参照一覧。"""
from pathlib import Path
import json,re
b=Path(__file__).parent;d=json.loads((b/'snapshot.json').read_text(encoding='utf-8'))
targets={'ST7_A_Dis2_左SF排出','Input_入力','RCON_IAI','Output_出力','Ins_A_Cv_左検査Cv','BoxPacking_箱詰め','Data_データ処理','ST1_A_Sply_左供給'}
print('SECTIONS',[(s['name'],len(s['rows'])) for s in d['sections']])
for s in d['sections']:
    if s['name']=='ST7_A_Dis2_左SF排出':continue
    for i,r in enumerate(s['rows']):
        txt=json.dumps(r,ensure_ascii=False)
        hit=any(t in txt for t in ['A_SF_CT','StackPitch','RCON1_5_Auto','RCON1_3_Auto','ST7_A_Dis2','Sen_SH_B','Sen_SH_A','NG2_Tray_A_Full','NG2_Tray_B_Full','Station_A_Data[7]','Out_CYw_Disc_Chk_A','Out_CYw_Ejc_Hldr_Feed_A','RCON1_5_SafePos','RCON1_3_SafePos'])
        hit|= s['name']=='RCON_IAI' and (109<=i<=122 or 190<=i<=203)
        hit|= s['name']=='BoxPacking_箱詰め' and any(t in txt for t in ['Wait_Pickup','Pickup_Done'])
        if not hit:continue
        print('\nSECTION',s['name'],'ROW',i,r.get('CMT','').replace('\r\n',' / '))
        for c in r['CLs']:
            if c['__type']=='HL':continue
            a={k:c[k] for k in ['__type','Var','Name','Not','X','Y','TXT'] if k in c}
            for io in ['In','Out']:
                if io in c:a[io]=[(z.get('Arg'),z.get('Var')) for z in c[io] if z.get('Var')]
            print(json.dumps(a,ensure_ascii=False))
        print('VLs',r['VLs'])
