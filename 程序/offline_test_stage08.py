"""Stage 08 离线测试：即梦 2.0、短稳版、物理约束和母版保护。"""

import copy
import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

import offline_test_stage06 as stage06_fixture
import offline_test_stage07 as stage07_fixture
from offline_test_stage05 import StoryboardProvider, prepare
from jimeng20_adapter import JIMENG20_PROMPT_BUDGET, Jimeng20Adapter
from jimeng20_validator import validate_physical_constraints
from model_stage_base import flatten_asset_refs
from model_prompt_validator import storyboard_shots
from stage05_manager import run_stage05
from stage06_manager import run_stage06
from stage07_manager import run_stage07
from stage08_manager import run_stage08


CURRENT_PROJECT: Path
SENTINEL = "禁止把 Seedance 内容作为即梦母版"


def make_plan(project: Path, mutate: str | None = None) -> dict:
    data = json.loads((project / "project.json").read_text(encoding="utf-8"))
    storyboard = json.loads((project / "storyboard.json").read_text(encoding="utf-8"))
    adapter = Jimeng20Adapter()
    shots = {}
    for shot_id, source in storyboard_shots(storyboard).items():
        level, reasons = adapter.assess_risk(source)
        standard = adapter.build_prompt(source, {})
        stable = adapter.build_stable_prompt(source, {})
        dialogue_total = sum(float(d["estimated_duration"]) + float(d["pause_before"]) + float(d["pause_after"]) for d in source.get("dialogue", []))
        warnings = ["DIALOGUE_DURATION_WARNING"] if dialogue_total > float(source["duration_seconds"]) else []
        if level == "high": warnings.append("JIMENG20_ADAPTATION_WARNING")
        shots[shot_id] = {
            "source_shot_id": shot_id,
            "duration_seconds": source["duration_seconds"],
            "asset_refs": flatten_asset_refs(source),
            "prompt": standard,
            "adapter_profile": "jimeng-2.0",
            "standard_prompt": standard,
            "stable_prompt": stable,
            "prompt_mode": "stable_short" if level == "high" else "standard",
            "end_frame_anchor": adapter.end_frame_anchor(source),
            "dialogue": copy.deepcopy(source.get("dialogue", [])),
            "start_state": copy.deepcopy(source["start_state"]),
            "end_state": copy.deepcopy(source["end_state"]),
            "forbidden": copy.deepcopy(source["forbidden"]),
            "risk": {"level": level, "reasons": reasons},
            "jimeng20_risk": level,
            "risk_reasons": reasons,
            "jimeng20_prompt_budget": JIMENG20_PROMPT_BUDGET,
            "model_duration_status": "warning" if warnings else "compatible",
            "source_rules": copy.deepcopy(source.get("continuity_notes", [])),
            "warnings": warnings,
        }
    if mutate == "state": shots["S01_SH01"]["end_frame_anchor"]["state"] = {"错误": True}
    if mutate == "physical":
        shots["S02_SH01"]["stable_prompt"] = shots["S02_SH01"]["stable_prompt"].replace("完全没有移动", "成功拉动")
        shots["S02_SH01"]["standard_prompt"] = shots["S02_SH01"]["standard_prompt"].replace("完全没有移动", "成功拉动")
        shots["S02_SH01"]["prompt"] = shots["S02_SH01"]["prompt"].replace("完全没有移动", "成功拉动")
    if mutate == "asset": shots["S01_SH01"]["asset_refs"][0] = "CH-999-V01"
    return {"schema_version": "1.0", "model": "jimeng-2.0", "project_id": data["project_id"], "project_name": data["project_name"], "shots": shots}


class Provider:
    def __init__(self, mutate=None): self.mutate = mutate
    def complete(self, prompt, schema=None):
        assert SENTINEL not in prompt
        return json.dumps(make_plan(CURRENT_PROJECT, self.mutate), ensure_ascii=False)


