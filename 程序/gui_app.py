"""AI影视助手桌面 GUI V1（Tkinter）。只负责界面和调度，底层 Stage 仍由现有 Manager 执行。"""
from __future__ import annotations

import json
import os
import queue
import subprocess
import shutil
import sys
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
from config import PROJECTS_DIR
from environment_checker import inspect_environment
from file_utils import safe_project_name
from file_utils import json_write
from project_manager import create_project
from stage01_manager import run_stage01
from stage02_manager import run_stage02
from stage03_manager import run_stage03
from stage04_manager import run_stage04
from stage05_manager import run_stage05
from stage06_manager import run_stage06
from stage07_manager import run_stage07
from stage08_manager import run_stage08
from stage09_manager import run_stage09
from stage10_manager import run_stage10
from stage11_manager import run_stage11
from stage12_manager import run_stage12
from codex_provider import CodexProvider


STAGES = [(0, "项目初始化"), (1, "剧本解析"), (2, "项目规则"), (3, "资产库"), (4, "资产提示词"), (5, "标准分镜"), (6, "Seedance 2.0"), (7, "Seedance 2.5"), (8, "即梦 2.0"), (9, "即梦 2.5"), (10, "连续性审核"), (11, "历史真实性审核"), (12, "AI生成风险终审")]
OUTPUTS = {"资产库": "03_资产库.md", "资产提示词": "04_资产生成提示词.md", "标准分镜": "05_标准分镜.md", "Seedance 2.0": "06_Seedance2.0提示词.md", "Seedance 2.5": "07_Seedance2.5提示词.md", "即梦 2.0": "08_即梦2.0提示词.md", "即梦 2.5": "09_即梦2.5提示词.md", "连续性审核": "10_连续性审核报告.md", "历史真实性审核": "11_历史真实性审核报告.md", "AI生成风险终审": "12_AI生成风险报告.md"}
MODEL_STAGES = {"Seedance 2.0": 6, "Seedance 2.5": 7, "即梦 2.0": 8, "即梦 2.5": 9}


def friendly_error(error: Exception) -> str:
    text = str(error)
    low = text.lower()
    if any(x in low for x in ("403", "dns", "connect", "timeout", "codex")):
        return "当前无法连接 AI 服务。项目文件没有损坏，稍后可点击‘重试当前阶段’。"
    return text or "发生了未知错误。"


