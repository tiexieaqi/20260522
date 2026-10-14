"""Stage 10 离线测试：连续性报告、Gate、评分、只读保护和稳定编号。"""

import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

import offline_test_stage06 as stage06_fixture
import offline_test_stage07 as stage07_fixture
import offline_test_stage08 as stage08_fixture
import offline_test_stage09 as stage09_fixture
from offline_test_stage05 import StoryboardProvider, prepare
from stage05_manager import run_stage05
from stage06_manager import run_stage06
from stage07_manager import run_stage07
from stage08_manager import run_stage08
from stage09_manager import run_stage09
from stage10_manager import run_stage10


def prepare_all(root: Path) -> Path:
    project = prepare(root)
    run_stage05(project, StoryboardProvider())
    stage06_fixture.CURRENT_PROJECT = project; run_stage06(project, stage06_fixture.Provider())
    stage07_fixture.CURRENT_PROJECT = project; run_stage07(project, stage07_fixture.Provider())
    stage08_fixture.CURRENT_PROJECT = project; run_stage08(project, stage08_fixture.Provider())
    stage09_fixture.CURRENT_PROJECT = project; run_stage09(project, stage09_fixture.Provider())
    return project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage10_") as temp:
        root = Path(temp)
        project = prepare_all(root)
        names = ("00_原始剧本.txt", "01_剧本解析报告.md", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "assets.json", "asset_prompts.json", "storyboard.json", "06_Seedance2.0提示词.md", "seedance20_prompts.json", "07_Seedance2.5提示词.md", "seedance25_prompts.json", "08_即梦2.0提示词.md", "jimeng20_prompts.json", "09_即梦2.5提示词.md", "jimeng25_prompts.json", "model_prompt_index.json")
        before = {name: (project / name).read_bytes() for name in names}
        run_stage10(project)
        report_bytes = (project / "continuity_report.json").read_bytes()
        report = json.loads(report_bytes.decode("utf-8"))
        assert 0 <= report["continuity_score"] <= 100
        assert report["gate"] in {"passed", "review_required", "blocked"}
        assert report["issues"] and all(item["issue_id"].startswith("CONT-") for item in report["issues"])
        assert report["cross_model"]["consistent"] is True
        assert (project / "10_连续性审核报告.md").read_text(encoding="utf-8").startswith("# 连续性审核报告")
        assert all((project / name).read_bytes() == content for name, content in before.items())
        run_stage10(project)
        assert report_bytes == (project / "continuity_report.json").read_bytes()
        # 制造人物版本倒退，验证版本问题会被定位而不是自动修复。
        storyboard_path = project / "storyboard.json"
        storyboard_data = json.loads(storyboard_path.read_text(encoding="utf-8"))
        storyboard_data["scenes"][0]["shots"][0]["assets"]["characters"] = ["CH-001-V02"]
        storyboard_data["scenes"][1]["shots"][0]["assets"]["characters"] = ["CH-001-V01"]
        storyboard_path.write_text(json.dumps(storyboard_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run_stage10(project)
        version_report = json.loads((project / "continuity_report.json").read_text(encoding="utf-8"))
        assert any(item["category"] == "version" and item["severity"] == "error" for item in version_report["issues"])
        storyboard_path.write_bytes(before["storyboard.json"])
        # 制造一个模型台词漂移，Stage 10 应报告错误但不得修改模型文件。
        model_path = project / "jimeng25_prompts.json"
        model = json.loads(model_path.read_text(encoding="utf-8"))
        model["shots"]["S01_SH01"]["dialogue"][0]["dialogue"] = "错误台词"
        model_path.write_text(json.dumps(model, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        try: run_stage10(project)
        except Exception as error: raise AssertionError(f"连续性审核不应因发现问题而失败：{error}")
        changed = json.loads((project / "continuity_report.json").read_text(encoding="utf-8"))
        assert any(item["category"] == "cross_model" and item["severity"] == "error" for item in changed["issues"])
        assert (project / "jimeng25_prompts.json").read_text(encoding="utf-8").find("错误台词") >= 0
    print("offline_test_stage10：全部通过")
    return 0


if __name__ == "__main__": raise SystemExit(main())
