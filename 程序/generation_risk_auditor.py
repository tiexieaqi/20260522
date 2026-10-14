"""基于静态制作包的 AI 视频生成风险分析。"""

import json

from failure_pattern_registry import FAILURE_PATTERNS
from generation_risk_schema import empty_risk_report
from model_stage_base import flatten_asset_refs


def _issue(report, category, risk_type, severity, score, shot, model, assets, description, evidence, failure, stage, fix, auto=False):
    report["issues"].append({"issue_id": f"RISK-{len(report['issues'])+1:03d}", "category": category, "risk_type": risk_type, "severity": severity, "risk_score": score, "shot_id": shot["shot_id"], "model": model, "asset_ids": assets, "description": description, "evidence": evidence, "failure_mode": failure, "suggested_fix_stage": stage, "suggested_fix": fix, "auto_fix_safe": auto})


def audit_generation(project: dict, storyboard: dict, registry: dict, model_outputs: dict[str, dict], continuity: dict, historical: dict) -> dict:
    report = empty_risk_report(project)
    shots = [shot for scene in storyboard["scenes"] for shot in scene["shots"]]
    for shot in shots:
        assets = flatten_asset_refs(shot)
        shot_score = 0
        action_count = len(shot.get("action", []))
        if action_count >= 4 or (action_count >= 3 and len(shot.get("assets", {}).get("characters", [])) > 1):
            _issue(report, "MOTION", "ACTION_OVERLOAD", "critical" if action_count >= 6 else "error", 85, shot, "all", assets, "镜头动作数量过多", "；".join(shot.get("action", [])), "模型可能并行动作、漏动作或混合动作顺序", "Stage 05", "拆分动作或降低单镜头动作密度。"); shot_score = max(shot_score, 85)
        text = json.dumps(shot, ensure_ascii=False)
        if any(word in text for word in ("跑", "冲", "转身", "站起", "倒地", "攀爬")) and shot.get("action_complexity") in {"medium", "high"}:
            _issue(report, "MOTION", "MECHANICAL_MOVEMENT_RISK", "warning", 58, shot, "all", assets, "移动动作需要真实重心和惯性", text, "人物可能滑步、漂移或突然转向", "Stage 05", "保留启动、重心变化和收势描述。" ); shot_score = max(shot_score, 58)
        dialogue_seconds = sum(float(d.get("estimated_duration", 0)) + float(d.get("pause_before", 0)) + float(d.get("pause_after", 0)) for d in shot.get("dialogue", []))
        if dialogue_seconds > float(shot["duration_seconds"]):
            _issue(report, "DIALOGUE", "DIALOGUE_TOO_FAST", "error", 70, shot, "all", assets, "对白与镜头时长竞争", f"对白需要约{dialogue_seconds:.1f}秒，镜头{shot['duration_seconds']}秒", "模型可能吞字、加速或截断对白", "Stage 05", "增加镜头时长或拆分对白，不修改台词。" ); shot_score = max(shot_score, 70)
        if shot.get("assets", {}).get("weapons") and "枪栓" in text:
            _issue(report, "WEAPON", "WEAPON_MECHANISM_RISK", "warning", 60, shot, "all", assets, "存在武器机械结构动作", text, "模型可能错误生成枪栓状态", "Stage 05", "只保留必要的结果约束式动作。" ); shot_score = max(shot_score, 60)
        if shot.get("assets", {}).get("groups"):
            _issue(report, "GROUP", "GROUP_CLONE_RISK", "warning", 55, shot, "all", assets, "群体镜头存在复制风险", text, "人物可能同脸、同身高、同姿势", "Stage 04", "保留群体差异化约束。" ); shot_score = max(shot_score, 55)
        if shot.get("assets", {}).get("props") and any(word in text for word in ("信", "文件", "文字", "地图")):
            _issue(report, "TEXT_ARTIFACT", "TEXT_ARTIFACT_RISK", "warning", 48, shot, "all", assets, "道具可能诱发字幕或乱码", text, "模型可能生成随机文字、乱码或 logo", "Stage 04", "避免要求可读文字，交由后期处理。" ); shot_score = max(shot_score, 48)
        if shot.get("assets", {}).get("fx"):
            _issue(report, "FX", "FX_SUBJECT_OCCLUSION", "warning", 52, shot, "all", assets, "特效可能遮挡主体", text, "烟雾、暴雪或火焰可能覆盖人物和关键动作", "Stage 05", "降低特效密度并保留主体可见区域。" ); shot_score = max(shot_score, 52)
        report["shot_risks"][shot["shot_id"]] = {"generation_risk_score": shot_score, "risk_level": "critical" if shot_score >= 80 else "high" if shot_score >= 60 else "medium" if shot_score >= 40 else "low", "scores": {"character_risk": 0, "motion_risk": shot_score if action_count else 0, "dialogue_risk": 70 if dialogue_seconds > shot["duration_seconds"] else 0, "asset_risk": 0, "camera_risk": 0, "prompt_risk": 0, "fx_risk": 52 if shot.get("assets", {}).get("fx") else 0, "model_risk": 0}}
        if shot_score >= 60: report["high_risk_shots"].append(shot["shot_id"])
    # 模型专属风险以各模型 JSON 的实际字段为依据，不将模型风险混成一个结论。
    for model, output in model_outputs.items():
        report["model_risks"][model] = {"shots": {shot_id: {"risk": item.get("risk", {}), "prompt_length": len(item.get("prompt", item.get("stable_prompt", "")))} for shot_id, item in output.get("shots", {}).items()}}
        for shot in shots:
            item = output.get("shots", {}).get(shot["shot_id"], {})
            prompt = json.dumps(item, ensure_ascii=False)
            if len(prompt) > 5000:
                _issue(report, "PROMPT", "PROMPT_OVERLOAD", "warning", 55, shot, model, flatten_asset_refs(shot), "模型提示词超过保守长度预算", f"{len(prompt)} 字符", "模型可能忽略核心动作或连续性约束", "Stage 06—09", "压缩修饰词，保留资产、动作、对白和首尾状态。")
            if shot.get("dialogue") and any(d.get("dialogue_type") == "voiceover" for d in shot["dialogue"]):
                if "不开口" not in prompt and "口型" not in prompt:
                    _issue(report, "LIPSYNC", "VOICEOVER_LIPSYNC_RISK", "warning", 50, shot, model, flatten_asset_refs(shot), "旁白提示缺少不开口约束", prompt, "画面人物可能错误生成旁白口型", "Stage 06—09", "明确旁白仅供后期配音，人物不开口。")
            if any(token in prompt for token in ("新增爆炸", "新增人物", "新增道具", "新伤势")):
                _issue(report, "MODEL", "MODEL_FACT_DRIFT_RISK", "error", 75, shot, model, flatten_asset_refs(shot), "模型提示词出现标准分镜之外的新事实", prompt, "模型可能生成未经母版允许的剧情、资产或伤势", "Stage 06—09", "回到对应模型适配阶段删除新增事实。")
            if "枪栓" in prompt and any(token in prompt for token in ("成功拉动", "拉开枪栓")):
                _issue(report, "PHYSICS", "PHYSICS_STATE_CONFLICT", "error", 78, shot, model, flatten_asset_refs(shot), "武器状态描述可能与锁定状态冲突", prompt, "冻结枪栓可能被模型错误生成可拉开", "Stage 05", "使用结果约束式描述，明确枪栓完全不移动。")
    report["failure_patterns"] = [dict(pattern_id=key, **value) for key, value in FAILURE_PATTERNS.items() if any(value["risk_type"] == issue["risk_type"] for issue in report["issues"])]
    if historical.get("requires_external_verification"):
        report["requires_real_generation_test"].append("历史视觉随机化需真实模型生成后确认")
        _issue(report, "MODEL", "HISTORICAL_VISUAL_RANDOMIZATION_RISK", "warning", 45, shots[0], "all", flatten_asset_refs(shots[0]), "历史事实缺少外部核验，视觉生成可能自行补全", "Stage 11 存在 requires_external_verification", "模型可能生成未经确认的年代、制服或装备细节", "Stage 11", "先补充可靠史料或明确艺术加工。" )
    severity = {issue["severity"] for issue in report["issues"]}
    report["overall_risk_score"] = min(100, round(sum(item["risk_score"] for item in report["issues"]) / max(1, len(shots))))
    report["scores"] = {key: round(sum(item["scores"].get(key, 0) for item in report["shot_risks"].values()) / max(1, len(shots))) for key in ("character_risk", "motion_risk", "dialogue_risk", "asset_risk", "camera_risk", "prompt_risk", "fx_risk", "model_risk")}
    report["risk_level"] = "critical" if "critical" in severity else "high" if report["overall_risk_score"] >= 60 else "medium" if report["overall_risk_score"] >= 30 else "low"
    report["generation_gate"] = "blocked" if "critical" in severity else "review_required" if severity & {"error", "warning"} else "passed"
    for shot_id in report["shot_risks"]:
        report["recommended_models"][shot_id] = {"recommended_model": "any", "recommendation_reason": "当前规则不足以证明某一模型绝对更优；按镜头风险人工选择。", "recommended_prompt_mode": "stable" if report["shot_risks"][shot_id]["generation_risk_score"] >= 60 else "cinematic"}
    report["final_pipeline_status"] = "blocked" if report["generation_gate"] == "blocked" or continuity.get("gate") == "blocked" or historical.get("historical_gate") == "blocked" else "review_required" if report["generation_gate"] == "review_required" or continuity.get("gate") == "review_required" or historical.get("historical_gate") == "review_required" else "ready"
    return report
