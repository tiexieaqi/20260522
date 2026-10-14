from pathlib import Path
from run_history import record
from gui_worker import ProjectWorker
from resume_controller import next_stage,validate_resume
class OfflineGUIController:
 def __init__(self,project,scope=range(1,7),failure_stage=None): self.project=project; self.scope=list(scope); self.failure_stage=failure_stage; self.lock=False; self.stop_after_current_stage=False; self.attempts={}
 def run(self,from_stage=None,only=False):
  if self.lock: return None,'project_already_running'
  self.lock=True; start=from_stage or next((n for n in self.scope if not self._status(n)=='completed'),self.scope[-1]); stages=[start] if only else [n for n in self.scope if n>=start]
  def runner(n):
   record(self.project,'stage_started',n,self.attempts.get(n,1),'running',f'Stage {n} started')
   if self.failure_stage==n and self.attempts.get(n,0)==0: self.attempts[n]=1; self._set(n,'failed'); record(self.project,'stage_failed',n,1,'failed','offline injected failure','validator_error'); raise RuntimeError('validator_error')
   self._set(n,'completed'); record(self.project,'stage_completed',n,self.attempts.get(n,1),'completed',f'Stage {n} completed')
  return ProjectWorker(stages,runner),None
 def _status(self,n):
  import json; return json.loads((self.project/'workflow_state.json').read_text(encoding='utf-8'))['stages'].get(str(n),{}).get('status','pending')
 def _set(self,n,status):
  import json; p=self.project/'workflow_state.json'; d=json.loads(p.read_text(encoding='utf-8')); d['stages'][str(n)]['status']=status; p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')
