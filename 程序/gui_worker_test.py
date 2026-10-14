import time
from gui_worker import ProjectWorker
def main():
 seen=[]; w=ProjectWorker([1,2],lambda s: seen.append(s)); assert w.start(); time.sleep(.1); kinds=[]
 while not w.events.empty(): kinds.append(w.events.get()[0])
 assert seen==[1,2] and kinds[:2]==['stage_started','stage_completed']; print('gui_worker_test：全部通过')
if __name__=='__main__': main()
