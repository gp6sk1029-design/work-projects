from pathlib import Path
import json,re,runpy
b=Path(__file__).parent
# check.pyの反例は読取り用であり、importしても原本には書かない。
n=runpy.run_path(str(b/'check.py'));Model=n['Model'];rows=n['rows'];s=n['s'];M=n['M'];d=n['d']
receivers=[]
for sec in d['sections']:
    for i,r in enumerate(sec['rows']):
        for c in r['CLs']:
            if c['__type']=='ST' and c.get('Var')=='Out_CYw_Ejc_Hldr_Feed_A_H_Auto[2]':receivers.append([sec['name'],i])
assert receivers==[]
print('UNUSED_RETURN_INDEX_2',receivers)
for i in list(range(81,91))+list(range(162,172)):
    r=s['RCON_IAI'][i]
    print('RCON',i,r.get('CMT','').replace('\r\n',' / '),[(c['__type'],c.get('Var'),c.get('Name')) for c in r['CLs'] if c['__type']!='HL'])
# 次のOR要求が立つ瞬間に前要求もまだONの例。Ready確認TONが再度立ち上がらない。
z=Model({'RCON1_5_Auto[2]':True,'RCON1_5_Ready':True})
for tick in range(25):z.row(s['RCON_IAI'][201],201)
z.e['RCON1_5_Auto[3]']=True;z.e['RCON1_5_MoveDone']=True;z.row(s['RCON_IAI'][201],201)
z.e['RCON1_5_Auto[2]']=False;z.e['RCON1_5_MoveDone']=False
for tick in range(25):z.row(s['RCON_IAI'][201],201)
assert not z.e['RCON1_5_M[1]']
print('OR_CONTINUOUS',{'next_request':z.e['RCON1_5_Auto[3]'],'M1_after_25_scans':z.e['RCON1_5_M[1]']})
# 仮に下降要求番号の重複を直しても、同一走査で旧Doneを拾う実行順の問題が残る。
copies=__import__('copy').deepcopy(rows)
for c in copies[19]['CLs']:
    if c['__type']=='ST' and c.get('Var')=='RCON1_5_Auto[2]':c['Var']='RCON1_5_Auto[5]'
z=Model({M(13):True,'RCON1_5_MoveDone':True,'Out_CYw_Disc_Chk_A_F_Done':True,'Station_A_Data[7].Total_Judge':1,'A_SF_CT':0})
for i in [11,12,13,14]:z.row(copies[i],i)
assert z.e[M(17)]
print('OLD_DONE_AFTER_UNIQUE_NUMBER_FIX',{'M14':z.e[M(14)],'M15':z.e[M(15)],'M16':z.e[M(16)],'M17':z.e[M(17)]})
extra={'unused_return_index_2_writers':receivers,'continuous_OR_blocks_next_request':True,'old_done_still_passes_after_unique_request_numbers':True}
(b/'extra_checks.json').write_text(json.dumps(extra,ensure_ascii=False,indent=2),encoding='utf-8')
