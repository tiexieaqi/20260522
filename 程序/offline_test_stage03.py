"""Stage 03 离线测试：普通、历史、战争输入及资产锁定保护。"""

import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

from project_manager import create_project
from stage01_manager import REQUIRED_HEADINGS as STAGE01_HEADINGS, run_stage01
from stage02_manager import REQUIRED_HEADINGS as STAGE02_HEADINGS, run_stage02
from stage03_manager import run_stage03


class MockStage01:
    def complete(self, prompt: str, schema: dict | None = None) -> str:
        return "\n\n".join(STAGE01_HEADINGS) + "\n\n历史真实性风险：待核验。"


class MockStage02:
    def complete(self, prompt: str, schema: dict | None = None) -> str:
        return "\n\n".join(STAGE02_HEADINGS) + "\n\n当前项目专属规则。"


class MockStage03:
    def complete(self, prompt: str, schema: dict | None = None) -> str:
        assert schema and "assets" in schema["properties"]
        plan = {
            "assets": [
                {
                    "category": "CH",
                    "canonical_name": "谢益先",
                    "aliases": ["谢同志", "年轻战士谢益先"],
                    "asset_type": "人物",
                    "story_role": "通信员",
                    "source_evidence": [{"kind": "explicit", "text": "谢益先"}],
                    "locked_fields": ["五官", "身份", "基础服装"],
                    "mutable_fields": ["疲劳", "伤势", "污损"],
                    "versions": [
                        {"label": "正常状态"},
                        {"label": "饥饿状态", "changes": ["疲劳", "污损"]},
                    ],
                },
                {
                    "category": "LOC",
                    "canonical_name": "山间驿站",
                    "aliases": ["驿站"],
                    "asset_type": "场景",
                    "source_evidence": [{"kind": "explicit", "text": "山间驿站"}],
                    "versions": [
                        {"label": "雨夜"},
                        {"label": "暴雪", "changes": ["天气"]},
                    ],
                },
                {
                    "category": "PROP",
                    "canonical_name": "重要信件",
                    "aliases": ["信"],
                    "asset_type": "道具",
                    "source_evidence": [{"kind": "explicit", "text": "一封信"}],
                    "versions": [{"label": "完整"}, {"label": "烧毁", "changes": ["燃烧"]}],
                },
                {
                    "category": "WPN",
                    "canonical_name": "步枪",
                    "aliases": [],
                    "asset_type": "武器",
                    "source_evidence": [{"kind": "explicit", "text": "步枪，具体型号待确认"}],
                    "versions": [{"label": "标准状态"}],
                },
                {
                    "category": "GRP",
                    "canonical_name": "搜山敌军",
                    "aliases": ["敌军"],
                    "asset_type": "群体",
                    "source_evidence": [{"kind": "explicit", "text": "敌人搜山"}],
                    "versions": [{"label": "搜索状态"}],
                },
            ]
        }
        return json.dumps(plan, ensure_ascii=False)


class InvalidStage03:
    def complete(self, prompt: str, schema: dict | None = None) -> str:
        return '{"invalid": true}'


def prepare_project(root: Path, filename: str) -> Path:
    source = root / filename
    source.write_text("测试剧本：1935年冬，通信员穿过山谷。", encoding="utf-8")
    project = create_project(source, projects_dir=root / "projects", input_func=lambda _: "1")
    run_stage01(project, MockStage01())
    run_stage02(project, MockStage02())
    return project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage03_") as temp:
        root = Path(temp)
        for filename in ("普通剧情.txt", "历史题材.txt", "战争题材.txt"):
            project = prepare_project(root, filename)
            run_stage03(project, MockStage03())
            data = json.loads((project / "assets.json").read_text(encoding="utf-8"))
            assert data["schema_version"] == "2.0"
            assert set(data["assets"]) == {"CH", "LOC", "PROP", "WPN", "GRP", "FX"}
            assert list(data["assets"]["CH"]) == ["CH-001"]
            assert data["assets"]["CH"]["CH-001"]["versions"][1]["version"] == "CH-001-V02"
            assert data["assets"]["FX"] == {}
            first_ids = {category: sorted(items) for category, items in data["assets"].items()}
            run_stage03(project, MockStage03())
            again = json.loads((project / "assets.json").read_text(encoding="utf-8"))
            assert first_ids == {category: sorted(items) for category, items in again["assets"].items()}
            assert "谢同志" in (project / "03_资产库.md").read_text(encoding="utf-8")

        failed = prepare_project(root, "失败保护.txt")
        before = (failed / "assets.json").read_bytes()
        try:
            run_stage03(failed, InvalidStage03())
        except Exception:
            pass
        else:
            raise AssertionError("无效 Schema 没有失败")
        assert before == (failed / "assets.json").read_bytes()
        state = json.loads((failed / "workflow_state.json").read_text(encoding="utf-8"))
        assert state["stages"]["3"]["status"] == "failed"
        assert (failed / "logs" / "stage03_error.log").is_file()
    print("offline_test_stage03：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
