"""Stage 03：生成正式资产库并锁定项目资产 ID。"""

import json
from pathlib import Path

from ai_provider import AIProvider
from asset_registry import atomic_save, build_registry, load_registry
from asset_schema import ASSET_CATEGORIES, validate_plan
from config import PROJECT_ROOT
from file_utils import json_read, read_utf8
from stage01_manager import _find_named_files
from stage_base import StageRunner


RULE_NAMES = [
    "00_系统总控规则.md",
    "04_资产库总规则.md",
    "05_人物资产规则.md",
    "06_场景资产规则.md",
    "07_道具资产规则.md",
    "13_历史真实性审核规则.md",
    "14_项目规则隔离规则.md",
]
TEMPLATE_NAMES = ["03_资产库生成模板.md"]
REPORT_NAME = "03_资产库.md"
ASSET_PLAN_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["assets"],
    "properties": {
        "assets": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["category", "canonical_name", "aliases", "source_evidence", "versions"],
                "properties": {
                    "category": {"enum": list(ASSET_CATEGORIES)},
                    "canonical_name": {"type": "string"},
                    "aliases": {"type": "array", "items": {"type": "string"}},
                    "asset_type": {"type": "string"},
                    "importance": {"type": "string"},
                    "story_role": {"type": "string"},
                    "needs_review": {"type": "boolean"},
                    "locked_fields": {"type": "array", "items": {"type": "string"}},
                    "mutable_fields": {"type": "array", "items": {"type": "string"}},
                    "source_evidence": {"type": "array"},
                    "details": {"type": "object"},
                    "versions": {"type": "array"},
                },
            },
        },
    },
}


def _read_sources(directory: Path, names: list[str]) -> str:
    return "".join(f"\n===== {path.name} =====\n{read_utf8(path)}" for path in _find_named_files(directory, names))


def build_stage03_prompt(project_name: str, script_text: str, report_text: str, project_rules: str, common_rules: str, template: str) -> str:
    return f"""你是 AI影视助手的 Stage 03 资产库规划模块。

安全边界：只分析当前项目资料和下方指定规则/模板；不要修改文件，不要读取其他项目，不要生成项目外的规则。

请只返回 JSON，格式为 {{"assets":[...]}}。不要给资产分配 asset_id；程序会统一编号。每个资产必须包含 category（CH/LOC/PROP/WPN/GRP/FX）、canonical_name、aliases、source_evidence（区分 explicit/inferred/needs_confirmation）、versions（至少 V01），以及适用的 locked_fields、mutable_fields、details。

去重要求：同一人物不同称呼绑定同一候选；状态变化用版本，不创建重复基础资产；无法确定是否同一资产时 needs_review=true，不擅自合并。普通雨、风、雾优先记录为 LOC 状态，不滥建 FX。型号未给出时写“具体型号待确认”。不得把故事细节写入通用规则。

项目：{project_name}
===== 原始剧本 =====
{script_text}
===== Stage 01 报告 =====
{report_text}
===== Stage 02 项目专属规则 =====
{project_rules}
===== 通用规则 =====
{common_rules}
===== 资产模板 =====
{template}
"""


def render_asset_markdown(project_name: str, registry: dict, review_items: list[str]) -> str:
    labels = {"CH": "人物资产", "LOC": "场景资产", "PROP": "道具资产", "WPN": "武器资产", "GRP": "群体资产", "FX": "效果资产"}
    lines = ["# 项目资产库", "", f"项目：{project_name}", "", "说明：资产 ID 由程序分配；本文件为人类可读视图，assets.json 为唯一权威登记表。", ""]
    for category in ASSET_CATEGORIES:
        lines += [f"## {category}｜{labels[category]}", ""]
        assets = registry["assets"][category]
        if not assets:
            lines += ["暂无登记资产。", ""]
            continue
        for asset_id, asset in assets.items():
            locked = [f"- {item}" for item in asset["locked_fields"]] or ["- 待确认"]
            mutable = [f"- {item}" for item in asset["mutable_fields"]] or ["- 待确认"]
            lines += [f"### {asset_id}｜{asset['canonical_name']}", "", f"状态：{asset['status']}", f"别名：{'、'.join(asset['aliases']) or '无'}", f"类型：{asset['asset_type']}", f"重要性：{asset['importance']}", f"剧情作用：{asset['story_role']}", "", "【锁定字段】", *locked, "", "【可变化字段】", *mutable, "", "【版本】"]
            for version in asset["versions"]:
                lines += [f"- {version['version']}：{version['label']}", f"  变化：{', '.join(version['changes']) if version['changes'] else '标准状态'}"]
            lines += ["", "【证据】", *[f"- {json.dumps(e, ensure_ascii=False) if isinstance(e, dict) else e}" for e in asset["source_evidence"]], ""]
    lines += ["## 待确认资产", ""]
    pending = [f"- {item}" for assets in registry["assets"].values() for item in assets.values() if item["status"] == "NEEDS_REVIEW"] + [f"- {item}" for item in review_items]
    lines += pending or ["暂无待确认资产。"]
    return "\n".join(lines) + "\n"


def run_stage03(project_dir: Path, provider: AIProvider) -> str:
    project = json_read(project_dir / "project.json")
    original = next(project_dir.glob("00_原始剧本.*"))
    stage01 = project_dir / "01_剧本解析报告.md"
    stage02 = project_dir / "02_项目专属规则.md"
    if "等待 AI 处理" in read_utf8(stage01) or "等待 AI 处理" in read_utf8(stage02):
        raise ValueError("Stage 03 需要先完成 Stage 01 和 Stage 02。")
    common = _read_sources(PROJECT_ROOT / "新版规则库", RULE_NAMES)
    template = _read_sources(PROJECT_ROOT / "15_模板库", TEMPLATE_NAMES)
    prompt = build_stage03_prompt(project["project_name"], read_utf8(original), read_utf8(stage01), read_utf8(stage02), common, template)
    registry_path = project_dir / "assets.json"
    current = load_registry(registry_path, project["project_id"])

    def operation() -> str:
        raw = provider.complete(prompt, schema=ASSET_PLAN_SCHEMA)
        plan = json.loads(raw)
        validate_plan(plan)
        updated, review_items = build_registry(plan, current)
        atomic_save(registry_path, updated)
        return render_asset_markdown(project["project_name"], updated, review_items)

    runner = StageRunner(project_dir, 3, REPORT_NAME, "Stage 03 资产库生成")
    return runner.run(operation, lambda text: text.startswith("# 项目资产库") and "## 待确认资产" in text)
