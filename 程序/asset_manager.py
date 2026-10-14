"""资产登记表初始化和未来资产锁定的最小接口。"""

from pathlib import Path

from asset_registry import atomic_save, build_registry, load_registry
from asset_schema import empty_registry
from file_utils import json_write


ASSET_CATEGORIES = ("CH", "LOC", "PROP", "WPN", "GRP", "FX")


def new_assets_data(project_id: str) -> dict:
    from datetime import datetime, timezone
    return empty_registry(project_id, datetime.now(timezone.utc).isoformat())


def allocate_asset_id(data: dict, category: str) -> str:
    """为未来 AI/人工登记提供不重复的基础资产编号。"""
    if category not in ASSET_CATEGORIES:
        raise ValueError(f"不支持的资产类型：{category}")
    counters = data.get("id_counters", data.get("counters", {}))
    number = int(counters.get(category, 1))
    asset_id = f"{category}-{number:03d}"
    existing_ids = set(data.get("retired_ids", []))
    if isinstance(data.get("assets"), dict):
        existing_ids.update(data["assets"].get(category, {}).keys())
    else:
        existing_ids.update(item.get("asset_id") for item in data.get("assets", []))
    while asset_id in existing_ids:
        number += 1
        asset_id = f"{category}-{number:03d}"
    counters[category] = number + 1
    return asset_id


def initialize_assets(project_dir: Path, project_id: str) -> Path:
    path = project_dir / "assets.json"
    json_write(path, new_assets_data(project_id))
    return path


def register_asset(
    project_dir: Path,
    category: str,
    name: str,
    asset_type: str | None = None,
    source_reference: str = "",
) -> dict:
    """登记并锁定一个基础资产，供后续 AI 阶段调用。"""
    path = project_dir / "assets.json"
    current = load_registry(path, project_dir.name)
    updated, _ = build_registry({"assets": [{"category": category, "canonical_name": name, "aliases": [], "asset_type": asset_type or category, "source_evidence": [source_reference or "待确认"], "versions": [{"label": "标准状态"}], "locked_fields": [], "mutable_fields": []}]}, current)
    atomic_save(path, updated)
    return next(item for item in updated["assets"][category].values() if item["canonical_name"] == name)
