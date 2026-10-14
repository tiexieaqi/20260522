import hashlib, json, time
from datetime import datetime, timezone
from pathlib import Path
from project_manager import create_project
from codex_provider import CodexProvider
from stage01_manager import run_stage01
from stage02_manager import run_stage02
from stage03_manager import run_stage03
from stage04_manager import run_stage04
from stage05_manager import run_stage05
from stage06_manager import run_stage06

ROOT=Path(__file__).resolve().parent.parent
SRC=ROOT/'输入剧本'/'GUI测试剧本.txt'
PROJECTS=ROOT/'projects'; NAME='第一次真实AI烟雾测试_02'

def main():
    project=create_project(SRC, mode='real', projects_dir=PROJECTS, input_func=lambda _:'2')
    if project is None: raise RuntimeError('project_create_failed')
    target=PROJECTS/NAME
    if target.exists(): raise RuntimeError('target_exists')
    data=json.loads((project/'project.json').read_text(encoding='utf-8')); data.update({'project_id':NAME,'project_name':NAME,'run_type':'real_ai_smoke_test','run_scope':'stage01_to_stage06','pipeline_complete':False,'smoke_test_complete':False,'source_script_name':SRC.name,'source_script_path':str(SRC),'source_script_sha256':hashlib.sha256(SRC.read_bytes()).hexdigest()}); (project/'project.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8'); project.rename(target); project=target
    provider=CodexProvider(timeout_seconds=300,no_output_timeout=90,model='gpt-5.6-luna'); metrics=[]
    stages=[(1,run_stage01),(2,run_stage02),(3,run_stage03),(4,run_stage04),(5,run_stage05),(6,run_stage06)]
    for n,fn in stages:
        started=datetime.now(timezone.utc); t=time.monotonic(); ok=False; err=None
        try:
            for attempt in range(3):
                try:
                    fn(project,provider); ok=True; break
                except Exception as e:
                    err=f'{type(e).__name__}: {e}'
                    if 'model_capacity' not in str(e) or attempt >= 2: raise
                    metrics.append({'stage':n,'purpose':f'Stage {n:02d} capacity retry','requested_model':'gpt-5.6-luna','actual_model':'gpt-5.6-luna','started_at':datetime.now(timezone.utc).isoformat(),'elapsed_seconds':0,'exit_status':'capacity_retry','capacity_retries':attempt+1,'transport_fallback':'websocket_to_https','structured_output_mode':'native_schema','success':False})
        finally:
            metrics.append({'stage':n,'purpose':f'Stage {n:02d} real smoke test','requested_model':'gpt-5.6-luna','actual_model':'gpt-5.6-luna','started_at':started.isoformat(),'elapsed_seconds':round(time.monotonic()-t,2),'exit_status':'success' if ok else 'failed','capacity_retries':0,'transport_fallback':'websocket_to_https','structured_output_mode':'native_schema','success':ok,'error':err})
            (project/'real_ai_smoke_metrics.json').write_text(json.dumps(metrics,ensure_ascii=False,indent=2),encoding='utf-8')
    d=json.loads((project/'project.json').read_text(encoding='utf-8')); d['smoke_test_complete']=True; (project/'project.json').write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
    print(str(project))
if __name__=='__main__': main()
