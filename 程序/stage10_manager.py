"""Stage 10：只读连续性审核。"""

import json
from pathlib import Path

from continuity_auditor import audit_project, shots_from_storyboard
from continuity_validator import validate_continuity_report
from file_utils import atomic_json_write, read_utf8
from model_stage_base import load_model_stage_context, read_model_sources
from stage_base import StageRunner


RULE_NAMES = ["00_系统总控规则.md", "04_资产库总规则.md", "05_人物资产规则.md", "06_场景资产规则.md", "07_道具资产规则.md", "08_分镜导演规则.md", "14_项目规则隔离规则.md"]
REPORT_NAME = "10_连续性审核报告.md"
JSON_NAME = "continuity_report.json"
MODEL_FILES = {"seedance20": "seedance20_prompts.json", "seedance25": "seedance25_prompts.json", "jimeng20": "jimeng20_prompts.json", "jimeng25": "jimeng25_prompts.json"}


def render_report(report: dict) -> str:
    lines = ["# 连续性审核报告", "", "## 总体结论", "", f"连续性评分：{report['continuity_score']}", f"审核状态：{'通过' if report['gate'] == 'passed' else '需要复核'}", f"Gate：{report['gate']}", "", "## 关键问题", ""]
    if not report["issues"]:
        lines.append("未发现连续性问题。")
    for issue in report["issues"]:
        lines += [f"### {issue['issue_id']}｜{issue['description']}", "", f"严重程度：{issue['severity']}", f"涉及镜头：{issue['shot_id']}", f"涉及资产：{'、'.join(issue['asset_ids']) or '无'}", "", "【问题】", issue["description"], "", "【证据】", issue["evidence"], "", "【期望状态】", issue["expected"], "", "【当前状态】", issue["actual"], "", "【建议修复阶段】", issue["suggested_fix_stage"], "", "【建议修复】", issue["suggested_fix"], "", f"自动修复安全：{'是' if issue['auto_fix_safe'] else '否'}", ""]
    sections = [("人物连续性", "character"), ("服装与状态连续性", "costume"), ("道具连续性", "prop"), ("武器连续性", "weapon"), ("场景空间连续性", "spatial"), ("时间与天气连续性", "temporal"), ("镜头首尾连续性", "state_link"), ("四模型一致性", "cross_model")]
    for title, category in sections:
        issues = [item for item in report["issues"] if item["category"] == category]
        lines += [f"## {title}", "", f"问题数：{len(issues)}", ""]
        lines += [f"- {item['issue_id']}：{item['description']}（{item['severity']}）" for item in issues] or ["- 未发现问题。"]
        lines.append("")
    lines += ["## 待人工确认", "", "- 任何 error 或 critical 问题应回到建议阶段处理。", "", "## 通过项", "", f"- 已检查 {len(report['shot_links'])} 个镜头。", f"- 四模型共同事实一致：{'是' if report['cross_model']['consistent'] else '否'}。", ""]
    return "\n".join(lines) + "\n"


def run_stage10(project_dir: Path) -> str:
    context = load_model_stage_context(project_dir)
    original = next(project_dir.glob("00_原始剧本.*"))
    for path in [project_dir / "01_剧本解析报告.md", original]:
        if not path.is_file(): raise ValueError(f"Stage 10 缺少输入：{path.name}")
    model_outputs = {}
    for key, filename in MODEL_FILES.items():
        path = project_dir / filename
        if not path.is_file(): raise ValueError(f"Stage 10 缺少模型输出：{filename}")
        model_outputs[key] = json.loads(path.read_text(encoding="utf-8"))
    index_path = project_dir / "model_prompt_index.json"
    if not index_path.is_file(): raise ValueError("Stage 10 缺少 model_prompt_index.json。")
    rules = read_model_sources("新版规则库", RULE_NAMES)
    before = {path: path.read_bytes() for path in [original, project_dir / "01_剧本解析报告.md", context.project_rules, context.assets_md, context.asset_prompts_md, context.storyboard_md, context.registry_path, context.asset_prompts_path, context.storyboard_path, index_path] + [project_dir / name for name in MODEL_FILES.values()]}

    def operation() -> str:
        report = audit_project(context.project, context.storyboard, context.registry, model_outputs)
        asset_ids = {asset_id for assets in context.registry["assets"].values() for asset_id in assets}
        shot_ids = {shot["shot_id"] for shot in shots_from_storyboard(context.storyboard)}
        validate_continuity_report(report, shot_ids, asset_ids)
        if any(path.read_bytes() != content for path, content in before.items()):
            raise ValueError("Stage 10 修改了上游文件。")
        markdown = render_report(report)
        atomic_json_write(project_dir / JSON_NAME, report)
        return markdown

    runner = StageRunner(project_dir, 10, REPORT_NAME, "Stage 10 连续性审核")
    return runner.run(operation, lambda text: text.startswith("# 连续性审核报告") and "连续性评分" in text)
