"""Stage 07 离线测试：Seedance 2.5 平行适配与 Stage 05/06 保护。"""

import copy
import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

import offline_test_stage06 as stage06_fixture
from offline_test_stage05 import StoryboardProvider, prepare
from model_prompt_validator import storyboard_shots
from model_stage_base import flatten_asset_refs
from seedance25_adapter import MODEL_PROMPT_BUDGET, Seedance25Adapter
from stage05_manager import run_stage05
from stage06_manager import run_stage06
from stage07_manager import run_stage07


CURRENT_PROJECT: Path
SOURCE20_SENTINEL = "STAGE06内容不得作为Stage07母版"


def make_plan(project: Path, mutate: str | None = None) -> dict:
    project_data = json.loads((project / "project.json").read_text(encoding="utf-8"))
    storyboard = json.loads((project / "storyboard.json").read_text(encoding="utf-8"))
    adapter = Seedance25Adapter()
    shots = {}
    for shot_id, source in storyboard_shots(storyboard).items():
        level, reasons = adapter.assess_risk(source)
        shots[shot_id] = {
            "source_shot_id": shot_id,
            "duration_seconds": source["duration_seconds"],
            "asset_refs": flatten_asset_refs(source),
            "prompt": adapter.build_prompt(source, {}),
            "timeline": [beat["action"] for beat in adapter.action_beats(source)],
            "dialogue": copy.deepcopy(source.get("dialogue", [])),
            "start_state": copy.deepcopy(source["start_state"]),
            "end_state": copy.deepcopy(source["end_state"]),
            "forbidden": copy.deepcopy(source["forbidden"]),
            "risk": {"level": level, "reasons": reasons},
            "model_duration_status": "warning" if source["duration_seconds"] > 10 else "compatible",
            "source_rules": copy.deepcopy(source.get("continuity_notes", [])),
            "action_beats": adapter.action_beats(source),
            "performance_timing": adapter.performance_timing(source),
            "dialogue_timing": adapter.dialogue_timing(source),
            "adaptation_strategy": adapter.adaptation_strategy(source),
            "adapter_profile": "seedance-2.5",
            "adaptation_features": ["performance_timing", "action_beats"],
            "model_prompt_budget": MODEL_PROMPT_BUDGET,
            "model_rule_gap": "MODEL_RULE_GAP",
        }
    if mutate == "dialogue":
        shots["S01_SH01"]["dialogue"][0]["dialogue"] = "错误改写"
    elif mutate == "asset":
        shots["S01_SH01"]["asset_refs"][0] = "CH-999-V01"
    elif mutate == "beats":
        shots["S02_SH01"]["action_beats"][0]["order"] = 9
    return {"schema_version": "1.0", "model": "seedance-2.5", "project_id": project_data["project_id"], "project_name": project_data["project_name"], "shots": shots}


class Provider:
    def __init__(self, mutate=None): self.mutate = mutate
    def complete(self, prompt, schema=None):
        assert SOURCE20_SENTINEL not in prompt
        return json.dumps(make_plan(CURRENT_PROJECT, self.mutate), ensure_ascii=False)


def main() -> int:
    global CURRENT_PROJECT
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage07_") as temp:
        root = Path(temp)
        CURRENT_PROJECT = prepare(root)
        run_stage05(CURRENT_PROJECT, StoryboardProvider())
        stage06_fixture.CURRENT_PROJECT = CURRENT_PROJECT
        run_stage06(CURRENT_PROJECT, stage06_fixture.Provider())
        seedance20 = json.loads((CURRENT_PROJECT / "seedance20_prompts.json").read_text(encoding="utf-8"))
        next(iter(seedance20["shots"].values()))["prompt"] += SOURCE20_SENTINEL
        (CURRENT_PROJECT / "seedance20_prompts.json").write_text(json.dumps(seedance20, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        protected_names = ("00_原始剧本.txt", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "storyboard.json", "assets.json", "asset_prompts.json", "06_Seedance2.0提示词.md", "seedance20_prompts.json")
        protected = {name: (CURRENT_PROJECT / name).read_bytes() for name in protected_names}
        run_stage07(CURRENT_PROJECT, Provider())
        plan_bytes = (CURRENT_PROJECT / "seedance25_prompts.json").read_bytes()
        plan = json.loads(plan_bytes.decode("utf-8"))
        storyboard = json.loads((CURRENT_PROJECT / "storyboard.json").read_text(encoding="utf-8"))
        assert list(plan["shots"]) == list(storyboard_shots(storyboard))
        assert plan["shots"]["S02_SH01"]["adaptation_strategy"] == "emphasis_order"
        assert plan["shots"]["S02_SH01"]["risk"]["level"] == "high"
        assert "枪栓完全没有发生位移" in plan["shots"]["S02_SH01"]["prompt"]
        assert plan["shots"]["S01_SH01"]["dialogue_timing"][0]["speaker_asset_id"] == "CH-001"
        assert all((CURRENT_PROJECT / name).read_bytes() == content for name, content in protected.items())
        run_stage07(CURRENT_PROJECT, Provider())
        assert plan_bytes == (CURRENT_PROJECT / "seedance25_prompts.json").read_bytes()
        report_before = (CURRENT_PROJECT / "07_Seedance2.5提示词.md").read_bytes()
        for mutation in ("dialogue", "asset", "beats"):
            try: run_stage07(CURRENT_PROJECT, Provider(mutation))
            except Exception: pass
            else: raise AssertionError(f"非法 Stage 07 输出未失败：{mutation}")
            assert report_before == (CURRENT_PROJECT / "07_Seedance2.5提示词.md").read_bytes()
            assert plan_bytes == (CURRENT_PROJECT / "seedance25_prompts.json").read_bytes()
            assert all((CURRENT_PROJECT / name).read_bytes() == content for name, content in protected.items())
    print("offline_test_stage07：全部通过")
    return 0


if __name__ == "__main__": raise SystemExit(main())
