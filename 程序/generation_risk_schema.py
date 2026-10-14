"""Stage 12 风险报告结构。"""

SEVERITIES = {"info", "warning", "error", "critical"}
GATES = {"passed", "review_required", "blocked"}
MODELS = {"seedance20", "seedance25", "jimeng20", "jimeng25"}


def empty_risk_report(project: dict) -> dict:
    return {"schema_version": "1.0", "project": project["project_name"], "project_id": project["project_id"], "overall_risk_score": 0, "risk_level": "low", "generation_gate": "passed", "scores": {}, "shot_risks": {}, "issues": [], "model_risks": {model: {} for model in MODELS}, "high_risk_shots": [], "recommended_models": {}, "failure_patterns": [], "requires_real_generation_test": [], "final_pipeline_status": "ready"}
