import tkinter as tk
from pathlib import Path
from gui_v2_app import App
def main():
 root=tk.Tk(); root.withdraw(); app=App(Path(__file__).resolve().parent.parent); app.withdraw(); assert all(callable(getattr(app,n,None)) for n in ('start_mock','continue_mock','retry_stage','resume_failed','stop_after_current','tech','show_history')); root.destroy(); print('gui_v2_button_wiring_test：全部通过')
if __name__=='__main__': main()
