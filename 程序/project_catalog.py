from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass

STAGE_NAMES={0:'项目初始化',1:'剧本解析',2:'项目规则建立',3:'资产库规划',4:'资产生成提示词',5:'分镜设计',6:'Seedance 2.0适配',7:'Seedance 2.5适配',8:'即梦2.0适配',9:'即梦2.5适配',10:'连续性审核',11:'历史真实性审核',12:'AI生成风险审核'}
@dataclass
class ProjectSummary:
    path:Path; data:dict; workflow:dict; error:str|None=None
    @property
    def name(self): return self.data.get('project_name') or self.path.name
    @property
    def statuses(self): return {int(k):v.get('status','pending') for k,v in self.workflow.get('stages',{}).items()}
    @property
    def current_stage(self): return self.workflow.get('current_stage',0)
    @property
    def scope(self): return self.data.get('run_scope') or self.data.get('metadata',{}).get('run_scope') or 'stage01_to_stage12'
    @property
    def scope_numbers(self):
        import re
        m=re.search(r'(\d+).*?(\d+)',self.scope); return list(range(int(m.group(1)),int(m.group(2))+1)) if m else list(range(1,13))
    @property
    def progress(self):
        nums=self.scope_numbers; done=sum(self.statuses.get(n)=='completed' for n in nums); return done,len(nums),round(done*100/len(nums)) if nums else 0
    @property
    def state(self):
        vals=list(self.statuses.values())
        if self.error or any(x=='failed' for x in vals): return '失败'
        if vals and all(self.statuses.get(n)=='completed' for n in self.scope_numbers): return '已完成'
        if any(x=='running' for x in vals): return '运行中'
        return '部分完成' if any(x=='completed' for x in vals) else '未开始'
def load_project(path):
    try: return ProjectSummary(path,json.loads((path/'project.json').read_text(encoding='utf-8')),json.loads((path/'workflow_state.json').read_text(encoding='utf-8')))
    except Exception as e: return ProjectSummary(path,{}, {}, f'项目数据异常：{e}')
def scan_projects(root): return sorted([load_project(p) for p in root.iterdir() if p.is_dir() and p.name!='.gitkeep'],key=lambda x:x.path.stat().st_mtime,reverse=True)
