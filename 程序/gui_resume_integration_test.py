from project_catalog import ProjectSummary
from resume_controller import next_stage
def main():
 p=ProjectSummary(None,{'run_scope':'stage01_to_stage06'},{'stages':{**{str(i):{'status':'completed'} for i in (1,2)},'3':{'status':'failed'},'4':{'status':'pending'},'5':{'status':'pending'},'6':{'status':'pending'}}}); assert next_stage(p)=={'action':'retry_failed','stage':3}; p.workflow['stages']['3']['status']='completed'; assert next_stage(p)['stage']==4; print('gui_resume_integration_test：全部通过')
if __name__=='__main__': main()
