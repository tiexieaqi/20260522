"""Stage 01 真实测试入口：仅在非受限环境调用 Codex CLI。"""

import json
import sys
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = PROGRAM_DIR.parent
sys.path.insert(0, str(PROGRAM_DIR))

from codex_provider import CodexProvider
from environment_checker import inspect_environment
from main import list_script_files
from project_manager import create_project
from stage01_manager import run_stage01


def main() -> int:
    environment = inspect_environment()
    print(environment.reason)
    if environment.restricted_network:
        print("检测到受限开发环境，live_test 已跳过真实联网调用。")
        return 2
    if not environment.codex_available:
        print("live_test 无法执行：未找到 codex CLI。")
        return 2
    if not environment.logged_in:
        print("live_test 无法执行：Codex CLI 当前未登录。")
        return 2
    files = list_script_files(PROJECT_ROOT / "输入剧本")
    if not files:
        print("输入剧本文件夹中没有可测试的 .txt 或 .md 文件。")
        return 2
    project = create_project(files[0], mode="live_test", projects_dir=PROJECT_ROOT / "projects", input_func=lambda _: "2")
    if project is None:
        print("无法创建 live_test 项目。")
        return 1
    try:
        run_stage01(project, CodexProvider())
    except Exception as error:
        print(f"Stage 01 真实调用失败：{error}")
        return 1
    report = project / "01_剧本解析报告.md"
    state = json.loads((project / "workflow_state.json").read_text(encoding="utf-8"))
    if not report.read_text(encoding="utf-8").strip():
        print("真实调用返回空报告。")
        return 1
    if state["stages"]["1"]["status"] != "completed":
        print("workflow_state 未进入 completed。")
        return 1
    print(f"live_test 成功：{project}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
