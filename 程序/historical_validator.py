"""历史审核报告 Schema 校验。"""

from historical_schema import CATEGORIES, EVIDENCE_LEVELS, GATES, SEVERITIES, VERIFICATION_STATUS


def validate_historical_report(report: dict, shot_ids: set[str], asset_ids: set[str]) -> None:
    if not isinstance(report, dict) or report.get("schema_version") != "1.0":
        raise ValueError("historical_report.json Schema 无效。")
    if report.get("historical_relevance") not in {"none", "low", "medium", "high"} or report.get("historical_gate") not in GATES:
        raise ValueError("历史相关度或 Gate 无效。")
    if not isinstance(report.get("historical_score"), (int, float)) or not 0 <= report["historical_score"] <= 100:
        raise ValueError("历史真实性评分必须在 0—100。")
    claims = report.get("claims", [])
    claim_ids = set()
    for claim in claims:
        for field in ("claim_id", "claim", "category", "source_origin", "related_shots", "related_assets"):
            if field not in claim: raise ValueError(f"历史事实缺少字段：{field}")
        if claim["claim_id"] in claim_ids or claim["category"] not in CATEGORIES: raise ValueError("历史事实编号或分类无效。")
        claim_ids.add(claim["claim_id"])
        if any(shot not in shot_ids for shot in claim["related_shots"]) or any(asset not in asset_ids and asset.split("-V", 1)[0] not in asset_ids for asset in claim["related_assets"]): raise ValueError("历史事实引用未知镜头或资产。")
    issue_ids = set()
    for issue in report.get("issues", []):
        required = ("issue_id", "category", "severity", "verification_status", "claim", "related_shots", "related_assets", "evidence", "evidence_level", "source_refs", "conflicting_sources", "historical_expected", "project_current", "dramatization_type", "production_deviation", "suggested_fix_stage", "suggested_fix", "requires_external_verification")
        if any(field not in issue for field in required): raise ValueError("历史问题字段不完整。")
        if issue["issue_id"] in issue_ids or issue["category"] not in CATEGORIES or issue["severity"] not in SEVERITIES or issue["verification_status"] not in VERIFICATION_STATUS or issue["evidence_level"] not in EVIDENCE_LEVELS: raise ValueError("历史问题编号、分类、状态或证据等级无效。")
        issue_ids.add(issue["issue_id"])
        if any(shot not in shot_ids for shot in issue["related_shots"]) or any(asset not in asset_ids and asset.split("-V", 1)[0] not in asset_ids for asset in issue["related_assets"]): raise ValueError("历史问题引用未知镜头或资产。")
        if not isinstance(issue["source_refs"], list) or not isinstance(issue["requires_external_verification"], bool): raise ValueError("历史问题来源字段无效。")
    source_ids = {source.get("source_id") for source in report.get("sources", [])}
    if any(ref not in source_ids for issue in report.get("issues", []) for ref in issue["source_refs"]): raise ValueError("历史问题引用了不存在的来源。")
    if not isinstance(report.get("requires_external_verification"), list): raise ValueError("外部核验清单无效。")
