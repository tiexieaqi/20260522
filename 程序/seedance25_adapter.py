"""Seedance 2.5 差异化适配：动作节拍、表演节奏和主次关系。"""

from model_adapter_base import ModelAdapter
from model_stage_base import flatten_asset_refs


MODEL_PROMPT_BUDGET = 3600
ADAPTATION_STRATEGIES = {"direct", "simplified_timing", "emphasis_order", "requires_review"}


class Seedance25Adapter(ModelAdapter):
    model_name = "seedance-2.5"

    def action_beats(self, shot: dict) -> list[dict]:
        actions = shot.get("action", []) or ["保持开始状态，完成剧情目标"]
        duration = float(shot["duration_seconds"])
        per_action = duration / len(actions)
        beats = []
        for index, action in enumerate(actions, 1):
            text = action
            if "枪栓" in text and any(word in text for word in ("冻", "卡死", "没有移动", "不动")):
                text += "；尝试后枪栓完全没有发生位移"
            beats.append({"order": index, "action": text, "duration_hint": round(per_action, 1)})
        return beats

    def performance_timing(self, shot: dict) -> list[dict]:
        return [{"order": index, "direction": direction, "timing": "配合相邻动作自然发生"} for index, direction in enumerate(shot.get("performance_direction", [])[:3], 1)]

    def dialogue_timing(self, shot: dict) -> list[dict]:
        return [{"speaker_asset_id": item.get("speaker_asset_id"), "dialogue_type": item["dialogue_type"], "estimated_duration": item["estimated_duration"], "pause_before": item["pause_before"], "pause_after": item["pause_after"]} for item in shot.get("dialogue", [])]

    def adaptation_strategy(self, shot: dict) -> str:
        if shot.get("action_complexity") == "high":
            return "emphasis_order"
        if len(shot.get("action", [])) > 2:
            return "simplified_timing"
        return "direct"

    def build_prompt(self, shot: dict, context: dict) -> str:
        refs = flatten_asset_refs(shot)
        camera = shot.get("camera", {})
        beats = self.action_beats(shot)
        lines = [
            f"当前资产：{'、'.join(refs)}。严格保持已锁定人物、空间、道具及版本状态，不重新设计。",
            f"开始状态：{shot['start_state']}。",
            "动作链：" + " → ".join(beat["action"] for beat in beats) + "。",
        ]
        for dialogue in shot.get("dialogue", []):
            if dialogue["dialogue_type"] == "voiceover":
                lines.append(f"后期旁白参考：{dialogue['dialogue']}。画面人物不开口，不生成旁白口型。")
            elif dialogue["dialogue_type"] == "character_dialogue":
                lines.append(f"{dialogue['speaker_asset_id']}本人逐字完整说出：{dialogue['dialogue']}；按原定停顿自然说完，口型准确。")
        if self.performance_timing(shot):
            lines.append("人物表演：" + "；".join(item["direction"] for item in self.performance_timing(shot)) + "。")
        lines.append(f"摄影保持：{camera.get('shot_size', '')}，{camera.get('focal_length', '')}，{camera.get('height', '')}，{camera.get('angle', '')}，{camera.get('position', '')}，只执行主要运镜 {camera.get('movement', '')}。")
        if shot.get("assets", {}).get("groups"):
            lines.append("群体保持同一身份体系，个体脸型、身高、步幅和姿势有差异，禁止机械同步和复制感。")
        lines.append(f"结束状态：{shot['end_state']}。动作完成后自然落定，保持空间和资产连续。")
        lines.append("禁止：" + "、".join(shot["forbidden"]) + "。")
        return "\n".join(lines)

    def assess_risk(self, shot: dict) -> tuple[str, list[str]]:
        reasons = []
        assets = shot.get("assets", {})
        if shot.get("action_complexity") == "high": reasons.append("高复杂度动作链")
        if len(assets.get("characters", [])) > 1: reasons.append("多人站位与表演")
        if assets.get("groups"): reasons.append("群体差异化")
        if assets.get("weapons"): reasons.append("武器物理状态")
        if assets.get("fx"): reasons.append("环境特效")
        if len(shot.get("dialogue", [])) > 1: reasons.append("多段对白节奏")
        if shot.get("camera", {}).get("movement") in {"tracking", "handheld", "arc"}: reasons.append("运动摄影")
        if len(reasons) >= 3 or shot.get("action_complexity") == "high": return "high", reasons
        if reasons: return "medium", reasons
        return "low", []
