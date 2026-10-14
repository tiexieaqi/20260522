"""Stage 03 资产登记表 Schema 和校验。"""

import re

ASSET_CATEGORIES = ("CH", "LOC", "PROP", "WPN", "GRP", "FX")
ASSET_STATUSES = ("LOCKED", "NEEDS_REVIEW", "RETIRED")
ID_PATTERN = re.compile(r"^(CH|LOC|PROP|WPN|GRP|FX)-\d{3,}$")


def empty_registry(project_id: str, created_at: str) -> dict:
    return {
        "schema_version": "2.0",
        "project_id": project_id,
        "created_at": created_at,
        "updated_at": created_at,
        "assets": {category: {} for category in ASSET_CATEGORIES},
        "id_counters": {category: 1 for category in ASSET_CATEGORIES},
        "retired_ids": [],
        "id_policy": {
            "base_format": "PREFIX-001",
            "version_format": "PREFIX-001-V01",
            "never_reuse": True,
            "project_local": True,
        },
    }


def validate_registry(data: dict) -> None:
    if not isinstance(data, dict) or data.get("schema_version") != "2.0":
        raise ValueError("assets.json Schema 版本不正确。")
    if not isinstance(data.get("assets"), dict) or set(data["assets"]) != set(ASSET_CATEGORIES):
        raise ValueError("assets.json 缺少完整资产分类。")
    if not isinstance(data.get("id_counters"), dict):
        raise ValueError("assets.json 缺少 id_counters。")
    all_ids = set(data.get("retired_ids", []))
    for category in ASSET_CATEGORIES:
        counter = data["id_counters"].get(category)
        if not isinstance(counter, int) or counter < 1:
            raise ValueError(f"{category} 编号计数器无效。")
        for asset_id, asset in data["assets"][category].items():
            if not ID_PATTERN.match(asset_id) or not asset_id.startswith(category + "-"):
                raise ValueError(f"资产 ID 无效：{asset_id}")
            if asset_id in all_ids:
                raise ValueError(f"资产 ID 与废止 ID 重复：{asset_id}")
            all_ids.add(asset_id)
            for field in ("id", "canonical_name", "aliases", "status", "versions", "locked_fields", "mutable_fields", "source_evidence"):
                if field not in asset:
                    raise ValueError(f"资产 {asset_id} 缺少字段：{field}")
            if asset["status"] not in ASSET_STATUSES:
                raise ValueError(f"资产 {asset_id} 状态无效。")
            if not isinstance(asset["versions"], list) or not asset["versions"]:
                raise ValueError(f"资产 {asset_id} 缺少版本。")
            if asset["versions"][0].get("version") != f"{asset_id}-V01":
                raise ValueError(f"资产 {asset_id} 必须从 V01 开始。")


def validate_plan(plan: dict) -> None:
    if not isinstance(plan, dict) or not isinstance(plan.get("assets"), list):
        raise ValueError("Stage 03 AI 输出缺少 assets 列表。")
    for index, item in enumerate(plan["assets"], 1):
        if not isinstance(item, dict):
            raise ValueError(f"第 {index} 个资产不是对象。")
        if item.get("category") not in ASSET_CATEGORIES:
            raise ValueError(f"第 {index} 个资产类型无效。")
        if not str(item.get("canonical_name", "")).strip():
            raise ValueError(f"第 {index} 个资产缺少 canonical_name。")
        if not isinstance(item.get("aliases", []), list):
            raise ValueError(f"第 {index} 个资产 aliases 必须是列表。")
        if not isinstance(item.get("source_evidence", []), list) or not item["source_evidence"]:
            raise ValueError(f"第 {index} 个资产缺少 source_evidence。")
        if not isinstance(item.get("versions", []), list) or not item["versions"]:
            raise ValueError(f"第 {index} 个资产缺少 V01 版本。")
