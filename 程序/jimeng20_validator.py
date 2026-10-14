"""即梦 2.0 专属字段和物理状态校验。"""

from model_prompt_validator import validate_model_plan
from jimeng20_adapter import JIMENG20_PROMPT_BUDGET


def validate_physical_constraints(source: dict, combined: str, shot_id: str) -> None:
    source_text = " ".join(source.get("action", [])) + " " + str(source.get("end_state", {}))
    checks = [
        (("枪栓" in source_text and any(word in source_text for word in ("冻", "卡死", "没有移动", "不动"))), "完全没有移动", "枪栓冻结"),
        (("门" in source_text and any(word in source_text for word in ("打不开", "锁住", "上锁"))), "完全打不开", "门锁"),
        ((any(word in source_text for word in ("冻僵", "冻死"))), "不突然恢复自然动作", "冻僵人物"),
        ((any(word in source_text for word in ("死亡", "已死"))), "不自行移动或开口", "死亡人物"),
        ((any(word in source_text for word in ("烧毁", "烧焦"))), "不恢复完整", "烧毁道具"),
        ((any(word in source_text for word in ("固定", "无法移动", "不能移动"))), "不发生位移", "固定物体"),
        ((any(word in source_text for word in ("伤势", "负伤", "受伤")) or "injury" in source_text), "伤势持续保持", "伤势连续"),
    ]
    for applies, required, label in checks:
        if applies and required not in combined:
            raise ValueError(f"{label}物理约束缺失：{shot_id}")


def validate_jimeng20_plan(plan: dict, storyboard: dict, registry: dict, asset_prompts: dict) -> None:
    required = ("adapter_profile", "standard_prompt", "stable_prompt", "end_frame_anchor", "prompt_mode", "jimeng20_risk", "risk_reasons", "jimeng20_prompt_budget")
    validate_model_plan(plan, storyboard, registry, asset_prompts, model="jimeng-2.0", prompt_budget=JIMENG20_PROMPT_BUDGET, required_shot_fields=required)
    expected = {shot["shot_id"]: shot for scene in storyboard["scenes"] for shot in scene["shots"]}
    for shot_id, item in plan["shots"].items():
        source = expected[shot_id]
        if item.get("adapter_profile") != "jimeng-2.0":
            raise ValueError(f"即梦 2.0 adapter_profile 无效：{shot_id}")
        if item.get("jimeng20_prompt_budget") != JIMENG20_PROMPT_BUDGET:
            raise ValueError(f"即梦 2.0 Prompt 预算无效：{shot_id}")
        if item.get("prompt_mode") not in {"standard", "stable_short"}:
            raise ValueError(f"即梦 2.0 prompt_mode 无效：{shot_id}")
        if item.get("jimeng20_risk") not in {"low", "medium", "high"} or not isinstance(item.get("risk_reasons"), list):
            raise ValueError(f"即梦 2.0 风险字段无效：{shot_id}")
        if item.get("risk") != {"level": item["jimeng20_risk"], "reasons": item["risk_reasons"]}:
            raise ValueError(f"公共风险字段与即梦风险字段不一致：{shot_id}")
        if item["jimeng20_risk"] == "high" and item["prompt_mode"] != "stable_short":
            raise ValueError(f"高风险镜头必须使用 stable_short：{shot_id}")
        if not isinstance(item["end_frame_anchor"], dict) or item["end_frame_anchor"].get("state") != source.get("end_state"):
            raise ValueError(f"end_frame_anchor 改变了结束状态：{shot_id}")
        if not isinstance(item["stable_prompt"], str) or not item["stable_prompt"].strip():
            raise ValueError(f"stable_prompt 为空：{shot_id}")
        if not isinstance(item["standard_prompt"], str) or not item["standard_prompt"].strip() or len(item["standard_prompt"]) > JIMENG20_PROMPT_BUDGET or len(item["stable_prompt"]) > JIMENG20_PROMPT_BUDGET:
            raise ValueError(f"即梦提示词为空或超过预算：{shot_id}")
        for dialogue in source.get("dialogue", []):
            if dialogue["dialogue_type"] == "voiceover" and not all(term in item["standard_prompt"] + item["stable_prompt"] for term in ("不开口", "不生成对应口型")):
                raise ValueError(f"旁白口型约束缺失：{shot_id}")
            if dialogue["dialogue_type"] == "character_dialogue" and (dialogue["speaker_asset_id"] not in item["standard_prompt"] or dialogue["dialogue"] not in item["standard_prompt"]):
                raise ValueError(f"角色对白提示缺少 speaker 或原文：{shot_id}")
        if item["jimeng20_risk"] == "high" and "JIMENG20_ADAPTATION_WARNING" not in item.get("warnings", []):
            raise ValueError(f"高风险镜头缺少适配警告：{shot_id}")
        combined = item["standard_prompt"] + " " + item["stable_prompt"]
        validate_physical_constraints(source, combined, shot_id)
        dialogue_total = sum(float(item.get("estimated_duration", 0)) + float(item.get("pause_before", 0)) + float(item.get("pause_after", 0)) for item in source.get("dialogue", []))
        if dialogue_total > float(source["duration_seconds"]):
            if "DIALOGUE_DURATION_WARNING" not in item.get("warnings", []):
                raise ValueError(f"对白时长不足但未标记警告：{shot_id}")
