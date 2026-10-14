"""Stage 06 离线测试：Seedance 2.0 适配、母版保护、引用和幂等。"""

import copy
import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

from offline_test_stage05 import StoryboardProvider, prepare
from seedance20_adapter import Seedance20Adapter
from seedance_prompt_validator import storyboard_shots
from stage06_manager import run_stage06


def make_plan(project: Path, mutate: str | None = None) -> dict:
    project_data = json.loads((project / "project.json").read_text(encoding="utf-8"))
    storyboard = json.loads((project / "storyboard.json").read_text(encoding="utf-8"))
    adapter = Seedance20Adapter()
    shots = {}
    for shot_id, source in storyboard_shots(storyboard).items():
        assets = source["assets"]
        refs = list(assets.get("characters", []))
        if assets.get("location"): refs.append(assets["location"])
        for key in ("props", "weapons", "groups", "fx"): refs.extend(assets.get(key, []))
        level, reasons = adapter.assess_risk(source)
        shots[shot_id] = {
            "source_shot_id": shot_id,
            "duration_seconds": source["duration_seconds"],
            "asset_refs": refs,
            "prompt": adapter.build_prompt(source, {}),
            "timeline": [f"按顺序完成：{action}" for action in source.get("action", [])] or ["保持开始状态"],
            "dialogue": copy.deepcopy(source.get("dialogue", [])),
            "start_state": copy.deepcopy(source["start_state"]),
            "end_state": copy.deepcopy(source["end_state"]),
            "forbidden": copy.deepcopy(source["forbidden"]),
            "risk": {"level": level, "reasons": reasons},
            "model_duration_status": "warning" if source["duration_seconds"] > 10 else "compatible",
            "source_rules": copy.deepcopy(source.get("continuity_notes", [])),
        }
    if mutate == "dialogue":
        first = next(iter(shots.values()))
        first["dialogue"][0]["dialogue"] = "被篡改的台词"
    if mutate == "unknown_shot":
        shots["S99_SH99"] = copy.deepcopy(next(iter(shots.values())))
        shots["S99_SH99"]["source_shot_id"] = "S99_SH99"
    return {"schema_version": "1.0", "model": "seedance-2.0", "project_id": project_data["project_id"], "project_name": project_data["project_name"], "shots": shots}


class Provider:
    def __init__(self, mutate=None): self.mutate = mutate
    def complete(self, prompt, schema=None):
        # 测试项目名称和目录名一致，先用已准备的 fixture 生成计划。
        return json.dumps(make_plan(CURRENT_PROJECT, self.mutate), ensure_ascii=False)


CURRENT_PROJECT: Path


def main() -> int:
    global CURRENT_PROJECT
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage06_") as temp:
        root = Path(temp)
        CURRENT_PROJECT = prepare(root)
        from stage05_manager import run_stage05
        run_stage05(CURRENT_PROJECT, StoryboardProvider())
        protected_names = ("00_原始剧本.txt", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "assets.json", "asset_prompts.json", "storyboard.json")
        protected = {name: (CURRENT_PROJECT / name).read_bytes() for name in protected_names}
        run_stage06(CURRENT_PROJECT, Provider())
        plan_bytes = (CURRENT_PROJECT / "seedance20_prompts.json").read_bytes()
        plan = json.loads(plan_bytes.decode("utf-8"))
        storyboard = json.loads((CURRENT_PROJECT / "storyboard.json").read_text(encoding="utf-8"))
        assert set(plan["shots"]) == set(storyboard_shots(storyboard))
        assert all(item["prompt"] and item["asset_refs"] for item in plan["shots"].values())
        assert "后期旁白参考" in plan["shots"]["S01_SH02"]["prompt"]
        assert "枪栓完全没有发生位移" in plan["shots"]["S02_SH01"]["prompt"]
        assert plan["shots"]["S02_SH01"]["risk"]["level"] == "high"
        assert all((CURRENT_PROJECT / name).read_bytes() == value for name, value in protected.items())
        run_stage06(CURRENT_PROJECT, Provider())
        assert plan_bytes == (CURRENT_PROJECT / "seedance20_prompts.json").read_bytes()
        report_before = (CURRENT_PROJECT / "06_Seedance2.0提示词.md").read_bytes()
        for mutate in ("dialogue", "unknown_shot"):
            try: run_stage06(CURRENT_PROJECT, Provider(mutate))
            except Exception: pass
            else: raise AssertionError(f"非法 Seedance 输出未失败：{mutate}")
            assert report_before == (CURRENT_PROJECT / "06_Seedance2.0提示词.md").read_bytes()
            assert plan_bytes == (CURRENT_PROJECT / "seedance20_prompts.json").read_bytes()
            assert all((CURRENT_PROJECT / name).read_bytes() == value for name, value in protected.items())
        state = json.loads((CURRENT_PROJECT / "workflow_state.json").read_text(encoding="utf-8"))
        assert state["stages"]["6"]["status"] == "failed"
    print("offline_test_stage06：全部通过")
    return 0


if __name__ == "__main__": raise SystemExit(main())
