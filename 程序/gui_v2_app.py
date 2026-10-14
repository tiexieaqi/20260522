import tkinter as tk
from tkinter import ttk
from pathlib import Path
from project_catalog import scan_projects,STAGE_NAMES
class App(tk.Tk):
 def __init__(self,root):
  super().__init__(); self.title('AI影视助手 GUI V2'); self.geometry('1200x720'); self.ps=scan_projects(root/'projects'); self.filtered=self.ps
  bar=ttk.Frame(self); bar.pack(fill='x',padx=10,pady=8); self.query=tk.StringVar(); ttk.Entry(bar,textvariable=self.query,width=24).pack(side='left'); self.query.trace_add('write',lambda *_:self.refresh()); self.filter=tk.StringVar(value='全部'); ttk.Combobox(bar,textvariable=self.filter,values=['全部','进行中','失败','已完成'],state='readonly',width=10).pack(side='left',padx=6); self.filter.trace_add('write',lambda *_:self.refresh())
  self.list=tk.Listbox(self,width=38); self.list.pack(side='left',fill='y',padx=10,pady=10); self.detail=tk.Text(self,state='disabled'); self.detail.pack(side='left',fill='both',expand=True,padx=10,pady=10); self.stage=ttk.Treeview(self,columns=('status',),show='tree headings'); self.stage.heading('#0',text='Stage'); self.stage.heading('status',text='状态'); self.stage.pack(side='right',fill='both',expand=True,padx=10,pady=10); self.list.bind('<<ListboxSelect>>',self.select); self.refresh()
 def refresh(self):
  q=self.query.get().lower(); f=self.filter.get(); self.filtered=[p for p in self.ps if (not q or q in p.name.lower() or q in str(p.data.get('source_script_name','')).lower()) and (f=='全部' or (f=='失败' and p.state=='失败') or (f=='已完成' and p.state=='已完成') or (f=='进行中' and p.state in ('运行中','部分完成')))]; self.list.delete(0,'end'); [self.list.insert('end',p.name+('｜项目数据异常' if p.error else '')) for p in self.filtered]
 def select(self,event):
  if not self.list.curselection(): return
  p=self.filtered[self.list.curselection()[0]]; self.detail.configure(state='normal'); self.detail.delete('1.0','end'); self.detail.insert('end',f'项目：{p.name}\n状态：{p.state}\n路径：{p.path}\n进度：{p.progress[0]}/{p.progress[1]} ({p.progress[2]}%)\n运行范围：{p.scope}'); self.detail.configure(state='disabled'); self.stage.delete(*self.stage.get_children()); [self.stage.insert('','end',text=f'Stage {n:02d}｜{STAGE_NAMES[n]}',values=(p.statuses.get(n,'pending'),)) for n in range(1,13)]
if __name__=='__main__': App(Path(__file__).resolve().parent.parent).mainloop()