def main() -> int:
    global CURRENT_PROJECT
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage08_") as temp:
        root = Path(temp)
        CURRENT_PROJECT = prepare(root)
        run_stage05(CURRENT_PROJECT, StoryboardProvider())
        stage06_fixture.CURRENT_PROJECT = CURRENT_PROJECT
        run_stage06(CURRENT_PROJECT, stage06_fixture.Provider())
        stage07_fixture.CURRENT_PROJECT = CURRENT_PROJECT
        run_stage07(CURRENT_PROJECT, stage07_fixture.Provider())
        for name in ("seedance20_prompts.json", "seedance25_prompts.json"):
            path = CURRENT_PROJECT / name
            data = json.loads(path.read_text(encoding="utf-8"))
            next(iter(data["shots"].values()))["prompt"] += SENTINEL
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        protected_names = ("00_原始剧本.txt", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "storyboard.json", "assets.json", "asset_prompts.json", "06_Seedance2.0提示词.md", "seedance20_prompts.json", "07_Seedance2.5提示词.md", "seedance25_prompts.json")
        protected = {name: (CURRENT_PROJECT / name).read_bytes() for name in protected_names}
        run_stage08(CURRENT_PROJECT, Provider())
        output_bytes = (CURRENT_PROJECT / "jimeng20_prompts.json").read_bytes()
        output = json.loads(output_bytes.decode("utf-8"))
        assert set(output["shots"]) == set(storyboard_shots(json.loads((CURRENT_PROJECT / "storyboard.json").read_text(encoding="utf-8"))))
        assert output["shots"]["S02_SH01"]["prompt_mode"] == "stable_short"
        assert "完全没有移动" in output["shots"]["S02_SH01"]["stable_prompt"]
        assert output["shots"]["S01_SH02"]["warnings"] == ["DIALOGUE_DURATION_WARNING"]
        assert all((CURRENT_PROJECT / name).read_bytes() == content for name, content in protected.items())
        run_stage08(CURRENT_PROJECT, Provider())
        assert output_bytes == (CURRENT_PROJECT / "jimeng20_prompts.json").read_bytes()
        report_before = (CURRENT_PROJECT / "08_即梦2.0提示词.md").read_bytes()
        for mutation in ("state", "physical", "asset"):
            try: run_stage08(CURRENT_PROJECT, Provider(mutation))
            except Exception: pass
            else: raise AssertionError(f"非法即梦 2.0输出未失败：{mutation}")
            assert report_before == (CURRENT_PROJECT / "08_即梦2.0提示词.md").read_bytes()
            assert output_bytes == (CURRENT_PROJECT / "jimeng20_prompts.json").read_bytes()
            assert all((CURRENT_PROJECT / name).read_bytes() == content for name, content in protected.items())
        adapter = Jimeng20Adapter()
        physical_cases = [
            ({"action": ["门被锁住，人物尝试推门但打不开"], "end_state": {}}, "完全打不开"),
            ({"action": ["人物已经冻僵"], "end_state": {}}, "不突然恢复自然动作"),
            ({"action": ["人物已经死亡"], "end_state": {}}, "不自行移动或开口"),
            ({"action": ["道具已经烧毁"], "end_state": {}}, "不恢复完整"),
            ({"action": ["物体固定且无法移动"], "end_state": {}}, "不发生位移"),
            ({"action": ["人物负伤后继续支撑"], "end_state": {"injury": "持续"}}, "伤势持续保持"),
        ]
        for source, expected in physical_cases:
            source.update({"assets": {}, "forbidden": ["禁止字幕", "禁止logo", "禁止水印"], "camera": {}, "dialogue": [], "start_state": {}, "blocking": {}, "duration_seconds": 5})
            combined = adapter.build_prompt(source, {}) + " " + adapter.build_stable_prompt(source, {})
            assert expected in combined
            validate_physical_constraints(source, combined, "PHYSICAL_TEST")
        moving = {"action": ["人物冲向掩体后转身停下"], "end_state": {}, "assets": {}, "forbidden": ["禁止字幕", "禁止logo", "禁止水印"], "camera": {}, "dialogue": [], "start_state": {}, "blocking": {}, "duration_seconds": 6}
        assert "重心先变化" in adapter.build_stable_prompt(moving, {})
    print("offline_test_stage08：全部通过")
    return 0


if __name__ == "__main__": raise SystemExit(main())
