from pathlib import Path
import json,re
b=Path(__file__).parent;d=json.loads((b/'snapshot.json').read_text(encoding='utf-8'))
for s in d['sections']:
    rows=range(len(s['rows'])) if s['name'] in ['AutoMode_自動運転','Ins_A_Cv_左検査Cv','Initial_初期化処理'] else ([0,1,31,32,33,34,35,36,37,38,39,40] if s['name']=='Error_エラー処理' else ([81,87,89,162,168,170,456] if s['name']=='RCON_IAI' else []))
    for i in rows:
        r=s['rows'][i];print(s['name'],i,r.get('CMT','').replace('\r\n',' / '))
        print(json.dumps({'CLs':[c for c in r['CLs'] if c['__type']!='HL'],'VLs':r['VLs']},ensure_ascii=False))
names={'In_Sen_SH_A_Ent','In_Sen_SH_A_Ext','In_Sen_SH_B_Ent','In_Sen_SH_B_Ext','In_Sen_NG2_Tray_A_Full','In_Sen_NG2_Tray_B_Full','In_Sen_Work_A_Pos_07','In_SenCY_Disc_Chk_A_H','In_SenCY_Disc_Chk_A_F','In_SenCY_Ejc_SH_Feed_A_H','In_SenCY_Ejc_SH_Feed_A_F','In_SenCY_SH_A_Turn_F','In_SenCY_SH_A_Turn_H','RCON1_5_SafePos_mm','A_SF_CT','A_SF_StackStepOffset','HMI_A_SF_StackPitch_mm','A_SF_StackTarget_mm','Station_A_Data','Retry'}
for txt in d['variables'].values():
    for line in txt.splitlines():
        fields=dict(x.split('=',1) for x in line.split('\t') if '=' in x)
        if fields.get('N') in names:print('VAR',line[:1500])
