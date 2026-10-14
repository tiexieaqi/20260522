"""Stage 11 离线测试：证据分级、历史 Gate、非历史项目和只读保护。"""

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
from historical_source_provider import HistoricalSourceProvider
from offline_test_stage05 import StoryboardProvider, prepare
from stage05_manager import run_stage05
from stage06_manager import run_stage06
from stage07_manager import run_stage07
from stage08_manager import run_stage08
from stage09_manager import run_stage09
from stage10_manager import run_stage10
from stage11_manager import run_stage11


class MockSourceProvider(HistoricalSourceProvider):
    def search(self, claim: str, context: dict) -> list[dict]:
        if "1935年" in claim:
            return [{"source_id": "MOCK-HIST-001", "source_type": "academic", "evidence_level": "B", "status": "supported", "title": "MockSource：1935年背景", "mock": True}]
        if "冲突" in claim:
            return [{"source_id": "MOCK-HIST-002A", "source_type": "book", "evidence_level": "B", "status": "supported", "title": "MockSource A", "mock": True}, {"source_id": "MOCK-HIST-002B", "source_type": "memoir", "evidence_level": "C", "status": "contradicted", "title": "MockSource B", "mock": True}]
        return []


def prepare_all(root: Path) -> Path:
    project = prepare(root)
    run_stage05(project, StoryboardProvider())
    stage06_fixture.CURRENT_PROJECT = project; run_stage06(project, stage06_fixture.Provider())
    stage07_fixture.CURRENT_PROJECT = project; run_stage07(project, stage07_fixture.Provider())
    stage08_fixture.CURRENT_PROJECT = project; run_stage08(project, stage08_fixture.Provider())
    stage09_fixture.CURRENT_PROJECT = project; run_stage09(project, stage09_fixture.Provider())
    run_stage10(project)
    return project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage11_") as temp:
        root = Path(temp)
        project = prepare_all(root)
        original = project / "00_原始剧本.txt"
        original.write_text("历史短片。HIST:1935年雨夜，通信员在山间驿站传递信件。\nHIST:冲突版本的桥梁结构。\nHIST:虚构战士之间的影视化对白。", encoding="utf-8")
        rules = project / "02_项目专属规则.md"
        rules.write_text(rules.read_text(encoding="utf-8") + "\n禁止logo，禁止文字。", encoding="utf-8")
        protected_names = ("00_原始剧本.txt", "01_剧本解析报告.md", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "assets.json", "asset_prompts.json", "storyboard.json", "06_Seedance2.0提示词.md", "seedance20_prompts.json", "07_Seedance2.5提示词.md", "seedance25_prompts.json", "08_即梦2.0提示词.md", "jimeng20_prompts.json", "09_即梦2.5提示词.md", "jimeng25_prompts.json", "model_prompt_index.json", "10_连续性审核报告.md", "continuity_report.json")
        before = {name: (project / name).read_bytes() for name in protected_names}
        run_stage11(project, MockSourceProvider())
        report_bytes = (project / "historical_report.json").read_bytes()
        report = json.loads(report_bytes.decode("utf-8"))
        assert report["historical_relevance"] == "high"
        assert 0 <= report["historical_score"] <= 100
        assert report["historical_gate"] in {"passed", "review_required", "blocked"}
        assert all(issue["verification_status"] in {"supported", "unverified", "disputed", "contradicted", "dramatized"} for issue in report["issues"])
        assert all(issue["evidence_level"] in {"A", "B", "C", "D", "E"} for issue in report["issues"])
        assert report["production_deviations"] and any(source.get("mock") for source in report["sources"])
        assert report["dramatizations"] and any(issue["verification_status"] == "dramatized" for issue in report["issues"])
        assert all((project / name).read_bytes() == content for name, content in before.items())
        run_stage11(project, MockSourceProvider())
        assert report_bytes == (project / "historical_report.json").read_bytes()
        # 无历史题材项目必须输出 not_applicable，而不是凭感觉生成史实结论。
        original.write_text("现代虚构短片。两位朋友在城市中散步。", encoding="utf-8")
        run_stage11(project)
        modern = json.loads((project / "historical_report.json").read_text(encoding="utf-8"))
        assert modern["historical_relevance"] == "none" and modern["historical_gate"] == "not_applicable" and modern["issues"] == []
    print("offline_test_stage11：全部通过")
    return 0


if __name__ == "__main__": raise SystemExit(main())
