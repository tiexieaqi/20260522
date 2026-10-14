"""连续性报告 Schema 校验。"""

from continuity_schema import CATEGORIES, GATES, SEVERITIES


def validate_continuity_report(report: dict, shot_ids: set[str], asset_ids: set[str]) -> None:
    if not isinstance(report, dict) or report.get("schema_version") != "1.0":
        raise ValueError("continuity_report.json Schema 无效。")
    if not isinstance(report.get("continuity_score"), (int, float)) or not 0 <= report["continuity_score"] <= 100:
        raise ValueError("连续性评分必须在 0—100。")
    if report.get("gate") not in GATES or not isinstance(report.get("issues"), list):
        raise ValueError("连续性 Gate 或 issues 无效。")
    seen = set()
    for issue in report["issues"]:
        for field in ("issue_id", "category", "severity", "shot_id", "description", "evidence", "expected", "actual", "suggested_fix", "suggested_fix_stage", "auto_fix_safe"):
            if field not in issue:
                raise ValueError(f"问题缺少字段 {field}。")
        if issue["issue_id"] in seen or issue["category"] not in CATEGORIES or issue["severity"] not in SEVERITIES:
            raise ValueError("问题编号、分类或严重程度无效。")
        seen.add(issue["issue_id"])
        if issue["shot_id"] and issue["shot_id"] not in shot_ids:
            raise ValueError(f"问题引用未知镜头：{issue['shot_id']}")
        if issue.get("next_shot_id") and issue["next_shot_id"] not in shot_ids:
            raise ValueError(f"问题引用未知后续镜头：{issue['next_shot_id']}")
        normalised_assets = {asset.split("-V", 1)[0] for asset in asset_ids}
        if not isinstance(issue["asset_ids"], list) or any(asset not in asset_ids and asset.split("-V", 1)[0] not in normalised_assets for asset in issue["asset_ids"]):
            raise ValueError("问题引用未知资产。")
        if not isinstance(issue["auto_fix_safe"], bool) or not isinstance(issue["suggested_fix_stage"], str):
            raise ValueError("问题修复建议字段无效。")
