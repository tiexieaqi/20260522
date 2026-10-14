"""GUI V1 的无窗口自动检查；用于无 Windows 图形会话的开发环境。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import gui_app

assert gui_app.STAGES[-1] == (12, "AI生成风险终审")
assert set(gui_app.MODEL_STAGES) == {"Seedance 2.0", "Seedance 2.5", "即梦 2.0", "即梦 2.5"}
assert gui_app.friendly_error(RuntimeError("HTTP 403 DNS connect timeout")) == "当前无法连接 AI 服务。项目文件没有损坏，稍后可点击‘重试当前阶段’。"
assert (Path(__file__).resolve().parent.parent / "启动AI影视助手.bat").is_file()
print("gui_self_test：逻辑检查通过；Tk 窗口和 Windows 双击行为需在 Windows 桌面环境验收。")
