"""只读连续性审计逻辑。"""

import json
from collections import defaultdict

from continuity_schema import empty_report
from model_stage_base import flatten_asset_refs


def shots_from_storyboard(storyboard: dict) -> list[dict]:
    return [shot for scene in storyboard["scenes"] for shot in scene["shots"]]


def _versions(refs: list[str]) -> dict[str, int]:
    result = {}
    for ref in refs:
        if "-V" in ref:
            base, version = ref.rsplit("-V", 1)
            try: result[base] = int(version)
            except ValueError: pass
    return result


def _issue(report: dict, category: str, severity: str, shot_id: str, description: str, evidence: str, expected: str, actual: str, fix: str, stage: str, assets=None, next_shot_id=None, auto=False) -> None:
    issue = {"issue_id": f"CONT-{len(report['issues']) + 1:03d}", "category": category, "severity": severity, "shot_id": shot_id, "asset_ids": assets or [], "description": description, "evidence": evidence, "expected": expected, "actual": actual, "suggested_fix": fix, "suggested_fix_stage": stage, "auto_fix_safe": auto}
    if next_shot_id: issue["next_shot_id"] = next_shot_id
    report["issues"].append(issue)


def _model_shots(data: dict) -> dict:
    return data.get("shots", {})


def audit_project(project: dict, storyboard: dict, registry: dict, model_outputs: dict[str, dict]) -> dict:
    report = empty_report(project)
    shots = shots_from_storyboard(storyboard)
    shot_ids = [shot["shot_id"] for shot in shots]
    previous_versions = {}
    for index, shot in enumerate(shots):
        shot_id = shot["shot_id"]
        report["shot_links"][shot_id] = {"previous": shot_ids[index - 1] if index else None, "next": shot_ids[index + 1] if index + 1 < len(shot_ids) else None}
        report["continuity_chain"].append({"shot_id": shot_id, "start_state": shot.get("start_state", {}), "end_state": shot.get("end_state", {}), "status": "compatible"})
        refs = flatten_asset_refs(shot)
        versions = _versions(refs)
        for base, version in versions.items():
            if base in previous_versions and version < previous_versions[base] and not shot.get("is_flashback"):
                _issue(report, "version", "error", shot_id, "资产版本无理由倒退", f"{base}-V{previous_versions[base]} → {base}-V{version}", "版本持续演进或明确闪回", f"{base}-V{version}", "回到 Stage 05 检查版本时间线。", "Stage 05", [base], report["shot_links"][shot_id]["previous"])
            previous_versions[base] = version
        if index:
            previous = shots[index - 1]
            previous_end, current_start = previous.get("end_state", {}), shot.get("start_state", {})
            mismatches = [(key, previous_end[key], current_start[key]) for key in previous_end.keys() & current_start.keys() if key != "compatible_with_previous" and previous_end[key] != current_start[key]]
            if current_start.get("compatible_with_previous") is False or len(mismatches) >= 2:
                _issue(report, "state_link", "error", shot_id, "镜头首尾状态断链", json.dumps(mismatches, ensure_ascii=False), "下一镜头开始状态承接上一镜头结束状态", json.dumps(current_start, ensure_ascii=False), "回到 Stage 05 修正 start_state/end_state。", "Stage 05", refs, report["shot_links"][shot_id]["previous"])
            elif mismatches:
                _issue(report, "state_link", "warning", shot_id, "镜头首尾存在轻微状态差异", json.dumps(mismatches, ensure_ascii=False), "仅允许有明确剧情依据的变化", json.dumps(current_start, ensure_ascii=False), "回到 Stage 05 核对连续性说明。", "Stage 05", refs, report["shot_links"][shot_id]["previous"])
        location = shot.get("assets", {}).get("location")
        report["asset_timelines"]["locations"].setdefault(location or "NONE", []).append({"shot_id": shot_id, "version": location, "state": shot.get("end_state", {})})
        for category, key in (("characters", "characters"), ("props", "props"), ("weapons", "weapons")):
            for ref in shot.get("assets", {}).get(key, []):
                report["asset_timelines"][category].setdefault(ref.split("-V")[0], []).append({"shot_id": shot_id, "version": ref, "state": shot.get("end_state", {})})
        text = json.dumps(shot, ensure_ascii=False)
        if any(word in text for word in ("伤", "injury", "负伤")):
            report["injury_timeline"].append({"shot_id": shot_id, "evidence": text})
        if shot.get("assets", {}).get("props"):
            report["prop_ownership_timeline"].append({"shot_id": shot_id, "props": shot["assets"]["props"], "state": shot.get("end_state", {})})
        if shot.get("assets", {}).get("weapons"):
            report["weapon_timeline"].append({"shot_id": shot_id, "weapons": shot["assets"]["weapons"], "state": shot.get("end_state", {})})
        report["time_timeline"].append({"shot_id": shot_id, "time": shot.get("start_state", {}).get("time"), "weather": shot.get("start_state", {}).get("weather")})
        for dialogue in shot.get("dialogue", []):
            if dialogue.get("dialogue_type") == "character_dialogue" and not dialogue.get("speaker_asset_id"):
                _issue(report, "dialogue", "critical", shot_id, "角色对白缺少 speaker_asset_id", json.dumps(dialogue, ensure_ascii=False), "每句对白绑定 CH 资产", "缺少 speaker", "回到 Stage 05 绑定角色对白。", "Stage 05")
    _audit_models(report, storyboard, model_outputs)
    _finish_scores(report)
    return report


