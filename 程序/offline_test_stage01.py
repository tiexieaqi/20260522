"""Stage 01 离线测试：不调用 AI、不联网，验证完整状态和写入流程。"""

import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

from project_manager import create_project
from stage01_manager import REQUIRED_HEADINGS, run_stage01


class OfflineProvider:
    def complete(self, prompt: str) -> str:
        assert "01_剧本分析规则.md" in prompt
        assert "01_剧本输入模板.md" in prompt
        assert "测试故事" in prompt
        return "\n\n".join(REQUIRED_HEADINGS) + "\n\n历史真实性风险：不适用。\n"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai影视助手_offline_") as temp:
        root = Path(temp)
        source_dir = root / "输入剧本"
        source_dir.mkdir()
        source = source_dir / "测试故事.txt"
        source.write_text("测试故事：一名信使穿过山谷。", encoding="utf-8")
        project = create_project(source, projects_dir=root / "projects", input_func=lambda _: "1")
        run_stage01(project, OfflineProvider())
        report = (project / "01_剧本解析报告.md").read_text(encoding="utf-8")
        state = json.loads((project / "workflow_state.json").read_text(encoding="utf-8"))
        assert report.startswith("# 剧本解析报告")
        assert state["stages"]["1"]["status"] == "completed"
        assert not (project / "logs").exists()
    print("offline_test：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
