"""创建项目目录、配置和初始化文件。"""

import shutil
from datetime import datetime, timezone
from pathlib import Path

from asset_manager import initialize_assets
from config import PROJECTS_DIR
from file_utils import ensure_directory, json_write, safe_project_name, write_utf8
from workflow_manager import initialize_workflow_files


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def choose_project_directory(base_name: str, projects_dir: Path, input_func=input, print_func=print) -> Path | None:
    """同名时让用户取消或创建 _v02、_v03 等新版本。"""
    target = projects_dir / base_name
    if not target.exists():
        return target
    print_func(f"项目“{base_name}”已经存在。")
    print_func("1. 取消")
    print_func("2. 创建新版本")
    choice = input_func("请输入数字：").strip()
    if choice == "1":
        return None
    if choice != "2":
        raise ValueError("请输入 1 或 2。")
    version = 2
    while True:
        candidate = projects_dir / f"{base_name}_v{version:02d}"
        if not candidate.exists():
            return candidate
        version += 1


def create_project(source_file: Path, mode: str = "confirm", projects_dir: Path = PROJECTS_DIR, input_func=input, print_func=print) -> Path | None:
    project_name = safe_project_name(source_file.stem)
    ensure_directory(projects_dir)
    project_dir = choose_project_directory(project_name, projects_dir, input_func, print_func)
    if project_dir is None:
        return None
    ensure_directory(project_dir)

    project_id = project_dir.name
    original_target = project_dir / f"00_原始剧本{source_file.suffix.lower()}"
    shutil.copy2(source_file, original_target)
    created_at = utc_now()
    project_data = {
        "schema_version": "1.0",
        "project_id": project_id,
        "project_name": project_name,
        "original_script_path": str(source_file.resolve()),
        "copied_script_path": str(original_target),
        "created_at": created_at,
        "mode": mode,
        "current_stage": 0,
        "project_status": "initialized",
    }
    json_write(project_dir / "project.json", project_data)
    write_utf8(
        project_dir / "00_项目说明.md",
        f"# 项目说明\n\n项目：{project_name}\n\n项目状态：已初始化，等待 AI 处理\n\n运行模式：{mode}\n\n创建时间：{created_at}\n\n第一版程序只建立本地工作流骨架，不生成真实 AI 内容。\n",
    )
    initialize_assets(project_dir, project_id)
    initialize_workflow_files(project_dir, project_name)
    return project_dir
