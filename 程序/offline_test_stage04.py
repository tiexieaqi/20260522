"""Stage 04 离线测试：提示词覆盖、ID 校验、幂等和资产保护。"""

import json
import sys
import tempfile
from pathlib import Path

PROGRAM_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(PROGRAM_DIR))

from project_manager import create_project
from stage01_manager import REQUIRED_HEADINGS as H1, run_stage01
from stage02_manager import REQUIRED_HEADINGS as H2, run_stage02
from stage03_manager import run_stage03
from stage04_manager import run_stage04


class TextProvider:
    def __init__(self, headings): self.headings = headings
    def complete(self, prompt, schema=None): return "\n\n".join(self.headings) + "\n\n测试内容。"


class AssetProvider:
    def complete(self, prompt, schema=None):
        def item(category, name, aliases, versions, locked, mutable=None, evidence="明确证据"):
            return {"category": category, "canonical_name": name, "aliases": aliases, "asset_type": category, "locked_fields": locked, "mutable_fields": mutable or [], "source_evidence": [{"kind": "explicit", "text": evidence}], "versions": [{"label": label, "changes": changes} for label, changes in versions]}
        assets = [
            item("CH", "林川", ["通信员"], [("标准状态", []), ("负伤状态", ["伤势", "泥污"])], ["五官", "年龄段", "基础服装"], ["伤势", "泥污"]),
            item("CH", "赵伯", ["老站长"], [("标准状态", [])], ["五官", "身份", "基础服装"], ["疲劳"]),
            item("LOC", "山间驿站", ["驿站"], [("雨夜", []), ("雪夜", ["天气", "积雪"])], ["空间结构", "门窗位置", "道路方向"], ["天气", "时间"]),
            item("PROP", "重要信件", ["信"], [("完整", []), ("烧毁", ["燃烧", "破损"])], ["材质", "尺寸", "基本外形"], ["湿润", "烧毁"]),
            item("WPN", "步枪", [], [("标准状态", [])], ["武器类别", "基础外观"], ["泥污", "结霜"], "步枪，具体型号待确认"),
            item("GRP", "搜山敌军", ["敌军"], [("搜索状态", [])], ["身份体系", "服装体系", "装备体系"], ["人数", "队形"]),
            item("FX", "特殊火障", [], [("燃烧状态", [])], ["视觉形态", "运动方式"], ["密度", "透明度"]),
        ]
        return json.dumps({"assets": assets}, ensure_ascii=False)


class PromptProvider:
    def __init__(self, mutate=None): self.mutate = mutate
    def complete(self, prompt, schema=None):
        ids = {
            "CH-001": (["CH-001-V01", "CH-001-V02"], ["五官", "年龄段", "基础服装"]),
            "CH-002": (["CH-002-V01"], ["五官", "身份", "基础服装"]),
            "LOC-001": (["LOC-001-V01", "LOC-001-V02"], ["空间结构", "门窗位置", "道路方向"]),
            "PROP-001": (["PROP-001-V01", "PROP-001-V02"], ["材质", "尺寸", "基本外形"]),
            "WPN-001": (["WPN-001-V01"], ["武器类别", "基础外观"]),
            "GRP-001": (["GRP-001-V01"], ["身份体系", "服装体系", "装备体系"]),
            "FX-001": (["FX-001-V01"], ["视觉形态", "运动方式"]),
        }
        records = []
        for asset_id, (versions, locked) in ids.items():
            for version in versions:
                category = asset_id.split("-")[0]
                content = f"{asset_id} 真人实拍电影资产，电影级真实质感，自然材质"
                if version != f"{asset_id}-V01": content += f"，严格保持 {asset_id}-V01 基础资产、锁定结构和身份不变，只改变已定义状态"
                if category == "LOC": content += "，保持空间布局、门窗位置和道路方向"
                if category == "WPN": content += "，1930年代旧式步枪，具体型号待确认，不猜测型号"
                if category == "GRP": content += "，脸型、身高、姿势、装备磨损差异化，禁止机械复制"
                if category == "FX": content += "，明确密度、透明度、运动和环境交互"
                records.append({"asset_id": asset_id, "version": version, "prompt": content, "negative": ["禁止字幕", "禁止文字", "禁止数字", "禁止logo", "禁止水印", "禁止UI", "禁止二维码", "禁止乱码"], "locked_fields": locked, "source_assets": [asset_id]})
        if self.mutate == "unknown": records.append({"asset_id": "CH-999", "version": "CH-999-V01", "prompt": "CH-999", "negative": ["字幕","文字","logo","水印","UI","二维码","乱码"], "locked_fields": [], "source_assets": ["CH-999"]})
        if self.mutate == "missing": records.pop()
        return json.dumps({"prompts": records}, ensure_ascii=False)


def prepare(root: Path, filename: str) -> Path:
    source = root / filename; source.write_text("1935年雨夜，通信员林川在山间驿站传递信件。", encoding="utf-8")
    project = create_project(source, projects_dir=root / "projects", input_func=lambda _: "1")
    run_stage01(project, TextProvider(H1)); run_stage02(project, TextProvider(H2)); run_stage03(project, AssetProvider())
    return project


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="ai影视助手_stage04_") as temp:
        root = Path(temp)
        for filename in ("历史项目.txt", "现代项目.txt"):
            project = prepare(root, filename)
            assets_before = (project / "assets.json").read_bytes()
            run_stage04(project, PromptProvider())
            prompts = json.loads((project / "asset_prompts.json").read_text(encoding="utf-8"))
            expected = sum(len(a["versions"]) for group in json.loads(assets_before)["assets"].values() for a in group.values())
            assert len(prompts["prompts"]) == expected
            assert "CH-001-V02" in prompts["prompts"] and "保持" in prompts["prompts"]["CH-001-V02"]["prompt"]
            assert "具体型号待确认" in prompts["prompts"]["WPN-001-V01"]["prompt"]
            assert "差异化" in prompts["prompts"]["GRP-001-V01"]["prompt"]
            assert assets_before == (project / "assets.json").read_bytes()
            json_before = (project / "asset_prompts.json").read_bytes(); md_before = (project / "04_资产生成提示词.md").read_bytes()
            run_stage04(project, PromptProvider())
            assert json_before == (project / "asset_prompts.json").read_bytes() and md_before == (project / "04_资产生成提示词.md").read_bytes()

        failed = prepare(root, "失败保护.txt")
        assets_before = (failed / "assets.json").read_bytes(); placeholder = (failed / "04_资产生成提示词.md").read_bytes()
        for mode in ("unknown", "missing"):
            try: run_stage04(failed, PromptProvider(mode))
            except Exception: pass
            else: raise AssertionError("非法 Stage 04 输出没有失败")
            assert assets_before == (failed / "assets.json").read_bytes()
            assert placeholder == (failed / "04_资产生成提示词.md").read_bytes()
        assert not (failed / "asset_prompts.json").exists()
        state = json.loads((failed / "workflow_state.json").read_text(encoding="utf-8"))
        assert state["stages"]["4"]["status"] == "failed"
    print("offline_test_stage04：全部通过")
    return 0


if __name__ == "__main__": raise SystemExit(main())
