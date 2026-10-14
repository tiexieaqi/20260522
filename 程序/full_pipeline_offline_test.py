"""完整 Stage 01—12 离线总验收及关键阶段失败阻断测试。"""
import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))
from offline_test_stage05 import StoryboardProvider, prepare
from offline_test_stage06 import Provider as P06
from offline_test_stage07 import Provider as P07
from offline_test_stage08 import Provider as P08
from offline_test_stage09 import Provider as P09
import offline_test_stage06 as f06, offline_test_stage07 as f07, offline_test_stage08 as f08, offline_test_stage09 as f09
from stage05_manager import run_stage05
from stage06_manager import run_stage06
from stage07_manager import run_stage07
from stage08_manager import run_stage08
from stage09_manager import run_stage09
from stage10_manager import run_stage10
from stage11_manager import run_stage11
from stage12_manager import run_stage12
from cross_model_consistency_test import validate_project


class FailProvider:
    def complete(self, prompt, schema=None):
        raise RuntimeError("mock AI failure")


class FailSource:
    def search(self, claim, context):
        raise RuntimeError("mock source failure")


def complete_project(root: Path) -> Path:
    project = prepare(root)
    run_stage05(project, StoryboardProvider())
    f06.CURRENT_PROJECT = project; run_stage06(project, P06())
    f07.CURRENT_PROJECT = project; run_stage07(project, P07())
    f08.CURRENT_PROJECT = project; run_stage08(project, P08())
    f09.CURRENT_PROJECT = project; run_stage09(project, P09())
    run_stage10(project)
    run_stage11(project)
    run_stage12(project)
    return project


def check_complete(project: Path) -> None:
    required = ["00_项目说明.md", "00_原始剧本.txt"] + [f"{n:02d}_" for n in range(1, 13)]
    for prefix in required:
        assert any(p.name.startswith(prefix) for p in project.iterdir()), f"缺少 {prefix}"
    for name in ("project.json", "assets.json", "workflow_state.json", "asset_prompts.json", "storyboard.json", "seedance20_prompts.json", "seedance25_prompts.json", "jimeng20_prompts.json", "jimeng25_prompts.json", "model_prompt_index.json", "continuity_report.json", "historical_report.json", "generation_risk_report.json", "project_final_status.json"):
        json.loads((project / name).read_text(encoding="utf-8"))
    state = json.loads((project / "workflow_state.json").read_text(encoding="utf-8"))
    assert all(state["stages"][str(n)]["status"] == "completed" for n in range(1, 13))
    risk = json.loads((project / "generation_risk_report.json").read_text(encoding="utf-8"))
    assert set(risk["model_risks"]) == {"seedance20", "seedance25", "jimeng20", "jimeng25"}
    final = json.loads((project / "project_final_status.json").read_text(encoding="utf-8"))
    assert final["final_pipeline_status"] in {"ready", "review_required", "blocked"}
    validate_project(project)


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai影视助手_full_") as temp:
        root = Path(temp)
        project = complete_project(root)
        check_complete(project)
        # Stage 05 失败后不应产生下游标准分镜。
        (root / "fail5").mkdir(parents=True)
        fail5 = prepare(root / "fail5")
        try: run_stage05(fail5, FailProvider())
        except Exception: pass
        else: raise AssertionError("Stage 05 mock failure 未触发")
        assert json.loads((fail5 / "workflow_state.json").read_text(encoding="utf-8"))["stages"]["5"]["status"] == "failed"
        # Stage 08 失败时 Stage 09/12 均不能假装继续。
        (root / "fail8").mkdir(parents=True)
        fail8 = prepare(root / "fail8"); run_stage05(fail8, StoryboardProvider())
        f06.CURRENT_PROJECT = fail8; run_stage06(fail8, P06()); f07.CURRENT_PROJECT = fail8; run_stage07(fail8, P07())
        f08.CURRENT_PROJECT = fail8
        try: run_stage08(fail8, FailProvider())
        except Exception: pass
        else: raise AssertionError("Stage 08 mock failure 未触发")
        try: run_stage12(fail8)
        except Exception: pass
        else: raise AssertionError("上游 Stage 08 失败后 Stage 12 错误继续")
        # Stage 11 失败后 Stage 12 必须阻断。
        (root / "fail11").mkdir(parents=True)
        fail11 = complete_project(root / "fail11")
        (fail11 / "historical_report.json").write_text("{}\n", encoding="utf-8")
        try: run_stage11(fail11, FailSource())
        except Exception: pass
        try: run_stage12(fail11)
        except Exception: pass
        else: raise AssertionError("Stage 11 mock failure后 Stage 12 错误继续")
    print("full_pipeline_offline_test：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
