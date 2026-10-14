import tkinter as tk
from pathlib import Path
from project_catalog import scan_projects
def main():
 root=tk.Tk(); root.withdraw(); ps=scan_projects(Path(__file__).resolve().parent.parent/'projects'); root.destroy(); assert isinstance(ps,list); print('gui_v2_self_test：全部通过')
if __name__=='__main__': main()
