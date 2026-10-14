"""Stage 12：AI 视频生成稳定性静态终审。"""

import json
from pathlib import Path

from file_utils import atomic_json_write, read_utf8
from generation_risk_auditor import audit_generation
from generation_risk_validator import validate_generation_report
from model_stage_base import load_model_stage_context, read_model_sources, flatten_asset_refs
from stage_base import StageRunner

REPORT_NAME = "12_AI生成风险报告.md"
JSON_NAME = "generation_risk_report.json"
MODEL_FILES = {"seedance20": "seedance20_prompts.json", "seedance25": "seedance25_prompts.json", "jimeng20": "jimeng20_prompts.json", "jimeng25": "jimeng25_prompts.json"}
RULE_NAMES = ["00_系统总控规则.md", "08_分镜导演规则.md", "09_Seedance2.0规则.md", "10_Seedance2.5规则.md", "11_即梦2.0规则.md", "12_即梦2.5规则.md", "14_项目规则隔离规则.md"]
UPSTREAM = ("01_剧本解析报告.md", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "assets.json", "asset_prompts.json", "storyboard.json", "06_Seedance2.0提示词.md", "07_Seedance2.5提示词.md", "08_即梦2.0提示词.md", "09_即梦2.5提示词.md", "seedance20_prompts.json", "seedance25_prompts.json", "jimeng20_prompts.json", "jimeng25_prompts.json", "model_prompt_index.json", "10_连续性审核报告.md", "continuity_report.json", "11_历史真实性审核报告.md", "historical_report.json")


def _model_status(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def render_report(report: dict) -> str:
    lines = ["# AI生成风险终审", "", "## 一、总体结论", "", f"总体风险：{report['risk_level']}", f"风险评分：{report['overall_risk_score']}", f"Generation Gate：{report['generation_gate']}", f"流水线状态：{report['final_pipeline_status']}", "", "## 二、高风险镜头", ""]
    for shot_id in report["high_risk_shots"]:
        item = report["shot_risks"][shot_id]
        rec = report["recommended_models"].get(shot_id, {})
        lines += [f"### {shot_id}", f"风险：{item['risk_level']}", f"评分：{item['generation_risk_score']}", f"推荐模型：{rec.get('recommended_model', 'any')}", f"推荐模式：{rec.get('recommended_prompt_mode', 'stable')}", ""]
        for issue in report["issues"]:
            if issue["shot_id"] == shot_id:
                lines += [f"- {issue['risk_type']}：{issue['description']}；失败形态：{issue['failure_mode']}"]
        lines.append("")
    if not report["high_risk_shots"]:
        lines.append("未发现高风险镜头。\n")
    categories = [("人物生成风险", {"CHARACTER", "FACE", "BODY"}), ("动作生成风险", {"MOTION"}), ("台词 / 口型风险", {"DIALOGUE", "LIPSYNC"}), ("道具 / 武器风险", {"PROP", "WEAPON"}), ("群体风险", {"GROUP"}), ("场景空间风险", {"LOCATION", "CONTINUITY"}), ("摄影 / 运镜风险", {"CAMERA"}), ("Prompt过载风险", {"PROMPT"}), ("FX风险", {"FX"})]
    for title, cats in categories:
        lines += [f"## {title}", ""]
        items = [i for i in report["issues"] if i["category"] in cats]
        lines += [f"- {i['issue_id']}｜{i['risk_type']}｜{i['severity']}｜{i['description']}" for i in items] or ["- 未发现。"]
        lines.append("")
    lines += ["## 四模型专项风险", ""]
    for model, item in report["model_risks"].items():
        lines += [f"### {model}", f"检查镜头数：{len(item.get('shots', {}))}", ""]
    lines += ["## 建议回退修改阶段", ""]
    lines += [f"- {i['issue_id']}：{i['suggested_fix_stage']}：{i['suggested_fix']}" for i in report["issues"]] or ["- 无。"]
    lines += ["", "## 静态审核已通过项", "", "- 已完成资产、镜头、提示词和审核报告的静态风险扫描。", "- 未调用 Seedance 或即梦真实视频生成服务。", "", "## 需要真实生成验证项", "", "- 仍需在用户本机分别调用视频模型后，根据实际成片反馈复核。"]
    return "\n".join(lines) + "\n"


def _final_status(project: dict, report: dict, workflow: dict) -> dict:
    stages = workflow.get("stages", {})
    historical = json.loads((project["_path"] / "historical_report.json").read_text(encoding="utf-8"))
    critical = [i["issue_id"] for i in report["issues"] if i["severity"] == "critical"]
    continuity = json.loads((project["_path"] / "continuity_report.json").read_text(encoding="utf-8"))
    return {"schema_version": "1.0", "project": project["project_name"], "project_id": project["project_id"], "stage_completion": {k: v.get("status") for k, v in stages.items()}, "continuity_gate": continuity.get("gate", "unknown"), "historical_gate": historical.get("historical_gate", "unknown"), "generation_gate": report["generation_gate"], "final_pipeline_status": report["final_pipeline_status"], "total_shots": len(report["shot_risks"]), "high_risk_shots": report["high_risk_shots"], "unverified_historical_claims": historical.get("requires_external_verification", []), "critical_issues": critical, "recommended_next_action": "先处理阻断问题后再进行真实视频生成" if report["final_pipeline_status"] == "blocked" else "可进入人工复核或本机真实生成验收"}


def run_stage12(project_dir: Path) -> str:
    context = load_model_stage_context(project_dir)
    for name in UPSTREAM:
        if not (project_dir / name).is_file():
            raise ValueError(f"Stage 12 缺少输入：{name}")
    continuity = json.loads((project_dir / "continuity_report.json").read_text(encoding="utf-8"))
    historical = json.loads((project_dir / "historical_report.json").read_text(encoding="utf-8"))
    if continuity.get("gate") not in {"passed", "review_required", "blocked"}:
        raise ValueError("Stage 12 需要有效的 Stage 10 continuity_report.json。")
    if historical.get("historical_gate") not in {"passed", "review_required", "blocked", "not_applicable"}:
        raise ValueError("Stage 12 需要有效的 Stage 11 historical_report.json。")
    model_outputs = {key: _model_status(project_dir / filename) for key, filename in MODEL_FILES.items()}
    read_model_sources("新版规则库", RULE_NAMES)
    protected = [context.original] + [project_dir / name for name in UPSTREAM]
    before = {p: p.read_bytes() for p in protected}
    project = dict(context.project); project["_path"] = project_dir
    workflow = json.loads((project_dir / "workflow_state.json").read_text(encoding="utf-8"))

    def operation() -> str:
        report = audit_generation(context.project, context.storyboard, context.registry, model_outputs, continuity, historical)
        shot_ids = {shot["shot_id"] for scene in context.storyboard["scenes"] for shot in scene["shots"]}
        asset_ids = {aid for group in context.registry["assets"].values() for aid in group}
        validate_generation_report(report, shot_ids, asset_ids)
        if any(p.read_bytes() != data for p, data in before.items()):
            raise ValueError("Stage 12 修改了上游文件。")
        final = _final_status(project, report, workflow)
        atomic_json_write(project_dir / JSON_NAME, report)
        atomic_json_write(project_dir / "project_final_status.json", final)
        return render_report(report)

    return StageRunner(project_dir, 12, REPORT_NAME, "Stage 12 AI生成风险终审").run(operation, lambda text: text.startswith("# AI生成风险终审") and "Generation Gate" in text)
