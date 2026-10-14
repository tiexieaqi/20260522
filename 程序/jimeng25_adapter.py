"""即梦 2.5 平行适配器：稳定版与电影增强版共享同一事实来源。"""

from model_adapter_base import ModelAdapter
from model_stage_base import flatten_asset_refs


JIMENG25_STABLE_BUDGET = 2600
JIMENG25_CINEMATIC_BUDGET = 3400


class Jimeng25Adapter(ModelAdapter):
    model_name = "jimeng-2.5"

    def build_prompt(self, shot: dict, context: dict) -> str:
        return self.build_stable_prompt(shot, context)

    def assess_risk(self, shot: dict) -> tuple[str, list[str]]:
        assets = shot.get("assets", {})
        reasons = []
        if shot.get("action_complexity") == "high": reasons.append("高复杂度动作")
        if len(assets.get("characters", [])) > 1: reasons.append("多人站位")
        if assets.get("weapons"): reasons.append("武器物理状态")
        if assets.get("groups"): reasons.append("群体差异化")
        if assets.get("fx"): reasons.append("环境事件")
        if len(shot.get("dialogue", [])) > 1: reasons.append("多段对白")
        if shot.get("camera", {}).get("movement") in {"tracking", "handheld", "arc"}: reasons.append("运动摄影")
        if len(reasons) >= 3 or shot.get("action_complexity") == "high": return "high", reasons
        if reasons: return "medium", reasons
        return "low", []

    def action_beats(self, shot: dict) -> list[dict]:
        actions = shot.get("action", []) or ["保持开始状态并完成本段剧情目标"]
        duration = float(shot["duration_seconds"])
        each = duration / len(actions)
        beats = []
        for order, action in enumerate(actions, 1):
            text = action
            if "枪栓" in text and any(word in text for word in ("冻", "卡死", "没有移动", "不动")):
                text += "；枪栓完全没有移动，始终保持原位置"
            beats.append({"order": order, "action": text, "duration_hint": round(each, 1)})
        return beats

    def performance_beats(self, shot: dict) -> list[str]:
        return list(shot.get("performance_direction", [])[:3])

    def dialogue_timing(self, shot: dict) -> list[dict]:
        return [{"speaker_asset_id": d.get("speaker_asset_id"), "dialogue_type": d["dialogue_type"], "estimated_duration": d["estimated_duration"], "pause_before": d["pause_before"], "pause_after": d["pause_after"], "emotion": d.get("emotion", "")} for d in shot.get("dialogue", [])]

    def end_frame_anchor(self, shot: dict) -> dict:
        return {"state": shot.get("end_state", {}), "blocking": shot.get("blocking", {}), "camera": shot.get("camera", {}).get("movement", "locked")}

    def _physical_constraints(self, shot: dict) -> list[str]:
        text = " ".join(shot.get("action", [])) + " " + str(shot.get("end_state", {}))
        constraints = []
        if "枪栓" in text and any(word in text for word in ("冻", "卡死", "没有移动", "不动")):
            constraints.append("枪栓完全没有移动，始终保持原位置")
        if "门" in text and any(word in text for word in ("打不开", "锁住", "上锁")):
            constraints.append("门完全打不开，保持关闭状态")
        if any(word in text for word in ("冻僵", "冻死")):
            constraints.append("人物不突然恢复自然动作")
        if any(word in text for word in ("死亡", "已死")):
            constraints.append("人物不自行移动或开口")
        if any(word in text for word in ("烧毁", "烧焦")):
            constraints.append("道具不恢复完整")
        if any(word in text for word in ("固定", "无法移动", "不能移动")):
            constraints.append("物体保持固定位置，不发生位移")
        if any(word in text for word in ("伤势", "负伤", "受伤")) or "injury" in text:
            constraints.append("伤势持续保持，不无故恢复")
        return constraints

    def cinematic_features(self, shot: dict) -> list[str]:
        camera = shot.get("camera", {})
        features = []
        if camera.get("shot_size") in {"close", "extreme_close", "medium_close"} and camera.get("focal_length") in {"85mm", "100mm"}:
            features.append("shallow_depth_of_field")
        if camera.get("movement") == "handheld": features.append("subtle_handheld")
        if shot.get("performance_direction"): features.append("performance_pause")
        if shot.get("assets", {}).get("fx") or shot.get("assets", {}).get("groups"): features.append("environmental_depth")
        if camera.get("movement") in {"tracking", "follow"}: features.append("natural_motion_blur")
        return features[:4]

    def build_stable_prompt(self, shot: dict, context: dict) -> str:
        refs = flatten_asset_refs(shot)
        camera = shot.get("camera", {})
        dialogues = []
        for d in shot.get("dialogue", []):
            if d["dialogue_type"] == "voiceover": dialogues.append(f"后期旁白：{d['dialogue']}，画面人物不开口，不生成口型")
            else: dialogues.append(f"{d['speaker_asset_id']}本人逐字完整说出：{d['dialogue']}，自然口型和停顿")
        return "\n".join([
            "强制禁止：" + "、".join(shot.get("forbidden", [])),
            "锁定资产：" + "、".join(refs),
            "开始状态：" + str(shot.get("start_state", {})),
            "核心动作：" + "；".join(beat["action"] for beat in self.action_beats(shot)),
            *self._physical_constraints(shot),
            *dialogues,
            f"镜头：{camera.get('shot_size', '')}，{camera.get('focal_length', '')}，{camera.get('height', '')}，{camera.get('angle', '')}，主要运镜 {camera.get('movement', '')}",
            "结束状态：" + str(shot.get("end_state", {})),
            "保持人物、空间、武器、道具和时间天气连续，不增加动作。",
        ])

    def build_cinematic_prompt(self, shot: dict, context: dict) -> str:
        stable = self.build_stable_prompt(shot, context)
        features = self.cinematic_features(shot)
        additions = {
            "shallow_depth_of_field": "依据焦段使用自然浅景深，主体清晰，空间关系仍可辨认",
            "subtle_handheld": "只保留轻微真实手持感，不剧烈抖动",
            "performance_pause": "保留呼吸、停顿和细小反应，动作完成后自然收势",
            "environmental_depth": "前景、主体、后景形成真实空间层次，不新增大型物体",
            "natural_motion_blur": "运动产生自然轻微动态模糊，不改变动作结果",
        }
        if features:
            stable += "\n电影增强（仅视觉表达）：" + "；".join(additions[x] for x in features[:4]) + "。"
        return stable

    def recommended_mode(self, risk: str) -> tuple[str, str]:
        if risk == "low": return "cinematic", "风险低，允许有限电影视觉增强"
        if risk == "medium": return "stable", "风险中等，稳定性优先，同时保留电影版供选择"
        return "stable", "风险高，优先降低提示歧义和动作冲突"