class PipelineRunner:
    def __init__(self, project: Path, offline: bool, mode: str, selected: set[str], callback):
        self.project, self.offline, self.mode, self.selected, self.callback = project, offline, mode, selected, callback
        self.stop_requested = False
        self.continue_event = threading.Event()

    def emit(self, kind, payload): self.callback((kind, payload))

    def run(self):
        try:
            if self.offline:
                self._run_mock()
            else:
                self._run_real()
            self.emit("done", self.project)
        except Exception as error:
            self.emit("error", error)

    def _provider(self):
        return CodexProvider(timeout_seconds=120)

    def _run_real(self):
        p = self.project; provider = self._provider()
        funcs = [(1, run_stage01), (2, run_stage02), (3, run_stage03), (4, run_stage04), (5, run_stage05)]
        for number, func in funcs:
            if self._should_run(number): self._stage(number, func, provider)
        for label, number, func in (("Seedance 2.0", 6, run_stage06), ("Seedance 2.5", 7, run_stage07), ("即梦 2.0", 8, run_stage08), ("即梦 2.5", 9, run_stage09)):
            if label in self.selected and self._should_run(number): self._stage(number, func, provider)
            else: self._skip_model(number, label); self.emit("skip", number)
        if self._should_run(10): self._stage(10, run_stage10, None)
        if self._should_run(11): self._stage(11, run_stage11, None)
        if self._should_run(12): self._stage(12, run_stage12, None)

    def _run_mock(self):
        # 离线模式复用已有离线测试供应商，绝不伪装成真实 AI。
        from offline_test_stage05 import StoryboardProvider, prepare
        from offline_test_stage04 import AssetProvider, PromptProvider, TextProvider
        from stage01_manager import REQUIRED_HEADINGS as H1
        from stage02_manager import REQUIRED_HEADINGS as H2
        p = self.project
        if self._should_run(1): self._stage(1, lambda _p: run_stage01(p, TextProvider(H1)), None)
        if self._should_run(2): self._stage(2, lambda _p: run_stage02(p, TextProvider(H2)), None)
        if self._should_run(3): self._stage(3, lambda _p: run_stage03(p, AssetProvider()), None)
        if self._should_run(4): self._stage(4, lambda _p: run_stage04(p, PromptProvider()), None)
        if self._should_run(5): self._stage(5, lambda _p: run_stage05(p, StoryboardProvider()), None)
        import offline_test_stage06 as f6, offline_test_stage07 as f7, offline_test_stage08 as f8, offline_test_stage09 as f9
        providers = [("Seedance 2.0", 6, f6, run_stage06), ("Seedance 2.5", 7, f7, run_stage07), ("即梦 2.0", 8, f8, run_stage08), ("即梦 2.5", 9, f9, run_stage09)]
        for label, number, fixture, func in providers:
            if label in self.selected and self._should_run(number):
                fixture.CURRENT_PROJECT = p; self._stage(number, lambda _p, fn=func, fx=fixture: fn(p, fx.Provider()), None)
            else: self._skip_model(number, label); self.emit("skip", number)
        if self._should_run(10): self._stage(10, lambda _p: run_stage10(p), None)
        if self._should_run(11): self._stage(11, lambda _p: run_stage11(p), None)
        if self._should_run(12): self._stage(12, lambda _p: run_stage12(p), None)

    def _should_run(self, number):
        try:
            state = json.loads((self.project / "workflow_state.json").read_text(encoding="utf-8"))
            return state.get("stages", {}).get(str(number), {}).get("status") != "completed"
        except Exception:
            return True

    def _stage(self, number, func, provider):
        self.emit("start", number)
        func(self.project, provider) if provider is not None else func(self.project)
        self.emit("stage", number)
        if self.mode == "confirm" and number in {1, 3, 5, 9, 12}:
            self.continue_event.clear(); self.emit("confirm", number); self.continue_event.wait()

    def _skip_model(self, number, label):
        """为审核阶段建立明确的 skipped 模型登记，绝不伪造模型生成结果。"""
        names = {6: "seedance20_prompts.json", 7: "seedance25_prompts.json", 8: "jimeng20_prompts.json", 9: "jimeng25_prompts.json"}
        storyboard = json.loads((self.project / "storyboard.json").read_text(encoding="utf-8"))
        shots = {}
        for scene in storyboard.get("scenes", []):
            for shot in scene.get("shots", []):
                assets = shot.get("assets", {}); refs = list(assets.get("characters", [])) + ([assets["location"]] if assets.get("location") else [])
                for key in ("props", "weapons", "groups", "fx"): refs.extend(assets.get(key, []))
                shots[shot["shot_id"]] = {"source_shot_id": shot["shot_id"], "duration_seconds": shot.get("duration_seconds", 0), "asset_refs": refs, "prompt": f"[{label} 未选择，当前阶段跳过]", "timeline": [], "dialogue": shot.get("dialogue", []), "start_state": shot.get("start_state", {}), "end_state": shot.get("end_state", {}), "forbidden": shot.get("forbidden", []), "risk": {"level": "info", "reasons": ["用户未选择该模型"]}}
        json_write(self.project / names[number], {"schema_version": "1.0", "model": label, "project_id": json.loads((self.project / "project.json").read_text(encoding="utf-8"))["project_id"], "project_name": self.project.name, "skipped": True, "shots": shots})


