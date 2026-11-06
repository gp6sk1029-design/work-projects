"""隔離した合成プロジェクトだけで編集・保存・拒否条件を確認する。"""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
from argparse import Namespace
from tempfile import TemporaryDirectory,gettempdir
import argparse,json,unittest,copy,sys
import sysmac as sm

opts=argparse.ArgumentParser();opts.add_argument('--native',action='store_true');params,rest=opts.parse_known_args()

def row(index,comment):
    return sm.reindex({'CLs':[{'__type':'LD','Var':'Enable'},{'__type':'ST','Var':f'Step_M[{index}]','X':1}],'VLs':[],'CMT':comment})

def fixture(path):
    oem='''<Root><Entity type="Solution" id="fixture-project" name="スキル検証用"><ChildEntities><Entity type="Pou" id="pou" name="Main"><ChildEntities><Entity type="Variables" id="vars" name="Variables"/><Entity type="PouBody" id="first" name="第一工程"/><Entity type="PouBody" id="second" name="第二工程"/></ChildEntities></Entity></ChildEntities></Entity></Root>'''
    data={'fixture-project.oem':oem.encode('utf-8'),'vars.xml':b'[SLWD version=1.0]\r\n_EN=Variables\r\n+GN=VAR\r\n++D=BOOL\tN=Enable\tG=VAR\r\n++D=ARRAY[0..99] OF BOOL\tN=Step_M\tG=VAR\r\n',
        'first.xml':b'\xef\xbb\xbf'+''.join(json.dumps(r,ensure_ascii=False,separators=(',',':'))+'\r\n' for r in [row(1,'【開始】\r\n【X1】：検証入力'),row(2,'次工程')]).encode('utf-8'),
        'second.xml':(json.dumps(row(3,'終了'),ensure_ascii=False,separators=(',',':'))+'\r\n').encode('utf-8'),'unchanged.dat':b'\x00\x01\xff\x0aKEEP'}
    with ZipFile(path,'w',compression=ZIP_DEFLATED) as z:
        for k,v in data.items():z.writestr(k,v)
    return path

