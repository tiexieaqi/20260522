"""Seedance 2.0 的提示词组织器；只转换镜头，不改写分镜母版。"""

from model_adapter_base import ModelAdapter


class Seedance20Adapter(ModelAdapter):
    model_name = "seedance-2.0"

    def build_prompt(self, shot: dict, context: dict) -> str:
        assets = shot.get("assets", {})
        refs = []
        refs.extend(assets.get("characters", []))
        if assets.get("location"):
            refs.append(assets["location"])
        for key in ("props", "weapons", "groups", "fx"):
            refs.extend(assets.get(key, []))
        camera = shot.get("camera", {})
        timeline = []
        actions = shot.get("action", [])
        duration = float(shot["duration_seconds"])
        if actions:
            slice_seconds = duration / len(actions)
            for index, action in enumerate(actions):
                start = round(index * slice_seconds, 1)
                end = round(duration if index == len(actions) - 1 else (index + 1) * slice_seconds, 1)
                timeline.append(f"{start:g}-{end:g}秒：{action}")
                if "枪栓" in action and any(word in action for word in ("冻", "冻结", "卡死", "没有移动", "不动")):
                    timeline[-1] += "；枪栓完全没有发生位移。"
        else:
            timeline.append(f"0-{duration:g}秒：保持开始状态并完成本段剧情目标。")
        lines = [
            "真人影视风格，按以下顺序完成一个连续视频段。",
            f"本段资产：{'、'.join(refs)}。严格保持资产 ID 对应的演员、空间和物件，不重新设计。",
            f"剧情目标：{shot.get('story_goal', '')}",
            f"开始状态：{shot.get('start_state', {})}",
            f"摄影：{camera.get('shot_size', '')}，{camera.get('focal_length', '')}，{camera.get('height', '')}，{camera.get('angle', '')}，{camera.get('position', '')}，主要运镜 {camera.get('movement', '')}。",
            *timeline,
        ]
        for dialogue in shot.get("dialogue", []):
            if dialogue.get("dialogue_type") == "voiceover":
                lines.append(f"后期旁白参考（约{dialogue['estimated_duration']}秒）：{dialogue.get('dialogue', '')}。画面人物不开口，不生成对应口型。")
            elif dialogue.get("dialogue_type") == "character_dialogue":
                lines.append(f"{dialogue['speaker_asset_id']}本人完整说出：{dialogue.get('dialogue', '')}；自然语速，保留停顿和尾音，口型同步。")
        if shot.get("performance_direction"):
            lines.append("表演：" + "；".join(shot["performance_direction"]) + "。")
        lines.append(f"结束状态：{shot.get('end_state', {})}。最后保持姿势和摄影状态稳定。")
        lines.append("连续性：" + "；".join(shot.get("continuity_notes", [])) + "。")
        lines.append("禁止：" + "、".join(shot.get("forbidden", [])) + "。")
        return "\n".join(lines)

    def assess_risk(self, shot: dict) -> tuple[str, list[str]]:
        reasons = []
        if shot.get("action_complexity") == "high":
            reasons.append("动作复杂度高")
        if len(shot.get("assets", {}).get("characters", [])) > 1:
            reasons.append("多人位置和动作需要保持")
        if shot.get("assets", {}).get("groups"):
            reasons.append("包含群体差异化控制")
        if shot.get("assets", {}).get("weapons"):
            reasons.append("包含武器状态或操作")
        if len(shot.get("dialogue", [])) > 1:
            reasons.append("同段包含多条对白或旁白")
        if shot.get("camera", {}).get("movement") in {"handheld", "tracking", "arc"}:
            reasons.append("摄影机存在明显运动")
        if len(reasons) >= 3 or shot.get("action_complexity") == "high":
            return "high", reasons
        if reasons:
            return "medium", reasons
        return "low", []
