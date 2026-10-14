"""创建工作流状态和 01—12 阶段占位输出。"""

from datetime import datetime, timezone
from pathlib import Path

from config import PLACEHOLDER_FILES, WORKFLOW_STAGES
from file_utils import json_write, write_utf8


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_workflow_state() -> dict:
    stages = {}
    for number, name in WORKFLOW_STAGES:
        stages[str(number)] = {
            "name": name,
            "status": "completed" if number == 0 else "pending",
            "updated_at": now_iso(),
            "message": "项目已初始化" if number == 0 else "等待前置阶段完成",
        }
    return {
        "schema_version": "1.0",
        "allowed_statuses": ["pending", "processing", "completed", "failed", "waiting_confirmation"],
        "current_stage": 0,
        "project_status": "initialized",
        "updated_at": now_iso(),
        "stages": stages,
    }


def placeholder_content(project_name: str, filename: str, title: str, rule_files: str, template_file: str, dependency: str) -> str:
    stage = filename[:2]
    return (
        f"# {title}\n\n"
        "状态：等待 AI 处理\n\n"
        f"项目：{project_name}\n\n"
        f"阶段：{stage}\n\n"
        "所需规则：\n"
        f"- {rule_files}\n\n"
        "所需模板：\n"
        f"- {template_file}\n\n"
        "上一阶段依赖：\n"
        f"- {dependency}\n\n"
        "说明：第一版程序只建立工作流文件骨架，不生成真实 AI 内容。\n"
    )


def initialize_workflow_files(project_dir: Path, project_name: str) -> None:
    for filename, title, rules, template, dependency in PLACEHOLDER_FILES:
        write_utf8(project_dir / filename, placeholder_content(project_name, filename, title, rules, template, dependency))
    state_path = project_dir / "workflow_state.json"
    json_write(state_path, new_workflow_state())
