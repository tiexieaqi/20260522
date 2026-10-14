"""所有视频模型适配结果共用的母版一致性校验。"""

from model_stage_base import flatten_asset_refs


ALLOWED_STATUS = {"compatible", "warning", "requires_review"}
ALLOWED_RISK = {"low", "medium", "high"}


def storyboard_shots(storyboard: dict) -> dict[str, dict]:
    return {shot["shot_id"]: shot for scene in storyboard["scenes"] for shot in scene["shots"]}


def registry_versions(registry: dict) -> set[str]:
    return {version["version"] for assets in registry["assets"].values() for asset in assets.values() for version in asset["versions"]}


def validate_model_plan(plan: dict, storyboard: dict, registry: dict, asset_prompts: dict, *, model: str, prompt_budget: int, required_shot_fields: tuple[str, ...] = ()) -> None:
    if not isinstance(plan, dict) or plan.get("schema_version") != "1.0" or plan.get("model") != model:
        raise ValueError(f"{model} 输出 Schema 或模型标识无效。")
    expected = storyboard_shots(storyboard)
    shots = plan.get("shots")
    if not isinstance(shots, dict) or list(shots) != list(expected):
        raise ValueError(f"{model} 镜头必须与 storyboard.json 顺序一致且一一对应。")
    valid_versions = registry_versions(registry)
    prompt_versions = set(asset_prompts.get("prompts", {}))
    for shot_id, source in expected.items():
        item = shots[shot_id]
        if item.get("source_shot_id") != shot_id or item.get("duration_seconds") != source.get("duration_seconds"):
            raise ValueError(f"镜头编号或时长被改变：{shot_id}")
        prompt = item.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > prompt_budget:
            raise ValueError(f"提示词为空或超过模型预算：{shot_id}")
        refs = item.get("asset_refs")
        if not isinstance(refs, list) or any(ref not in valid_versions or ref not in prompt_versions for ref in refs):
            raise ValueError(f"资产引用无效：{shot_id}")
        if refs != flatten_asset_refs(source):
            raise ValueError(f"资产引用顺序或内容被改变：{shot_id}")
        if item.get("dialogue") != source.get("dialogue", []):
            raise ValueError(f"对白或 speaker 被改变：{shot_id}")
        if item.get("start_state") != source.get("start_state") or item.get("end_state") != source.get("end_state"):
            raise ValueError(f"首尾状态被改变：{shot_id}")
        if item.get("model_duration_status") not in ALLOWED_STATUS:
            raise ValueError(f"模型时长状态无效：{shot_id}")
        risk = item.get("risk", {})
        if risk.get("level") not in ALLOWED_RISK or not isinstance(risk.get("reasons"), list) or risk["level"] == "high" and not risk["reasons"]:
            raise ValueError(f"风险评分无效：{shot_id}")
        forbidden = item.get("forbidden")
        if not isinstance(forbidden, list) or not all(isinstance(x, str) for x in forbidden):
            raise ValueError(f"禁止项无效：{shot_id}")
        if not all(term in " ".join(forbidden) for term in ("字幕", "logo", "水印")):
            raise ValueError(f"禁止项不完整：{shot_id}")
        if any(rule not in forbidden for rule in source.get("forbidden", [])):
            raise ValueError(f"未完整继承标准分镜禁止项：{shot_id}")
        for field in required_shot_fields:
            if field not in item:
                raise ValueError(f"模型适配缺少字段 {field}：{shot_id}")
