import tempfile,json,time
from pathlib import Path
from offline_gui_controller import OfflineGUIController
def main():
 with tempfile.TemporaryDirectory() as d:
  p=Path(d); (p/'workflow_state.json').write_text(json.dumps({'stages':{str(i):{'status':'pending'} for i in range(1,7)}}),encoding='utf-8'); c=OfflineGUIController(p,failure_stage=3); w,e=c.run(); assert not e; w.start(); time.sleep(.2); assert json.loads((p/'workflow_state.json').read_text())['stages']['3']['status']=='failed'; c=OfflineGUIController(p); w,_=c.run(from_stage=3); w.start(); time.sleep(.2); assert all(json.loads((p/'workflow_state.json').read_text())['stages'][str(i)]['status']=='completed' for i in range(3,7))
 print('gui_v2_full_integration_test：全部通过')
if __name__=='__main__': main()
