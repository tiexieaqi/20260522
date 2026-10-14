from pathlib import Path
import hashlib
def next_stage(project):
    for n in project.scope_numbers:
        if project.statuses.get(n)=='failed': return {'action':'retry_failed','stage':n}
        if project.statuses.get(n)!='completed': return {'action':'run_next','stage':n}
    return {'action':'scope_complete','stage':None}
def validate_resume(project):
    p=project.data; source=p.get('source_script_path')
    if source and Path(source).is_file() and p.get('source_script_sha256') and hashlib.sha256(Path(source).read_bytes()).hexdigest()!=p['source_script_sha256']: return {'ok':False,'error_type':'source_mismatch'}
    return {'ok':True}
