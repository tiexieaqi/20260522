"""即梦 2.5 专属字段、电影增强和事实不变校验。"""

from jimeng25_adapter import JIMENG25_CINEMATIC_BUDGET, JIMENG25_STABLE_BUDGET
from jimeng20_validator import validate_physical_constraints
from model_prompt_validator import validate_model_plan


def validate_jimeng25_plan(plan: dict, storyboard: dict, registry: dict, asset_prompts: dict) -> None:
    required = ("adapter_profile", "stable_prompt", "cinematic_prompt", "recommended_prompt_mode", "recommendation_reason", "cinematic_features", "cinematic_budget", "action_beats", "performance_beats", "dialogue_timing", "end_frame_anchor", "jimeng25_risk", "risk_reasons", "jimeng25_prompt_budget")
    validate_model_plan(plan, storyboard, registry, asset_prompts, model="jimeng-2.5", prompt_budget=JIMENG25_CINEMATIC_BUDGET, required_shot_fields=required)
    expected = {shot["shot_id"]: shot for scene in storyboard["scenes"] for shot in scene["shots"]}
    for shot_id, item in plan["shots"].items():
        source = expected[shot_id]
        if item.get("adapter_profile") != "jimeng-2.5" or item.get("jimeng25_prompt_budget") != JIMENG25_CINEMATIC_BUDGET:
            raise ValueError(f"即梦 2.5 适配配置无效：{shot_id}")
        if item.get("recommended_prompt_mode") not in {"stable", "cinematic"}:
            raise ValueError(f"推荐模式无效：{shot_id}")
        if not isinstance(item.get("recommendation_reason"), str) or not item["recommendation_reason"].strip():
            raise ValueError(f"推荐模式原因缺失：{shot_id}")
        if item.get("jimeng25_risk") not in {"low", "medium", "high"} or item.get("risk") != {"level": item["jimeng25_risk"], "reasons": item["risk_reasons"]}:
            raise ValueError(f"即梦 2.5 风险字段无效：{shot_id}")
        if item["jimeng25_risk"] == "high" and item["recommended_prompt_mode"] != "stable":
            raise ValueError(f"高风险镜头推荐模式必须为 stable：{shot_id}")
        budget = item["cinematic_budget"]
        if budget != {"stable_budget": JIMENG25_STABLE_BUDGET, "cinematic_budget": JIMENG25_CINEMATIC_BUDGET}:
            raise ValueError(f"电影增强预算无效：{shot_id}")
        if not isinstance(item["stable_prompt"], str) or not item["stable_prompt"].strip() or not isinstance(item["cinematic_prompt"], str) or not item["cinematic_prompt"].strip():
            raise ValueError(f"stable/cinematic 提示词缺失：{shot_id}")
        if len(item["stable_prompt"]) > JIMENG25_STABLE_BUDGET or len(item["cinematic_prompt"]) > JIMENG25_CINEMATIC_BUDGET:
            raise ValueError(f"提示词超过预算：{shot_id}")
        if not isinstance(item["cinematic_features"], list) or len(item["cinematic_features"]) > 4:
            raise ValueError(f"电影增强项过载：{shot_id}")
        source_actions = source.get("action", []) or ["保持开始状态并完成本段剧情目标"]
        beats = item["action_beats"]
        if len(beats) != len(source_actions) or [b.get("order") for b in beats] != list(range(1, len(beats) + 1)) or any(action not in b.get("action", "") for action, b in zip(source_actions, beats)):
            raise ValueError(f"action_beats 改变了标准动作：{shot_id}")
        if item["dialogue_timing"] != [{"speaker_asset_id": d.get("speaker_asset_id"), "dialogue_type": d["dialogue_type"], "estimated_duration": d["estimated_duration"], "pause_before": d["pause_before"], "pause_after": d["pause_after"], "emotion": d.get("emotion", "")} for d in source.get("dialogue", [])]:
            raise ValueError(f"对白节奏被改变：{shot_id}")
        if item["end_frame_anchor"].get("state") != source.get("end_state"):
            raise ValueError(f"尾帧锚点改变结束状态：{shot_id}")
        combined = item["stable_prompt"] + " " + item["cinematic_prompt"]
        validate_physical_constraints(source, combined, shot_id)
        forbidden_additions = ("新增人物", "新人物", "新增道具", "新增武器", "新增爆炸", "新伤势", "改变位置", "重构场景")
        if any(term in item["cinematic_prompt"] for term in forbidden_additions):
            raise ValueError(f"cinematic_prompt 增加了剧情事实：{shot_id}")
        if source.get("camera", {}).get("movement") == "locked" and "环绕" in item["cinematic_prompt"]:
            raise ValueError(f"cinematic_prompt 改变了固定机位：{shot_id}")
        for d in source.get("dialogue", []):
            if d["dialogue_type"] == "voiceover" and not all(x in combined for x in ("不开口", "不生成口型")):
                raise ValueError(f"旁白口型约束缺失：{shot_id}")
            if d["dialogue_type"] == "character_dialogue" and (d["dialogue"] not in combined or d["speaker_asset_id"] not in combined):
                raise ValueError(f"角色对白或 speaker 缺失：{shot_id}")
        if item["cinematic_prompt"] == item["stable_prompt"] and item["cinematic_features"]:
            raise ValueError(f"电影增强项未体现在 cinematic_prompt：{shot_id}")
