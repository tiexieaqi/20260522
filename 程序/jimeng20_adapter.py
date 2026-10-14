"""即梦 2.0 的短稳提示词适配器。"""

from model_adapter_base import ModelAdapter
from model_stage_base import flatten_asset_refs


JIMENG20_PROMPT_BUDGET = 2800


class Jimeng20Adapter(ModelAdapter):
    model_name = "jimeng-2.0"

    def assess_risk(self, shot: dict) -> tuple[str, list[str]]:
        assets = shot.get("assets", {})
        reasons = []
        if shot.get("action_complexity") == "high": reasons.append("高复杂度动作")
        if len(assets.get("characters", [])) > 1: reasons.append("多人位置")
        if assets.get("weapons"): reasons.append("武器操作或物理状态")
        if assets.get("groups"): reasons.append("群体差异化")
        if assets.get("fx"): reasons.append("环境特效")
        if len(shot.get("dialogue", [])) > 1: reasons.append("多段对白")
        if shot.get("camera", {}).get("movement") in {"tracking", "handheld", "arc"}: reasons.append("移动运镜")
        if len(reasons) >= 3 or shot.get("action_complexity") == "high": return "high", reasons
        if reasons: return "medium", reasons
        return "low", []

    def _physical_constraints(self, shot: dict) -> list[str]:
        text = " ".join(shot.get("action", [])) + " " + str(shot.get("end_state", {}))
        constraints = []
        if "枪栓" in text and any(word in text for word in ("冻", "卡死", "没有移动", "不动")):
            constraints.append("尝试后拉枪栓，但枪栓完全没有移动，始终保持原位置")
        if "门" in text and any(word in text for word in ("打不开", "锁住", "上锁")):
            constraints.append("尝试推门，但门完全打不开，保持关闭状态")
        if any(word in text for word in ("冻僵", "冻死")):
            constraints.append("人物保持既定僵硬状态，不突然恢复自然动作")
        if any(word in text for word in ("烧毁", "烧焦")):
            constraints.append("道具保持烧毁状态，不恢复完整")
        if any(word in text for word in ("死亡", "已死")):
            constraints.append("人物保持死亡状态，不自行移动或开口")
        if any(word in text for word in ("固定", "无法移动", "不能移动")):
            constraints.append("物体保持固定位置，不发生位移")
        if any(word in text for word in ("伤势", "负伤", "受伤")) or "injury" in text:
            constraints.append("人物伤势持续保持，不无故恢复")
        return constraints

    def end_frame_anchor(self, shot: dict) -> dict:
        end_state = shot.get("end_state", {})
        return {
            "state": end_state,
            "blocking": shot.get("blocking", {}),
            "camera": shot.get("camera", {}).get("movement", "locked"),
        }

    def _dialogue_lines(self, shot: dict) -> list[str]:
        lines = []
        for dialogue in shot.get("dialogue", []):
            if dialogue["dialogue_type"] == "voiceover":
                lines.append(f"后期旁白参考：{dialogue['dialogue']}。画面人物保持自然表演，不开口，不生成对应口型")
            elif dialogue["dialogue_type"] == "character_dialogue":
                lines.append(f"{dialogue['speaker_asset_id']}本人逐字完整说出：{dialogue['dialogue']}，保留停顿，口型自然同步")
        return lines

    def _movement_guidance(self, shot: dict) -> str | None:
        text = " ".join(shot.get("action", []))
        if any(word in text for word in ("走", "跑", "冲", "转身", "站起", "跪下", "倒地", "攀爬", "跨越", "移动")):
            return "移动自然启动，重心先变化，脚步与身体同步，停止时保留惯性收势；禁止滑步、漂移、机械匀速和突然转向"
        return None

    def build_prompt(self, shot: dict, context: dict) -> str:
        refs = flatten_asset_refs(shot)
        camera = shot.get("camera", {})
        actions = shot.get("action", []) or ["保持开始状态，完成本段剧情目标"]
        movement = self._movement_guidance(shot)
        lines = [
            "强制禁止：" + "、".join(shot.get("forbidden", [])),
            "本段引用资产：" + "、".join(refs),
            f"开始状态：{shot.get('start_state', {})}",
            f"{camera.get('shot_size', '')}，{camera.get('focal_length', '')}，{camera.get('height', '')}机位，{camera.get('angle', '')}，{camera.get('movement', '')}。",
            "动作：" + "；".join(actions),
            *([movement] if movement else []),
            *self._physical_constraints(shot),
            *self._dialogue_lines(shot),
            "结束状态：" + str(shot.get("end_state", {})),
            "保持人物、空间、道具和武器连续，不添加额外动作或镜头。",
        ]
        return "\n".join(lines)

    def build_stable_prompt(self, shot: dict, context: dict) -> str:
        refs = flatten_asset_refs(shot)
        actions = shot.get("action", []) or ["保持开始状态，完成本段剧情目标"]
        dialogue = self._dialogue_lines(shot)
        constraints = self._physical_constraints(shot)
        movement = self._movement_guidance(shot)
        return "\n".join([
            "强制禁止：" + "、".join(shot.get("forbidden", [])),
            "资产：" + "、".join(refs),
            "核心动作：" + "；".join(actions),
            *([movement] if movement else []),
            *constraints,
            *dialogue,
            "结束状态：" + str(shot.get("end_state", {})),
        ])
