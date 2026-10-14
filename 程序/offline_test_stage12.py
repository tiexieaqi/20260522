"""Stage 12 离线测试：静态风险、四模型风险、幂等和只读保护。"""
import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))
from offline_test_stage11 import prepare_all
from stage11_manager import run_stage11
from stage12_manager import run_stage12


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage12_") as temp:
        project = prepare_all(Path(temp))
        run_stage11(project)
        names = ("00_原始剧本.txt", "01_剧本解析报告.md", "02_项目专属规则.md", "03_资产库.md", "04_资产生成提示词.md", "05_标准分镜.md", "assets.json", "asset_prompts.json", "storyboard.json", "06_Seedance2.0提示词.md", "07_Seedance2.5提示词.md", "08_即梦2.0提示词.md", "09_即梦2.5提示词.md", "seedance20_prompts.json", "seedance25_prompts.json", "jimeng20_prompts.json", "jimeng25_prompts.json", "model_prompt_index.json", "10_连续性审核报告.md", "continuity_report.json", "11_历史真实性审核报告.md", "historical_report.json")
        before = {name: (project / name).read_bytes() for name in names}
        run_stage12(project)
        report = json.loads((project / "generation_risk_report.json").read_text(encoding="utf-8"))
        assert 0 <= report["overall_risk_score"] <= 100
        assert report["generation_gate"] in {"passed", "review_required", "blocked"}
        assert set(report["model_risks"]) == {"seedance20", "seedance25", "jimeng20", "jimeng25"}
        assert (project / "project_final_status.json").is_file()
        final = json.loads((project / "project_final_status.json").read_text(encoding="utf-8"))
        assert final["generation_gate"] == report["generation_gate"]
        assert (project / "12_AI生成风险报告.md").read_text(encoding="utf-8").startswith("# AI生成风险终审")
        assert all((project / name).read_bytes() == content for name, content in before.items())
        report_bytes = (project / "generation_risk_report.json").read_bytes()
        run_stage12(project)
        assert report_bytes == (project / "generation_risk_report.json").read_bytes()
        # 注入一个模型层的静态新增事实，必须被定位为模型风险而不是修改母版。
        path = project / "jimeng25_prompts.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        first = next(iter(data["shots"]))
        data["shots"][first]["prompt"] = data["shots"][first].get("prompt", "") + " 新增爆炸"
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        run_stage12(project)
        changed = json.loads((project / "generation_risk_report.json").read_text(encoding="utf-8"))
        assert any(item["risk_type"] == "MODEL_FACT_DRIFT_RISK" and item["model"] == "jimeng25" for item in changed["issues"])
    print("offline_test_stage12：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
