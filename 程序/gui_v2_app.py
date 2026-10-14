import tkinter as tk
from tkinter import ttk,messagebox
from pathlib import Path
from project_catalog import scan_projects,STAGE_NAMES
from run_history import load
from gui_error_mapper import explain
class App(tk.Tk):
 def __init__(self,root):
  super().__init__(); self.rootdir=root; self.title('AI影视助手 GUI V2'); self.geometry('1280x760'); self.ps=scan_projects(root/'projects'); self.filtered=self.ps; self.selected=None
  top=ttk.Frame(self); top.pack(fill='x',padx=10,pady=8); self.query=tk.StringVar(); ttk.Entry(top,textvariable=self.query,width=25).pack(side='left'); self.query.trace_add('write',lambda *_:self.refresh()); self.filter=tk.StringVar(value='全部'); ttk.Combobox(top,textvariable=self.filter,values=['全部','进行中','失败','已完成'],state='readonly',width=10).pack(side='left',padx=5); self.filter.trace_add('write',lambda *_:self.refresh()); ttk.Button(top,text='刷新',command=self.refresh).pack(side='left')
  body=ttk.Frame(self); body.pack(fill='both',expand=True,padx=10); left=ttk.Frame(body,width=300); left.pack(side='left',fill='y'); ttk.Label(left,text='最近项目（5）').pack(anchor='w'); self.list=tk.Listbox(left,width=38); self.list.pack(fill='both',expand=True); self.list.bind('<<ListboxSelect>>',self.select); mid=ttk.Frame(body); mid.pack(side='left',fill='both',expand=True,padx=10); self.detail=tk.Text(mid,height=12,state='disabled'); self.detail.pack(fill='x'); self.history=tk.Listbox(mid,height=8); self.history.pack(fill='x',pady=5); btn=ttk.Frame(mid); btn.pack(fill='x'); self.startbtn=ttk.Button(btn,text='开始/继续 Mock',command=self.start_mock); self.startbtn.pack(side='left'); ttk.Button(btn,text='查看技术详情',command=self.tech).pack(side='left',padx=5); ttk.Button(btn,text='查看全部历史',command=self.show_history).pack(side='left'); right=ttk.Frame(body,width=360); right.pack(side='right',fill='both'); self.stage=ttk.Treeview(right,columns=('status',),show='tree headings'); self.stage.heading('#0',text='Stage'); self.stage.heading('status',text='状态'); self.stage.pack(fill='both',expand=True); self.dynamic=tk.StringVar(value='运行动态：空闲'); ttk.Label(self,textvariable=self.dynamic).pack(anchor='w',padx=10,pady=6); self.refresh()
 def refresh(self):
  q=self.query.get().lower(); f=self.filter.get(); self.filtered=[p for p in self.ps if (not q or q in p.name.lower() or q in str(p.data.get('source_script_name','')).lower()) and (f=='全部' or (f=='失败' and p.state=='失败') or (f=='已完成' and p.state=='已完成') or (f=='进行中' and p.state in ('运行中','部分完成')))]; self.list.delete(0,'end'); [self.list.insert('end',p.name+('｜异常' if p.error else '')) for p in self.filtered]
 def select(self,event=None):
  if not self.list.curselection(): return
  self.selected=self.filtered[self.list.curselection()[0]]; p=self.selected; self.detail.configure(state='normal'); self.detail.delete('1.0','end'); self.detail.insert('end',f'项目：{p.name}\n状态：{p.state}\n路径：{p.path}\n进度：{p.progress[0]}/{p.progress[1]} ({p.progress[2]}%)\n范围：{p.scope}'); self.detail.configure(state='disabled'); self.stage.delete(*self.stage.get_children()); [self.stage.insert('','end',text=f'Stage {n:02d}｜{STAGE_NAMES[n]}',values=(p.statuses.get(n,'pending'),)) for n in range(1,13)]; self.history.delete(0,'end'); [self.history.insert('end',f"{x.get('timestamp','')[:16]} Stage {x.get('stage','-')} {x.get('status','')}") for x in load(p.path)[-10:]]
 def start_mock(self): self.dynamic.set('运行动态：离线 Mock 控制器入口已连接；真实 AI 在测试模式下禁止调用。')
 def tech(self):
  if not self.selected: return
  w=tk.Toplevel(self); w.title('技术详情'); t=tk.Text(w,width=90,height=20); t.pack(fill='both',expand=True); t.insert('end',f'项目路径：{self.selected.path}\n状态：{self.selected.state}\n错误类型：无\nrequested_model：无\nactual_model：无\n')
 def show_history(self):
  if self.selected: messagebox.showinfo('运行历史','\n'.join(f'{x.get("timestamp","")[:19]} Stage {x.get("stage","-")} {x.get("status","")}' for x in load(self.selected.path)) or '暂无运行历史')
if __name__=='__main__': App(Path(__file__).resolve().parent.parent).mainloop()
