import json, sys, tempfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from project_manager import create_project
from mock.script_derived_pipeline import run

def main():
    root=Path(__file__).resolve().parent.parent; src=root/'输入剧本'/'GUI测试剧本.txt'
    if not src.is_file(): src=root/'tests'/'fixtures'/'GUI测试剧本.txt'
    with tempfile.TemporaryDirectory(prefix='script_derived_') as t:
        pr=create_project(src, projects_dir=Path(t)/'projects', input_func=lambda _: '2')
        data=json.loads((pr/'project.json').read_text(encoding='utf-8')); data['project_id']='script-derived-regression'; data['project_name']='script-derived-regression'; (pr/'project.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); run(pr)
        a=json.loads((pr/'assets.json').read_text(encoding='utf-8')); names=' '.join(x['canonical_name'] for g in a['assets'].values() for x in g.values()); assert all(x in names for x in ('林夏','陈默','旧书店门口','红色折叠伞')); assert not any(x in names for x in ('林川','赵伯','山间驿站','步枪','搜山敌军','特殊火障'))
        shots=json.loads((pr/'storyboard.json').read_text(encoding='utf-8'))['scenes'][0]['shots']; ids={x['shot_id'] for x in shots}
        for n in ('seedance20_prompts.json','seedance25_prompts.json','jimeng20_prompts.json','jimeng25_prompts.json'): assert set(json.loads((pr/n).read_text(encoding='utf-8'))['shots'])==ids
        assert json.loads((pr/'project_final_status.json').read_text(encoding='utf-8'))['stage_completion']['12']=='completed'
    print('script_derived_mock_regression_test：全部通过')
if __name__=='__main__': main()
