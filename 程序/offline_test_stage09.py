"""Stage 09 离线测试：即梦 2.5 双提示词、电影增强和四模型索引。"""

import copy
import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

import offline_test_stage06 as stage06_fixture
import offline_test_stage07 as stage07_fixture
import offline_test_stage08 as stage08_fixture
from jimeng25_adapter import JIMENG25_CINEMATIC_BUDGET, JIMENG25_STABLE_BUDGET, Jimeng25Adapter
from model_prompt_validator import storyboard_shots
from model_stage_base import flatten_asset_refs
from offline_test_stage05 import StoryboardProvider, prepare
from stage05_manager import run_stage05
from stage06_manager import run_stage06
from stage07_manager import run_stage07
from stage08_manager import run_stage08
from stage09_manager import run_stage09
from cross_model_consistency_test import validate_project


CURRENT_PROJECT: Path
SENTINEL = "其他模型内容不得成为即梦2.5母版"


def make_plan(project: Path, mutate: str | None = None) -> dict:
    data = json.loads((project / "project.json").read_text(encoding="utf-8"))
    storyboard = json.loads((project / "storyboard.json").read_text(encoding="utf-8"))
    adapter = Jimeng25Adapter()
    shots = {}
    for shot_id, source in storyboard_shots(storyboard).items():
        level, reasons = adapter.assess_risk(source)
        stable = adapter.build_stable_prompt(source, {})
        cinematic = adapter.build_cinematic_prompt(source, {})
        recommended, reason = adapter.recommended_mode(level)
        shots[shot_id] = {
            "source_shot_id": shot_id,
            "duration_seconds": source["duration_seconds"],
            "asset_refs": flatten_asset_refs(source),
            "prompt": stable,
            "adapter_profile": "jimeng-2.5",
            "stable_prompt": stable,
            "cinematic_prompt": cinematic,
            "recommended_prompt_mode": recommended,
            "recommendation_reason": reason,
            "cinematic_features": adapter.cinematic_features(source),
            "cinematic_budget": {"stable_budget": JIMENG25_STABLE_BUDGET, "cinematic_budget": JIMENG25_CINEMATIC_BUDGET},
            "action_beats": adapter.action_beats(source),
            "performance_beats": adapter.performance_beats(source),
            "dialogue_timing": adapter.dialogue_timing(source),
            "end_frame_anchor": adapter.end_frame_anchor(source),
            "dialogue": copy.deepcopy(source.get("dialogue", [])),
            "start_state": copy.deepcopy(source["start_state"]),
            "end_state": copy.deepcopy(source["end_state"]),
            "forbidden": copy.deepcopy(source["forbidden"]),
            "risk": {"level": level, "reasons": reasons},
            "jimeng25_risk": level,
            "risk_reasons": reasons,
            "jimeng25_prompt_budget": JIMENG25_CINEMATIC_BUDGET,
            "model_duration_status": "compatible",
            "source_rules": copy.deepcopy(source.get("continuity_notes", [])),
        }
    if mutate == "dialogue": shots["S01_SH01"]["dialogue"][0]["dialogue"] = "被改写的对白"
    if mutate == "asset": shots["S01_SH01"]["asset_refs"][0] = "CH-999-V01"
    if mutate == "cinematic_fact": shots["S01_SH01"]["cinematic_prompt"] += " 新增爆炸和新人物"
    return {"schema_version": "1.0", "model": "jimeng-2.5", "project_id": data["project_id"], "project_name": data["project_name"], "shots": shots}


class Provider:
    def __init__(self, mutate=None): self.mutate = mutate
    def complete(self, prompt, schema=None):
        assert SENTINEL not in prompt
        return json.dumps(make_plan(CURRENT_PROJECT, self.mutate), ensure_ascii=False)


def main() -> int:
    global CURRENT_PROJECT
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage09_") as temp:
        root = Path(temp)
        CURRENT_PROJECT = prepare(root)
        run_stage05(CURRENT_PROJECT, StoryboardProvider())
        stage06_fixture.CURRENT_PROJECT = CURRENT_PROJECT; run_stage06(CURRENT_PROJECT, stage06_fixture.Provider())
        stage07_fixture.CURRENT_PROJECT = CURRENT_PROJECT; run_stage07(CURRENT_PROJECT, stage07_fixture.Provider())
        stage08_fixture.CURRENT_PROJECT = CURRENT_PROJECT; run_stage08(CURRENT_PROJECT, stage08_fixture.Provider())
        for name in ("seedance20_prompts.json", "seedance25_prompts.json", "jimeng20_prompts.json"):
            path = CURRENT_PROJECT / name
            data = json.loads(path.read_text(encoding="utf-8")); next(iter(data["shots"].values()))["prompt"] += SENTINEL
            path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        protected_names = ("00_原始剧本.txt", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "storyboard.json", "assets.json", "asset_prompts.json", "06_Seedance2.0提示词.md", "seedance20_prompts.json", "07_Seedance2.5提示词.md", "seedance25_prompts.json", "08_即梦2.0提示词.md", "jimeng20_prompts.json")
        protected = {name: (CURRENT_PROJECT / name).read_bytes() for name in protected_names}
        run_stage09(CURRENT_PROJECT, Provider())
        output_bytes = (CURRENT_PROJECT / "jimeng25_prompts.json").read_bytes()
        output = json.loads(output_bytes.decode("utf-8"))
        storyboard = json.loads((CURRENT_PROJECT / "storyboard.json").read_text(encoding="utf-8"))
        assert list(output["shots"]) == list(storyboard_shots(storyboard))
        assert output["shots"]["S02_SH01"]["recommended_prompt_mode"] == "stable"
        assert output["shots"]["S02_SH01"]["stable_prompt"] and output["shots"]["S02_SH01"]["cinematic_prompt"]
        assert (CURRENT_PROJECT / "model_prompt_index.json").is_file()
        index = json.loads((CURRENT_PROJECT / "model_prompt_index.json").read_text(encoding="utf-8"))
        assert set(index["shots"]) == set(output["shots"])
        validate_project(CURRENT_PROJECT)
        assert all((CURRENT_PROJECT / name).read_bytes() == content for name, content in protected.items())
        run_stage09(CURRENT_PROJECT, Provider())
        assert output_bytes == (CURRENT_PROJECT / "jimeng25_prompts.json").read_bytes()
        report_before = (CURRENT_PROJECT / "09_即梦2.5提示词.md").read_bytes()
        for mutation in ("dialogue", "asset", "cinematic_fact"):
            try: run_stage09(CURRENT_PROJECT, Provider(mutation))
            except Exception: pass
            else: raise AssertionError(f"非法即梦 2.5输出未失败：{mutation}")
            assert report_before == (CURRENT_PROJECT / "09_即梦2.5提示词.md").read_bytes()
            assert output_bytes == (CURRENT_PROJECT / "jimeng25_prompts.json").read_bytes()
    print("offline_test_stage09：全部通过")
    return 0


if __name__ == "__main__": raise SystemExit(main())
