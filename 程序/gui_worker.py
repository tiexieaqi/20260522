import threading
from queue import Queue
class ProjectWorker:
 def __init__(self, stages, runner): self.stages=stages; self.runner=runner; self.events=Queue(); self.stop_after_current_stage=False; self._thread=None
 def start(self):
  if self._thread and self._thread.is_alive(): self.events.put(('error',{'error_type':'project_already_running'})); return False
  def work():
   for stage in self.stages:
    self.events.put(('stage_started',stage));
    try: self.runner(stage); self.events.put(('stage_completed',stage))
    except Exception as e: self.events.put(('stage_failed',(stage,e))); break
    if self.stop_after_current_stage: self.events.put(('stopped',stage)); break
   else: self.events.put(('scope_completed',None))
  self._thread=threading.Thread(target=work,daemon=True); self._thread.start(); return True
