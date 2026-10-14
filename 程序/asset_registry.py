"""资产去重、编号、版本和原子保存。"""

import copy
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from asset_schema import ASSET_CATEGORIES, empty_registry, validate_registry
from file_utils import json_read


def load_registry(path: Path, project_id: str) -> dict:
    if not path.exists():
        return empty_registry(project_id, datetime.now(timezone.utc).isoformat())
    data = json_read(path)
    if data.get("schema_version") == "1.0" and isinstance(data.get("assets"), list):
        raise ValueError("旧版 assets.json 需要在 Stage 03 前重新初始化，拒绝覆盖迁移。")
    validate_registry(data)
    return data


def _text_keys(item: dict) -> set[str]:
    names = [item.get("canonical_name", "")] + item.get("aliases", [])
    return {str(value).strip().casefold() for value in names if str(value).strip()}


def _find_match(category: str, item: dict, registry: dict) -> dict | None:
    keys = _text_keys(item)
    item_type = str(item.get("asset_type", category)).casefold()
    item_role = str(item.get("story_role", "")).casefold()
    for existing in registry["assets"][category].values():
        existing_keys = _text_keys(existing)
        if keys & existing_keys:
            if str(existing.get("asset_type", category)).casefold() == item_type and (
                not item_role or not existing.get("story_role") or str(existing.get("story_role")).casefold() == item_role
            ):
                return existing
    return None


def _next_id(category: str, registry: dict) -> str:
    number = registry["id_counters"][category]
    while True:
        asset_id = f"{category}-{number:03d}"
        if asset_id not in registry["assets"][category] and asset_id not in registry["retired_ids"]:
            registry["id_counters"][category] = number + 1
            return asset_id
        number += 1


def _normalise_version(asset_id: str, version: dict, index: int) -> dict:
    version_name = str(version.get("version", f"{asset_id}-V{index:02d}"))
    if not version_name.startswith(asset_id + "-V"):
        version_name = f"{asset_id}-V{index:02d}"
    return {
        "version": version_name,
        "label": str(version.get("label", "标准状态" if index == 1 else "状态变化")),
        "changes": version.get("changes", []),
        "source_evidence": version.get("source_evidence", []),
    }


def build_registry(plan: dict, current: dict) -> tuple[dict, list[str]]:
    registry = copy.deepcopy(current)
    review_items = []
    for item in plan["assets"]:
        category = item["category"]
        existing = _find_match(category, item, registry)
        if existing:
            asset_id = existing["id"]
            review_items.append(f"已绑定已有资产 {asset_id}：{item['canonical_name']}")
            continue
        asset_id = _next_id(category, registry)
        versions = [_normalise_version(asset_id, version, index) for index, version in enumerate(item["versions"], 1)]
        if versions[0]["version"] != f"{asset_id}-V01":
            raise ValueError(f"资产 {asset_id} 版本必须从 V01 开始。")
        record = {
            "id": asset_id,
            "canonical_name": item["canonical_name"],
            "aliases": item.get("aliases", []),
            "asset_type": item.get("asset_type", category),
            "importance": item.get("importance", "待确认"),
            "story_role": item.get("story_role", "待确认"),
            "status": "NEEDS_REVIEW" if item.get("needs_review") else "LOCKED",
            "versions": versions,
            "locked_fields": item.get("locked_fields", []),
            "mutable_fields": item.get("mutable_fields", []),
            "source_evidence": item["source_evidence"],
            "details": item.get("details", {}),
        }
        registry["assets"][category][asset_id] = record
    registry["updated_at"] = datetime.now(timezone.utc).isoformat()
    validate_registry(registry)
    return registry, review_items


def atomic_save(path: Path, data: dict) -> None:
    validate_registry(data)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
