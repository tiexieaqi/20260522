"""Seedance 2.0 校验兼容入口。"""

from model_prompt_validator import storyboard_shots, validate_model_plan


def validate_seedance_plan(plan: dict, storyboard: dict, registry: dict, asset_prompts: dict) -> None:
    validate_model_plan(plan, storyboard, registry, asset_prompts, model="seedance-2.0", prompt_budget=3000, required_shot_fields=("timeline",))
    for shot_id, item in plan["shots"].items():
        if not isinstance(item["timeline"], list) or not item["timeline"]:
            raise ValueError(f"缺少动作时间线：{shot_id}")
