"""标准分镜 Schema 和连续性验证。"""

from storyboard_schema import COMPLEXITIES, DIALOGUE_TYPES, MOVEMENTS, SHOT_SIZES


def _asset_versions(registry: dict) -> dict[str, tuple[str, str]]:
    result = {}
    for category, assets in registry["assets"].items():
        for asset_id, asset in assets.items():
            for version in asset["versions"]:
                result[version["version"]] = (asset_id, category)
    return result


def validate_storyboard(document: dict, registry: dict) -> None:
    if not isinstance(document, dict) or document.get("schema_version") != "1.0":
        raise ValueError("storyboard.json Schema 版本无效。")
    scenes = document.get("scenes")
    timeline = document.get("continuity_timeline")
    if not isinstance(timeline, list):
        raise ValueError("标准分镜缺少 continuity_timeline。")
    if not isinstance(scenes, list) or not scenes:
        raise ValueError("标准分镜至少需要一个剧情段。")
    versions = _asset_versions(registry)
    scene_ids, shot_ids = set(), set()
    previous_end = None
    previous_versions = {}
    total = 0.0
    has_model_terms = False
    for scene in scenes:
        scene_id = scene.get("scene_id")
        if not isinstance(scene_id, str) or not scene_id.startswith("S") or scene_id in scene_ids:
            raise ValueError(f"scene_id 无效或重复：{scene_id}")
        scene_ids.add(scene_id)
        shots = scene.get("shots")
        if not isinstance(shots, list) or not shots:
            raise ValueError(f"剧情段没有镜头：{scene_id}")
        for shot in shots:
            shot_id = shot.get("shot_id")
            if not isinstance(shot_id, str) or not shot_id.startswith(scene_id + "_SH") or shot_id in shot_ids:
                raise ValueError(f"shot_id 无效或重复：{shot_id}")
            shot_ids.add(shot_id)
            duration = shot.get("duration_seconds")
            if not isinstance(duration, (int, float)) or duration <= 0:
                raise ValueError(f"镜头时长无效：{shot_id}")
            total += float(duration)
            camera = shot.get("camera", {})
            if camera.get("shot_size") not in SHOT_SIZES or camera.get("movement") not in MOVEMENTS or not camera.get("focal_length"):
                raise ValueError(f"镜头摄影字段不完整：{shot_id}")
            if shot.get("action_complexity") not in COMPLEXITIES or not shot.get("movement_style"):
                raise ValueError(f"镜头动作字段不完整：{shot_id}")
            if shot.get("action_complexity") == "high" and len(shot.get("action", [])) > 3:
                raise ValueError(f"高复杂度镜头动作过多，应拆镜：{shot_id}")
            for key in ("start_state", "end_state", "blocking", "forbidden"):
                if key not in shot:
                    raise ValueError(f"镜头缺少字段 {key}：{shot_id}")
            if not isinstance(shot["forbidden"], list) or not all(isinstance(x, str) for x in shot["forbidden"]):
                raise ValueError(f"镜头禁止项无效：{shot_id}")
            forbidden = " ".join(shot["forbidden"]).casefold()
            if not all(x in forbidden for x in ("字幕", "logo", "水印")):
                raise ValueError(f"镜头缺少基础禁止项：{shot_id}")
            if previous_end is not None and not shot.get("start_state", {}).get("compatible_with_previous", True):
                raise ValueError(f"镜头首状态无法衔接上一镜：{shot_id}")
            previous_end = shot["end_state"]
            for group in ("characters", "props", "weapons", "groups", "fx"):
                for asset_version in shot.get("assets", {}).get(group, []):
                    if asset_version not in versions:
                        raise ValueError(f"未知资产版本：{asset_version}")
                    base_id, _ = versions[asset_version]
                    current_version = int(asset_version.rsplit("-V", 1)[1])
                    old_version = previous_versions.get(base_id)
                    if old_version and current_version < old_version and not shot.get("is_flashback", False):
                        raise ValueError(f"人物/道具/场景版本倒退：{asset_version}")
                    previous_versions[base_id] = current_version
            location = shot.get("assets", {}).get("location")
            if location:
                if location not in versions:
                    raise ValueError(f"未知场景版本：{location}")
                previous_versions[versions[location][0]] = int(location.rsplit("-V", 1)[1])
            for dialogue in shot.get("dialogue", []):
                if dialogue.get("dialogue_type") not in DIALOGUE_TYPES:
                    raise ValueError(f"对白类型无效：{shot_id}")
                if not isinstance(dialogue.get("estimated_duration"), (int, float)) or dialogue["estimated_duration"] <= 0:
                    raise ValueError(f"对白时长无效：{shot_id}")
                for field in ("speaker", "dialogue", "pause_before", "pause_after", "emotion"):
                    if field not in dialogue:
                        raise ValueError(f"对白缺少字段 {field}：{shot_id}")
                if dialogue["dialogue_type"] == "character_dialogue":
                    speaker_id = dialogue.get("speaker_asset_id")
                    if not speaker_id or f"{speaker_id}-V01" not in versions or versions[f"{speaker_id}-V01"][1] != "CH":
                        raise ValueError(f"对白说话人不是有效人物资产：{shot_id}")
                    if not dialogue.get("lip_sync_required", False):
                        raise ValueError(f"角色对白必须要求口型同步：{shot_id}")
                elif dialogue["dialogue_type"] == "voiceover" and dialogue.get("lip_sync_required", True):
                    raise ValueError(f"旁白不得要求画面人物口型：{shot_id}")
            text = str(shot)
            if "Seedance" in text or "即梦" in text:
                has_model_terms = True
    if has_model_terms:
        raise ValueError("标准分镜不得包含模型专用描述。")
    timeline_ids = [item.get("shot_id") for item in timeline if isinstance(item, dict)]
    if set(timeline_ids) != shot_ids or len(timeline_ids) != len(shot_ids):
        raise ValueError("continuity_timeline 必须为每个镜头提供唯一结束状态。")
    declared = document.get("total_duration_seconds")
    if not isinstance(declared, (int, float)) or abs(float(declared) - total) > 0.01:
        raise ValueError("总时长与镜头时长之和不一致。")