def _audit_models(report: dict, storyboard: dict, model_outputs: dict[str, dict]) -> None:
    expected = {shot["shot_id"]: shot for shot in shots_from_storyboard(storyboard)}
    consistent = True
    for model_name, document in model_outputs.items():
        for shot_id, source in expected.items():
            item = _model_shots(document).get(shot_id)
            if not item:
                consistent = False
                _issue(report, "cross_model", "critical", shot_id, "模型输出缺少镜头", model_name, "四模型均覆盖镜头", "缺失", "回到对应 Stage 06—09 重新生成。", "Stage 06—09")
                continue
            for field in ("asset_refs", "dialogue", "start_state", "end_state"):
                expected_value = flatten_asset_refs(source) if field == "asset_refs" else source.get(field, [])
                if item.get(field) != expected_value:
                    consistent = False
                    _issue(report, "cross_model", "error", shot_id, f"{model_name} 的 {field} 与标准分镜不一致", model_name, json.dumps(expected_value, ensure_ascii=False), json.dumps(item.get(field), ensure_ascii=False), f"回到对应模型 Stage 重新生成，不修改 storyboard。", model_name)
            prompt = item.get("prompt", "") + " " + item.get("standard_prompt", "") + " " + item.get("stable_prompt", "") + " " + item.get("cinematic_prompt", "")
            if any(term in prompt for term in ("新增人物", "新人物", "新增道具", "新增爆炸", "新伤势")):
                consistent = False
                _issue(report, "cross_model", "error", shot_id, "模型提示词增加了未授权事实", model_name, "只保留标准分镜事实", "发现新增事实措辞", f"回到{model_name}对应适配阶段压缩提示词。", model_name)
    report["cross_model"]["consistent"] = consistent


def _finish_scores(report: dict) -> None:
    counts = defaultdict(int)
    for issue in report["issues"]:
        counts[issue["category"]] += 1
    mapping = {"character_score": "character", "prop_score": "prop", "weapon_score": "weapon", "location_score": "location", "temporal_score": "temporal", "cross_model_score": "cross_model"}
    for score, category in mapping.items():
        report["scores"][score] = max(0, 100 - counts[category] * 15)
    report["continuity_score"] = round(sum(report["scores"].values()) / len(report["scores"]))
    severities = {issue["severity"] for issue in report["issues"]}
    report["gate"] = "blocked" if "critical" in severities else "review_required" if "error" in severities else "passed"