class SkillTests(unittest.TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory(prefix='sysmac-skill-test-');self.root=Path(self.temp.name)
        self.source=fixture(self.root/'source.smc2');self.plan=self.root/'plan.json'
        self.candidate=self.root/'candidate.smc2';self.stage_report=self.root/'stage.json'
    def tearDown(self):
        self.assertEqual(self.root.resolve().parent,Path(gettempdir()).resolve())
        self.assertTrue(self.root.name.startswith('sysmac-skill-test-'))
        self.temp.cleanup()
    def stage(self,ops):
        sm.save_json(self.plan,{'source_sha256':sm.Project(self.source).fingerprint,'operations':ops})
        return sm.stage(Namespace(source=str(self.source),plan=str(self.plan),output=str(self.candidate),report=str(self.stage_report)))
    def comments(self,two=False):
        ops=[{'op':'comment','section':'第一工程','row':0,'expected':sm.Project(self.source).section('第一工程')['rows'][0]['CMT'],'text':'【改行済み】\n\n【X1】：検証入力'}]
        if two:ops.append({'op':'comment','section':'第二工程','row':0,'expected':'終了','text':'【完了】'})
        return self.stage(ops)
    def internal(self):
        folder=self.root/'managed'/'fixture-project';folder.mkdir(parents=True)
        with ZipFile(self.source) as z:
            for name in z.namelist():(folder/name).write_bytes(z.read(name))
        return folder
    def args_direct(self,folder,apply=False,closed=False):
        return Namespace(project=str(folder),source=str(self.candidate),expected_name='スキル検証用',report=str(self.root/'direct.json'),apply=apply,project_closed=closed)
    def test_inspect(self):
        p=sm.Project(self.source);self.assertEqual(len(p.sections),2);self.assertEqual(len(p.variable_parts),1)
        self.assertEqual(p.section('第一工程')['key'],'Main/第一工程')
    def test_discovery_skips_empty_other_project(self):
        folder=self.internal();bad=folder.parent/'empty';bad.mkdir();(bad/'empty.oem').write_bytes(b'')
        result=sm.find_projects(folder.parent,'スキル検証用')
        self.assertEqual(len(result['matches']),1);self.assertEqual(result['skipped_unreadable'],1)
    def test_comment_retains_logic_and_bytes(self):
        r=self.comments();self.assertTrue(r['comment_only'])
        with ZipFile(self.source) as a,ZipFile(self.candidate) as b:
            self.assertEqual(a.read('unchanged.dat'),b.read('unchanged.dat'))
            self.assertEqual(a.read('second.xml'),b.read('second.xml'))
            self.assertTrue(b.read('first.xml').startswith(b'\xef\xbb\xbf'))
        diff=sm.comparison(sm.Project(self.source),sm.Project(self.candidate));self.assertFalse(diff['control_difference']);self.assertEqual(diff['comment_rows'],1)
    def test_simultaneous_number_mapping(self):
        self.stage([{'op':'map-indices','section':'第一工程','tag':'Step_M','mapping':{'1':2,'2':3}}])
        rs=sm.Project(self.candidate).section('第一工程')['rows']
        self.assertEqual([r['CLs'][1]['Var'] for r in rs],['Step_M[2]','Step_M[3]'])
    def test_wrong_source_hash_rejected(self):
        sm.save_json(self.plan,{'source_sha256':'bad','operations':[]})
        with self.assertRaises(ValueError):sm.stage(Namespace(source=str(self.source),plan=str(self.plan),output=str(self.candidate),report=str(self.stage_report)))
        self.assertFalse(self.candidate.exists())
    def test_wrong_old_comment_rejected(self):
        with self.assertRaises(ValueError):self.stage([{'op':'comment','section':'第一工程','row':0,'expected':'違う旧版','text':'変更'}])
    def test_insert_rung(self):
        self.stage([{'op':'insert-row','section':'第一工程','row':1,'value':row(4,'挿入'),'reindex':True}])
        self.assertEqual(len(sm.Project(self.candidate).section('第一工程')['rows']),3)
    def test_part_and_row_mix_rejected(self):
        replacement=self.root/'part.xml';replacement.write_bytes(sm.Project(self.source).entries['first.xml'])
        with self.assertRaises(ValueError):self.stage([{'op':'replace-part','part':'first.xml','expected_sha256':sm.sha(replacement.read_bytes()),'file':str(replacement)},{'op':'comment','section':'第一工程','row':0,'expected':'','text':'bad'}])
    def test_direct_dry_run_does_not_write(self):
        self.comments();folder=self.internal();before=sm.Project(folder).fingerprint
        result=sm.direct_comments(self.args_direct(folder));self.assertFalse(result['applied']);self.assertEqual(sm.Project(folder).fingerprint,before)
    def test_direct_requires_closed_confirmation(self):
        self.comments();folder=self.internal();before=sm.Project(folder).fingerprint
        with self.assertRaises(ValueError):sm.direct_comments(self.args_direct(folder,True,False))
        self.assertEqual(sm.Project(folder).fingerprint,before)
    def test_direct_backup_apply_and_reload(self):
        self.comments(True);folder=self.internal();before=sm.Project(folder)
        result=sm.direct_comments(self.args_direct(folder,True,True));self.assertTrue(result['applied'])
        with ZipFile(result['backup']) as z:
            for part,data in before.entries.items():self.assertEqual(z.read(part),data)
        diff=sm.comparison(sm.Project(folder),sm.Project(self.candidate));self.assertEqual(diff['comment_rows'],0);self.assertFalse(diff['control_difference'])
    def test_direct_blocks_wrong_target(self):
        self.comments();folder=self.internal();args=self.args_direct(folder,True,True);args.expected_name='別のプロジェクト'
        with self.assertRaises(ValueError):sm.direct_comments(args)
    def test_direct_blocks_logic_change(self):
        self.stage([{'op':'map-indices','section':'第一工程','tag':'Step_M','mapping':{'1':5}}]);folder=self.internal();before=sm.Project(folder).fingerprint
        with self.assertRaises(ValueError):sm.direct_comments(self.args_direct(folder,True,True))
        self.assertEqual(sm.Project(folder).fingerprint,before)
    def test_direct_blocks_declaration_difference(self):
        self.comments();folder=self.internal();p=folder/'vars.xml';p.write_bytes(p.read_bytes().replace(b'N=Enable',b'N=OtherEnable'))
        with self.assertRaises(ValueError):sm.direct_comments(self.args_direct(folder,True,True))
    def test_direct_disallows_report_inside_project(self):
        self.comments();folder=self.internal();args=self.args_direct(folder,True,True);args.report=str(folder/'result.json')
        with self.assertRaises(ValueError):sm.direct_comments(args)
    def test_partial_internal_failure_restores_written_files(self):
        self.comments(True);folder=self.internal();before=sm.Project(folder).fingerprint;real=sm.atomic_write;state={'failed':False}
        def fail_second(path,data,fallback=False):
            if Path(path).name=='second.xml' and not state['failed']:state['failed']=True;raise OSError('検証用の書込み失敗')
            return real(path,data,fallback)
        sm.atomic_write=fail_second
        try:
            with self.assertRaises(OSError):sm.direct_comments(self.args_direct(folder,True,True))
        finally:sm.atomic_write=real
        self.assertEqual(sm.Project(folder).fingerprint,before)
    def test_sync_internal_to_smc2(self):
        self.comments();folder=self.internal();sm.direct_comments(self.args_direct(folder,True,True))
        target=sm.Project(self.source);sm.sync_comments(target,sm.Project(folder));dest=self.root/'roundtrip.smc2';target.write_archive(dest)
        self.assertFalse(sm.comparison(sm.Project(dest),sm.Project(self.candidate))['sections'])
    def test_zip_path_escape_rejected(self):
        with ZipFile(self.source,'a') as z:z.writestr('../unexpected.xml',b'x')
        with self.assertRaises(ValueError):sm.Project(self.source)
    def test_publish_rejects_changed_source(self):
        self.comments();self.source.write_bytes(self.source.read_bytes()+b'changed')
        args=Namespace(stage_report=str(self.stage_report),native_report=None,destination=str(self.root/'out.smc2'),report=str(self.root/'pub.json'),allow_logic=False,history=None,overwrite=False,archive_source=False)
        with self.assertRaises(ValueError):sm.publish(args)
        self.assertFalse((self.root/'out.smc2').exists())
    @unittest.skipUnless(params.native,'--native指定時に実メーカー同梱処理を使用')
    def test_native_and_publish_with_backup(self):
        self.comments();nr=self.root/'native.json';result=sm.native(Namespace(source=str(self.candidate),report=str(nr),install_root='C:/Program Files (x86)/OMRON/Sysmac Studio'))
        self.assertTrue(result['verified']);self.assertEqual(result['rows'],3)
        dest=self.root/'published.smc2';dest.write_bytes(self.source.read_bytes())
        args=Namespace(stage_report=str(self.stage_report),native_report=str(nr),destination=str(dest),report=str(self.root/'pub.json'),allow_logic=False,history=None,overwrite=True,archive_source=False)
        result=sm.publish(args);self.assertEqual(dest.read_bytes(),self.candidate.read_bytes());self.assertEqual(len(result['backups']),1)

if __name__=='__main__':unittest.main(argv=[sys.argv[0]]+rest,verbosity=2)
