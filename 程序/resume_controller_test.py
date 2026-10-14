from project_catalog import ProjectSummary
from resume_controller import next_stage
def main():
 p=ProjectSummary(None,{'run_scope':'stage01_to_stage12'},{'stages':{'1':{'status':'completed'},'2':{'status':'completed'},'3':{'status':'failed'}}}); assert next_stage(p)['stage']==3
 p=ProjectSummary(None,{'run_scope':'stage01_to_stage06'},{'stages':{str(i):{'status':'completed'} for i in range(1,7)}}); assert next_stage(p)['action']=='scope_complete'
 print('resume_controller_test：全部通过')
if __name__=='__main__': main()