class App(tk.Tk):
    def __init__(self):
        super().__init__(); self.title("AI影视助手"); self.geometry("1100x720"); self.minsize(900, 600)
        self.script = None; self.project = None; self.worker = None; self.events = queue.Queue(); self.stage_rows = {}
        self.mode = tk.StringVar(value="auto"); self.ai_mode = tk.StringVar(value="real"); self.offline_var = tk.BooleanVar(value=False); self.project_name = tk.StringVar(); self.detail_var = tk.BooleanVar(value=False)
        self.models = {name: tk.BooleanVar(value=True) for name in MODEL_STAGES}
        self._build(); self.after(100, self._poll)

    def _build(self):
        header = ttk.Frame(self, padding=12); header.pack(fill="x"); ttk.Label(header, text="AI影视助手", font=("Microsoft YaHei", 22, "bold")).pack(side="left"); ttk.Label(header, text="本地制作包工作台", foreground="#666").pack(side="left", padx=18)
        self.stack = ttk.Frame(self, padding=12); self.stack.pack(fill="both", expand=True); self._home()

    def clear(self):
        for child in self.stack.winfo_children(): child.destroy()

    def _home(self):
        self.clear(); left = ttk.Frame(self.stack); left.pack(side="left", fill="both", expand=True, padx=(0, 10)); right = ttk.Frame(self.stack, width=330); right.pack(side="right", fill="y")
        ttk.Label(left, text="1｜剧本", font=("Microsoft YaHei", 15, "bold")).pack(anchor="w")
        box = ttk.LabelFrame(left, text="选择或导入剧本", padding=20); box.pack(fill="x", pady=10); ttk.Button(box, text="选择 .txt / .md 剧本", command=self.choose_script).pack(anchor="w")
        self.script_label = ttk.Label(box, text="尚未选择剧本", foreground="#666"); self.script_label.pack(anchor="w", pady=10)
        ttk.Label(left, text="项目名称").pack(anchor="w"); ttk.Entry(left, textvariable=self.project_name, width=55).pack(anchor="w", pady=5)
        options = ttk.LabelFrame(left, text="制作模式", padding=10); options.pack(fill="x", pady=15); ttk.Radiobutton(options, text="全自动模式（推荐）", variable=self.mode, value="auto").pack(anchor="w"); ttk.Radiobutton(options, text="分阶段确认模式", variable=self.mode, value="confirm").pack(anchor="w")
        models = ttk.LabelFrame(left, text="模型输出（基础阶段始终执行）", padding=10); models.pack(fill="x")
        for name, var in self.models.items(): ttk.Checkbutton(models, text=name, variable=var).pack(side="left", padx=8)
        self.jimeng_mode = tk.StringVar(value="auto"); ttk.Label(models, text="即梦2.5：").pack(side="left", padx=(15, 2)); ttk.Combobox(models, textvariable=self.jimeng_mode, values=["自动推荐", "稳定版", "电影增强版"], state="readonly", width=10).pack(side="left")
        adv = ttk.LabelFrame(right, text="高级设置", padding=10); adv.pack(fill="x"); ttk.Radiobutton(adv, text="真实 AI（Codex CLI）", variable=self.ai_mode, value="real").pack(anchor="w"); ttk.Radiobutton(adv, text="离线测试（Mock）", variable=self.ai_mode, value="offline").pack(anchor="w"); ttk.Label(adv, text="离线测试只用于验证流程，不生成真实 AI 内容。", wraplength=260, foreground="#996600").pack(anchor="w", pady=8)
        ttk.Button(right, text="开始制作", command=self.start, style="Accent.TButton").pack(fill="x", pady=18, ipady=8); ttk.Button(right, text="打开已有项目", command=self.open_project).pack(fill="x"); ttk.Label(right, text="最近项目", font=("Microsoft YaHei", 12, "bold")).pack(anchor="w", pady=(25, 5)); self.recent = tk.Listbox(right, height=7); self.recent.pack(fill="x"); self.load_recent()

    def choose_script(self):
        path = filedialog.askopenfilename(title="选择剧本", filetypes=[("剧本文件", "*.txt *.md"), ("所有文件", "*.*")])
        if path:
            self.script = Path(path); self.project_name.set(safe_project_name(self.script.stem)); self.script_label.configure(text=f"{self.script.name}\n{self.script}\n大小：{self.script.stat().st_size} 字节", foreground="#222")

    def start(self):
        if not self.script or not self.script.is_file(): return messagebox.showwarning("需要剧本", "请先选择 .txt 或 .md 剧本。")
        name = safe_project_name(self.project_name.get().strip() or self.script.stem)
        if not name: return messagebox.showwarning("项目名称", "项目名称不能为空。")
        if self.ai_mode.get() == "real" and not CodexProvider.is_available(): return messagebox.showerror("AI 服务不可用", "找不到 Codex CLI。请先完成 Codex CLI 登录。")
        try:
            self.project = create_project(self.script, mode=self.mode.get(), projects_dir=PROJECTS_DIR, input_func=lambda _: "2", print_func=lambda *_: None)
            if self.project is None: return
            if name != self.project.name:
                renamed = PROJECTS_DIR / name
                if renamed.exists():
                    renamed = PROJECTS_DIR / f"{name}_v02"
                self.project = Path(shutil.move(str(self.project), str(renamed)))
                config_path = self.project / "project.json"
                config = json.loads(config_path.read_text(encoding="utf-8")); config["project_id"] = self.project.name; config["project_name"] = name; config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self.show_progress(); selected = {n for n, v in self.models.items() if v.get()}; self.worker = PipelineRunner(self.project, self.ai_mode.get() == "offline", self.mode.get(), selected, self.events.put); threading.Thread(target=self.worker.run, daemon=True).start()
        except Exception as error: messagebox.showerror("项目初始化失败", friendly_error(error))

    def show_progress(self):
        self.clear(); ttk.Label(self.stack, text="项目执行进度", font=("Microsoft YaHei", 17, "bold")).pack(anchor="w"); self.progress = ttk.Progressbar(self.stack, maximum=12); self.progress.pack(fill="x", pady=12); self.status = ttk.Label(self.stack, text="准备开始"); self.status.pack(anchor="w"); frame = ttk.Frame(self.stack); frame.pack(fill="both", expand=True, pady=10); self.tree = ttk.Treeview(frame, columns=("state", "message"), show="headings"); self.tree.heading("state", text="状态"); self.tree.heading("message", text="说明"); self.tree.column("state", width=100); self.tree.pack(side="left", fill="both", expand=True); self.log = tk.Text(frame, height=8, state="disabled"); self.log.pack(side="right", fill="both", expand=True, padx=10)
        for n, label in STAGES[1:]: self.stage_rows[n] = self.tree.insert("", "end", values=("等待", f"Stage {n:02d}｜{label}"))

    def _poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait(); self.handle_event(kind, payload)
        except queue.Empty: pass
        self.after(100, self._poll)

    def handle_event(self, kind, payload):
        if kind == "start": self.tree.set(self.stage_rows[payload], "state", "运行中"); self.status.configure(text=f"正在处理 Stage {payload:02d}…")
        elif kind == "stage": self.tree.set(self.stage_rows[payload], "state", "完成"); self.progress["value"] = payload; self.status.configure(text=f"Stage {payload:02d} 已完成")
        elif kind == "skip": self.tree.set(self.stage_rows[payload], "state", "跳过"); self.tree.set(self.stage_rows[payload], "message", "用户未选择此模型")
        elif kind == "confirm": self.status.configure(text=f"Stage {payload:02d} 已完成，请确认后继续。"); self.continue_button = ttk.Button(self.stack, text="继续", command=self.continue_pipeline); self.continue_button.pack(pady=8)
        elif kind == "error": self.tree.set(self.stage_rows.get(self._current_stage(), ""), "state", "失败") if self.stage_rows else None; self.status.configure(text=f"处理失败：{friendly_error(payload)}"); messagebox.showerror("制作失败", f"{friendly_error(payload)}\n\n项目文件没有损坏，可返回项目后重试失败阶段。")
        elif kind == "done": self.show_result(payload)

    def _current_stage(self):
        try: return json.loads((self.project / "workflow_state.json").read_text(encoding="utf-8")).get("current_stage", 1)
        except Exception: return 1

    def continue_pipeline(self):
        if hasattr(self, "continue_button"):
            self.continue_button.destroy()
        if self.worker:
            self.worker.continue_event.set()

    def show_result(self, project):
        self.clear(); ttk.Label(self.stack, text="AI影视制作包生成完成", font=("Microsoft YaHei", 18, "bold")).pack(anchor="w"); final = json.loads((project / "project_final_status.json").read_text(encoding="utf-8")); ttk.Label(self.stack, text=f"总体状态：{ {'ready':'可以制作','review_required':'建议检查','blocked':'存在阻断问题'}.get(final.get('final_pipeline_status'), '需要确认') }", font=("Microsoft YaHei", 13)).pack(anchor="w", pady=8); buttons = ttk.Frame(self.stack); buttons.pack(fill="x", pady=8)
        for label, filename in OUTPUTS.items(): ttk.Button(buttons, text=f"查看{label}", command=lambda f=filename, l=label: self.view_file(project, f, l)).pack(side="left", padx=3, pady=3)
        ttk.Button(self.stack, text="打开项目文件夹", command=lambda: os.startfile(project) if hasattr(os, "startfile") else subprocess.Popen(["xdg-open", str(project)])).pack(anchor="w", pady=8); ttk.Button(self.stack, text="返回首页", command=self._home).pack(anchor="w")

    def view_file(self, project, filename, title):
        path = project / filename
        if not path.is_file(): return messagebox.showinfo(title, "该文件尚未生成。")
        win = tk.Toplevel(self); win.title(title); win.geometry("900x650"); text = tk.Text(win, wrap="word"); text.pack(fill="both", expand=True); text.insert("1.0", path.read_text(encoding="utf-8", errors="replace")); text.configure(state="disabled")

    def open_project(self):
        path = filedialog.askdirectory(title="选择项目文件夹", initialdir=str(PROJECTS_DIR));
        if path:
            self.project = Path(path)
            if (self.project / "project_final_status.json").is_file():
                self.show_result(self.project)
            else:
                self.show_progress(); self.resume_button = ttk.Button(self.stack, text="继续未完成项目", command=self.resume_project); self.resume_button.pack(pady=10)

    def resume_project(self):
        if hasattr(self, "resume_button"): self.resume_button.destroy()
        environment = inspect_environment()
        if not environment.restricted_network and not CodexProvider.is_available():
            messagebox.showerror("AI 服务不可用", "找不到 Codex CLI，无法继续真实 AI 项目。"); return
        self.worker = PipelineRunner(self.project, self.ai_mode.get() == "offline", "auto", set(MODEL_STAGES), self.events.put); threading.Thread(target=self.worker.run, daemon=True).start()

    def load_recent(self):
        PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
        for p in sorted([x for x in PROJECTS_DIR.iterdir() if x.is_dir()], key=lambda x: x.stat().st_mtime, reverse=True)[:8]: self.recent.insert("end", p.name)


def main():
    app = App();
    try: ttk.Style().theme_use("vista")
    except tk.TclError: pass
    app.mainloop()


if __name__ == "__main__": main()
