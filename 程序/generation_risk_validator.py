"""生成风险报告 Schema 校验。"""

from generation_risk_schema import GATES, MODELS, SEVERITIES


def validate_generation_report(report: dict, shot_ids: set[str], asset_ids: set[str]) -> None:
    if not isinstance(report, dict) or report.get("schema_version") != "1.0": raise ValueError("generation_risk_report.json Schema 无效。")
    if not 0 <= report.get("overall_risk_score", -1) <= 100 or report.get("generation_gate") not in GATES: raise ValueError("风险评分或 Gate 无效。")
    seen = set()
    for issue in report.get("issues", []):
        for field in ("issue_id", "category", "risk_type", "severity", "risk_score", "shot_id", "model", "asset_ids", "description", "evidence", "failure_mode", "suggested_fix_stage", "suggested_fix", "auto_fix_safe"):
            if field not in issue: raise ValueError(f"风险问题缺少字段：{field}")
        if issue["issue_id"] in seen or issue["severity"] not in SEVERITIES or not 0 <= issue["risk_score"] <= 100 or issue["model"] not in MODELS and issue["model"] != "all": raise ValueError("风险问题编号、严重度、模型或分数无效。")
        seen.add(issue["issue_id"])
        if issue["shot_id"] not in shot_ids or any(asset.split("-V", 1)[0] not in asset_ids for asset in issue["asset_ids"]): raise ValueError("风险问题引用未知镜头或资产。")
    if any(model not in report.get("model_risks", {}) for model in MODELS): raise ValueError("缺少模型专项风险。")
