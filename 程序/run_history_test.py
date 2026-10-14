import tempfile
from run_history import record,load
def main():
 with tempfile.TemporaryDirectory() as d:
  record(d,'stage_started',3,1,'running','Stage 03 started'); record(d,'stage_failed',3,1,'failed','bad','validator_error'); assert len(load(d))==2
 print('run_history_test：全部通过')
if __name__=='__main__': main()
