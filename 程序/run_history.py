import json
from datetime import datetime,timezone
from pathlib import Path
def _path(project): return Path(project)/'run_history.json'
def record(project,event_type,stage=None,attempt=1,status='',message='',error_type=None):
 p=_path(project); items=[]
 if p.exists():
  try: items=json.loads(p.read_text(encoding='utf-8'))
  except Exception: items=[]
 items.append({'timestamp':datetime.now(timezone.utc).isoformat(),'event_type':event_type,'stage':stage,'attempt':attempt,'status':status,'message':message,'error_type':error_type}); p.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
 return items[-1]
def load(project):
 try: return json.loads(_path(project).read_text(encoding='utf-8')) if _path(project).exists() else []
 except Exception: return []
